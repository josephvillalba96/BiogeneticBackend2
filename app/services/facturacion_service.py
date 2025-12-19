from sqlalchemy.orm import Session
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime
from decimal import Decimal
from fastapi import HTTPException, status
from sqlalchemy import and_, or_

from app.models.facturacion import Facturacion, FacturaDetalle, EstadoFactura
from app.models.user import User, Role
from app.services import role_service
from app.schemas.facturacion_schema import (
    FacturaFormData, 
    FacturaItemCreate, 
    FacturacionCreate,
    FacturacionUpdate,
    FacturacionResponse,
    FacturacionListResponse
)
import re

def generate_factura_id(fecha: datetime, documento_cliente: str, serial: int) -> str:
    """
    Genera un ID de factura con formato: mmddyyyydddddddx
    donde:
    - mmddyyyy: fecha en formato mmddyyyy
    - ddddddd: todos los dígitos del documento del cliente (máximo 7 dígitos)
    - x: número serial (1, 2, 3, ...)
    """
    # Formatear fecha como mmddyyyy
    fecha_str = fecha.strftime("%m%d%Y")
    
    # Limpiar documento del cliente (solo números)
    doc_clean = re.sub(r'[^0-9]', '', documento_cliente)
    
    # Asegurar que el documento tenga máximo 7 dígitos
    if len(doc_clean) > 7:
        doc_clean = doc_clean[:7]
    elif len(doc_clean) < 7:
        # Rellenar con ceros a la izquierda
        doc_clean = doc_clean.zfill(7)
    
    # Generar ID completo
    factura_id = f"{fecha_str}{doc_clean}{serial}"
    
    return factura_id

def generate_unique_factura_id(db: Session, fecha: datetime, documento_cliente: str) -> str:
    """
    Genera un ID de factura único verificando que no exista en la base de datos
    """
    # Limpiar documento del cliente
    doc_clean = re.sub(r'[^0-9]', '', documento_cliente)
    if len(doc_clean) > 7:
        doc_clean = doc_clean[:7]
    elif len(doc_clean) < 7:
        doc_clean = doc_clean.zfill(7)
    
    # Formatear fecha
    fecha_str = fecha.strftime("%m%d%Y")
    
    # Intentar generar ID único
    for serial in range(1, 1000):  # Máximo 999 facturas por día por cliente
        factura_id = f"{fecha_str}{doc_clean}{serial}"
        
        # Verificar si ya existe
        existing = db.query(Facturacion).filter(Facturacion.id_factura == factura_id).first()
        if not existing:
            return factura_id
    
    # Si llegamos aquí, usar timestamp como fallback
    timestamp = int(fecha.timestamp())
    return f"{fecha_str}{doc_clean}{timestamp}"

def get_next_serial_for_date(db: Session, fecha: datetime, documento_cliente: str) -> int:
    """
    Obtiene el siguiente número serial para una fecha y documento específicos
    """
    # Limpiar documento del cliente
    doc_clean = re.sub(r'[^0-9]', '', documento_cliente)
    if len(doc_clean) > 7:
        doc_clean = doc_clean[:7]
    elif len(doc_clean) < 7:
        doc_clean = doc_clean.zfill(7)
    
    # Obtener todas las facturas del día para este documento específico
    fecha_inicio = fecha.replace(hour=0, minute=0, second=0, microsecond=0)
    fecha_fin = fecha.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    # Buscar facturas que terminen con el documento del cliente
    facturas = db.query(Facturacion).filter(
        Facturacion.fecha_generacion >= fecha_inicio,
        Facturacion.fecha_generacion <= fecha_fin,
        Facturacion.id_factura.like(f'%{doc_clean}%')
    ).all()
    
    # Contar facturas que coincidan exactamente con el patrón del documento
    serial_count = 0
    for factura in facturas:
        if factura.id_factura.endswith(doc_clean):
            # Extraer el serial del final del ID
            try:
                serial_part = factura.id_factura[-1]  # Último carácter
                if serial_part.isdigit():
                    serial_count = max(serial_count, int(serial_part))
            except (ValueError, IndexError):
                continue
    
    return serial_count + 1

def process_factura_form_data(form_data: FacturaFormData) -> List[FacturaItemCreate]:
    """
    Procesa los datos del formulario y crea los items de factura
    """
    items = []
    
    # Mapeo de campos del formulario a nombres de items
    item_mapping = {
        "embrio_fresco": "Embrión fresco",
        "embrio_congelado": "Embrión congelado", 
        "material_campo": "Material de campo",
        "nitrogeno": "Nitrógeno",
        "mensajeria": "Mensajería",
        "pajilla_semen": "Pajilla de semen",
        "fundas_te": "Fundas T.E"
    }
    
    for field_name, item_name in item_mapping.items():
        valor = getattr(form_data, field_name, 0)
        if valor and valor > 0:
            items.append(FacturaItemCreate(
                nombre=item_name,
                valor=valor
            ))
    
    return items

def calculate_total(items: List[FacturaItemCreate]) -> Decimal:
    """
    Calcula el total de los items
    """
    return sum(item.valor for item in items)

def calculate_iva_amount(monto_base: Decimal, iva_porcentaje: Decimal) -> Decimal:
    """
    Calcula el valor del IVA
    """
    return monto_base * (iva_porcentaje / Decimal('100'))

def calculate_factura_amounts(monto_base: Decimal, aplica_iva: bool, iva_porcentaje: Decimal = Decimal('19.0')) -> Tuple[Decimal, Decimal, Decimal]:
    """
    Calcula los montos de la factura considerando si aplica IVA o no
    
    Returns:
        tuple: (monto_base, valor_iva, monto_total)
    """
    if aplica_iva:
        valor_iva = calculate_iva_amount(monto_base, iva_porcentaje)
        monto_total = monto_base + valor_iva
    else:
        valor_iva = Decimal('0')
        monto_total = monto_base
    
    return monto_base, valor_iva, monto_total

def create_factura_with_details(
    db: Session, 
    factura_data: FacturacionCreate, 
    admin_user: User
) -> Facturacion:
    """
    Crea una factura con sus detalles en una sola operación
    """
    try:
        # Obtener el cliente al que pertenece la factura
        cliente = db.query(User).filter(User.id == factura_data.cliente_id).first()
        if not cliente:
            raise ValueError(f"Cliente con ID {factura_data.cliente_id} no encontrado")
        
        # Calcular monto base de los items
        monto_base = calculate_total(factura_data.items)
        
        if monto_base <= 0:
            raise ValueError("El monto base debe ser mayor a 0")
        
        # Calcular montos considerando IVA
        monto_base, valor_iva, monto_total = calculate_factura_amounts(
            monto_base, 
            factura_data.aplica_iva, 
            factura_data.iva or Decimal('19.0')
        )
        
        # Generar ID de factura único
        fecha_actual = datetime.now()
        factura_id = generate_unique_factura_id(db, fecha_actual, cliente.number_document)
        
        # Crear factura
        factura = Facturacion(
            id_factura=factura_id,
            fecha_generacion=fecha_actual,
            monto_pagar=monto_total,
            monto_base=monto_base,
            iva=factura_data.iva or Decimal('19.0'),
            valor_iva=valor_iva,
            estado=EstadoFactura.pendiente,
            descripcion=factura_data.descripcion,
            fecha_vencimiento=factura_data.fecha_vencimiento,
            cliente_id=factura_data.cliente_id,
            aplica_iva=factura_data.aplica_iva
        )
        
        db.add(factura)
        db.flush()  # Para obtener el ID de la factura
        
        # Crear un solo detalle de factura con todos los items
        detalle = FacturaDetalle(
            factura_id=factura.id,
            embrio_fresco=Decimal('0'),
            embrio_congelado=Decimal('0'),
            material_campo=Decimal('0'),
            nitrogeno=Decimal('0'),
            mensajeria=Decimal('0'),
            pajilla_semen=Decimal('0'),
            fundas_te=Decimal('0'),
            iva=factura_data.iva or Decimal('19.0')
        )
        
        # Mapear cada item a su campo correspondiente
        for item in factura_data.items:
            # Normalizar nombre para comparación (sin acentos y minúsculas)
            nombre_normalizado = item.nombre.lower().replace('ó', 'o').replace('é', 'e').replace('í', 'i').replace('á', 'a').replace('ú', 'u')
            
            if "embrion fresco" in nombre_normalizado:
                detalle.embrio_fresco = item.valor
            elif "embrion congelado" in nombre_normalizado:
                detalle.embrio_congelado = item.valor
            elif "material de campo" in nombre_normalizado:
                detalle.material_campo = item.valor
            elif "nitrogeno" in nombre_normalizado:
                detalle.nitrogeno = item.valor
            elif "mensajeria" in nombre_normalizado:
                detalle.mensajeria = item.valor
            elif "pajilla de semen" in nombre_normalizado:
                detalle.pajilla_semen = item.valor
            elif "fundas t.e" in nombre_normalizado:
                detalle.fundas_te = item.valor
        
        db.add(detalle)
        
        db.commit()
        db.refresh(factura)
        
        return factura
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error al crear factura: {str(e)}")

def create_factura_from_form(
    db: Session, 
    form_data: FacturaFormData, 
    admin_user: User
) -> Facturacion:
    """
    Crea una factura a partir de los datos del formulario
    """
    # Procesar items del formulario
    items = process_factura_form_data(form_data)
    
    if not items:
        raise ValueError("Debe ingresar al menos un item con valor mayor a 0")
    
    # Crear datos de factura
    factura_data = FacturacionCreate(
        monto_pagar=Decimal('0'),  # Se calculará automáticamente
        monto_base=Decimal('0'),   # Se calculará automáticamente
        iva=form_data.iva_porcentaje or Decimal('19.0'),
        valor_iva=Decimal('0'),    # Se calculará automáticamente
        descripcion=form_data.descripcion,
        fecha_vencimiento=form_data.fecha_vencimiento,
        items=items,
        aplica_iva=form_data.aplica_iva
    )
    
    return create_factura_with_details(db, factura_data, admin_user)

def get_factura_by_id(db: Session, factura_id: int, user: User) -> Optional[Facturacion]:
    """
    Obtiene una factura por ID con control de acceso
    """
    factura = db.query(Facturacion).filter(Facturacion.id == factura_id).first()
    
    if not factura:
        return None
    
    # Verificar permisos de acceso
    if not can_access_factura(user, factura):
        raise HTTPException(status_code=403, detail="No tiene permisos para acceder a esta factura")
    
    return factura

def can_access_factura(user: User, factura: Facturacion) -> bool:
    """
    Verifica si un usuario puede acceder a una factura específica
    """
    # Admin y veterinarios pueden ver todas las facturas
    if role_service.is_admin(user) or has_veterinario_role(user):
        return True
    
    # Los clientes solo pueden ver sus propias facturas
    return factura.cliente_id == user.id

def has_veterinario_role(user: User) -> bool:
    """
    Verifica si el usuario tiene rol de veterinario
    """
    if not user.roles:
        return False
    
    return any(role.name.lower() in ['veterinario', 'veterinaria', 'admin'] for role in user.roles)

def list_facturas(
    db: Session, 
    user: User, 
    cliente_id: Optional[int] = None,
    skip: int = 0, 
    limit: int = 100,
    estado: Optional[str] = None,
    fecha_desde: Optional[datetime] = None,
    fecha_hasta: Optional[datetime] = None
) -> Tuple[List[Facturacion], int]:
    """
    Lista facturas con paginación y filtros
    
    Args:
        db: Sesión de la base de datos
        user: Usuario autenticado
        cliente_id: ID del cliente para filtrar (solo para admin/veterinario, opcional)
        skip: Número de registros a omitir
        limit: Número máximo de registros
        estado: Filtrar por estado
        fecha_desde: Filtrar desde fecha
        fecha_hasta: Filtrar hasta fecha
    
    Returns:
        Tupla con (lista de facturas, total de registros)
    """
    # Construir query base
    query = db.query(Facturacion)
    
    # Verificar si el usuario es admin o veterinario
    is_admin_or_vet = role_service.is_admin(user) or has_veterinario_role(user)
    
    # Aplicar filtros de acceso
    if not is_admin_or_vet:
        # Los clientes solo ven sus propias facturas (ignoran cliente_id si lo envían)
        query = query.filter(Facturacion.cliente_id == user.id)
    else:
        # Admin y veterinarios pueden ver todas las facturas o filtrar por cliente_id
        if cliente_id is not None:
            # Verificar que el cliente exista
            cliente = db.query(User).filter(User.id == cliente_id).first()
            if not cliente:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Cliente no encontrado"
                )
            query = query.filter(Facturacion.cliente_id == cliente_id)
    
    # Aplicar filtros opcionales
    if estado:
        query = query.filter(Facturacion.estado == estado)
    
    if fecha_desde:
        query = query.filter(Facturacion.fecha_generacion >= fecha_desde)
    
    if fecha_hasta:
        query = query.filter(Facturacion.fecha_generacion <= fecha_hasta)
    
    # Obtener total de registros
    total = query.count()
    
    # Aplicar paginación y ordenamiento
    facturas = query.order_by(Facturacion.fecha_generacion.desc()).offset(skip).limit(limit).all()
    
    return facturas, total

def get_my_facturas(
    db: Session, 
    user: User, 
    skip: int = 0, 
    limit: int = 100,
    estado: Optional[str] = None,
    fecha_desde: Optional[datetime] = None,
    fecha_hasta: Optional[datetime] = None
) -> Tuple[List[Facturacion], int]:
    """
    Obtiene las facturas del cliente autenticado.
    Este método es exclusivo para clientes y siempre filtra por el ID del usuario autenticado.
    
    Args:
        db: Sesión de la base de datos
        user: Usuario autenticado (cliente)
        skip: Número de registros a omitir (paginación)
        limit: Número máximo de registros a devolver (paginación)
        estado: Filtrar por estado (opcional)
        fecha_desde: Filtrar desde fecha (opcional)
        fecha_hasta: Filtrar hasta fecha (opcional)
    
    Returns:
        Tupla con (lista de facturas, total de registros)
    """
    # Construir query base filtrando exclusivamente por el ID del cliente autenticado
    query = db.query(Facturacion).filter(Facturacion.cliente_id == user.id)
    
    # Aplicar filtros opcionales
    if estado:
        query = query.filter(Facturacion.estado == estado)
    
    if fecha_desde:
        query = query.filter(Facturacion.fecha_generacion >= fecha_desde)
    
    if fecha_hasta:
        query = query.filter(Facturacion.fecha_generacion <= fecha_hasta)
    
    # Obtener total de registros
    total = query.count()
    
    # Aplicar paginación y ordenamiento
    facturas = query.order_by(Facturacion.fecha_generacion.desc()).offset(skip).limit(limit).all()
    
    return facturas, total

def update_factura(
    db: Session, 
    factura_id: int, 
    factura_update: FacturacionUpdate, 
    user: User
) -> Facturacion:
    """
    Actualiza una factura existente
    """
    factura = get_factura_by_id(db, factura_id, user)
    
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    
    # Verificar que solo se puedan actualizar ciertos campos
    allowed_fields = ['descripcion', 'estado', 'fecha_pago', 'fecha_vencimiento']
    
    for field, value in factura_update.dict(exclude_unset=True).items():
        if field in allowed_fields and hasattr(factura, field):
            setattr(factura, field, value)
    
    db.commit()
    db.refresh(factura)
    
    return factura

def delete_factura(db: Session, factura_id: int, user: User) -> bool:
    """
    Elimina una factura (solo si está pendiente)
    """
    factura = get_factura_by_id(db, factura_id, user)
    
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    
    # Solo se pueden eliminar facturas pendientes
    if factura.estado != EstadoFactura.pendiente:
        raise HTTPException(status_code=400, detail="Solo se pueden eliminar facturas pendientes")
    
    # Verificar permisos de eliminación
    if not (user.is_admin or has_veterinario_role(user)):
        raise HTTPException(status_code=403, detail="No tiene permisos para eliminar facturas")
    
    try:
        db.delete(factura)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al eliminar factura: {str(e)}")

def get_factura_summary(factura: Facturacion) -> Dict[str, Any]:
    """
    Obtiene un resumen de la factura con cálculos de IVA
    """
    return {
        "id": factura.id,
        "id_factura": factura.id_factura,
        "monto_base": factura.monto_base or Decimal('0'),
        "iva_porcentaje": factura.iva or Decimal('19.0'),
        "valor_iva": factura.valor_iva or Decimal('0'),
        "monto_total": factura.monto_pagar,
        "aplica_iva": factura.aplica_iva,
        "estado": factura.estado.value,
        "descripcion": factura.descripcion,
        "fecha_generacion": factura.fecha_generacion,
        "fecha_pago": factura.fecha_pago,
        "fecha_vencimiento": factura.fecha_vencimiento,
        "cliente_id": factura.cliente_id
    }

def get_factura_detalles(factura: Facturacion) -> List[Dict[str, Any]]:
    """
    Obtiene los detalles de una factura
    """
    detalles = []
    
    for detalle in factura.detalles:
        detalle_dict = {
            "id": detalle.id,
            "embrio_fresco": detalle.embrio_fresco or Decimal('0'),
            "embrio_congelado": detalle.embrio_congelado or Decimal('0'),
            "material_campo": detalle.material_campo or Decimal('0'),
            "nitrogeno": detalle.nitrogeno or Decimal('0'),
            "mensajeria": detalle.mensajeria or Decimal('0'),
            "pajilla_semen": detalle.pajilla_semen or Decimal('0'),
            "fundas_te": detalle.fundas_te or Decimal('0'),
            "iva_porcentaje": detalle.iva or Decimal('19.0')
        }
        detalles.append(detalle_dict)
    
    return detalles

def get_factura_completa(db: Session, factura_id: int, user: User) -> Dict[str, Any]:
    """
    Obtiene una factura completa con sus detalles
    """
    factura = get_factura_by_id(db, factura_id, user)
    
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    
    return {
        "factura": get_factura_summary(factura),
        "detalles": get_factura_detalles(factura),
        "pagos": [
            {
                "id": pago.id,
                "monto": pago.monto,
                "estado": pago.estado.value,
                "metodo_pago": pago.metodo_pago,
                "fecha_pago": pago.fecha_pago
            }
            for pago in factura.pagos
        ]
    }