from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape
import os
from datetime import datetime
from decimal import Decimal

from app.models.facturacion import Facturacion
from app.models.user import User


def _get_templates_env() -> Environment:
    """Configura el entorno de Jinja2 para cargar templates"""
    templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
    env = Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=select_autoescape(["html", "xml"]),
        enable_async=False,
    )
    return env


def fetch_factura_context(db: Session, factura_id: int, current_user: Optional[User] = None) -> Dict[str, Any]:
    """
    Obtiene todos los datos necesarios para generar el PDF de la factura
    """
    # Obtener la factura con sus relaciones
    factura = db.query(Facturacion).filter(Facturacion.id == factura_id).first()
    if not factura:
        raise ValueError(f"Factura con ID {factura_id} no encontrada")
    
    # Obtener el cliente
    cliente = db.query(User).filter(User.id == factura.cliente_id).first()
    if not cliente:
        raise ValueError(f"Cliente con ID {factura.cliente_id} no encontrado")
    
    # Obtener los detalles de la factura
    detalles = factura.detalles
    
    # Formatear fechas
    fecha_generacion = factura.fecha_generacion.strftime("%d/%m/%Y") if factura.fecha_generacion else "N/A"
    fecha_pago = factura.fecha_pago.strftime("%d/%m/%Y") if factura.fecha_pago else "No pagada"
    fecha_vencimiento = factura.fecha_vencimiento.strftime("%d/%m/%Y") if factura.fecha_vencimiento else "N/A"
    
    # Formatear montos con separadores de miles
    def format_currency(amount: Decimal) -> str:
        """Formatea un monto como moneda colombiana"""
        if amount is None:
            return "$0,00"
        # Convertir a entero para evitar decimales innecesarios
        amount_int = int(amount)
        # Formatear con separadores de miles
        formatted = f"{amount_int:,}".replace(",", ".")
        return f"${formatted},00"
    
    # Obtener los items de la factura desde los detalles
    items = []
    if detalles:
        detalle = detalles[0]  # Solo hay un detalle por factura
        if detalle.embrio_fresco > 0:
            items.append({"nombre": "Embrión Fresco", "valor": format_currency(detalle.embrio_fresco)})
        if detalle.embrio_congelado > 0:
            items.append({"nombre": "Embrión Congelado", "valor": format_currency(detalle.embrio_congelado)})
        if detalle.material_campo > 0:
            items.append({"nombre": "Material de Campo", "valor": format_currency(detalle.material_campo)})
        if detalle.nitrogeno > 0:
            items.append({"nombre": "Nitrógeno", "valor": format_currency(detalle.nitrogeno)})
        if detalle.mensajeria > 0:
            items.append({"nombre": "Mensajería", "valor": format_currency(detalle.mensajeria)})
        if detalle.pajilla_semen > 0:
            items.append({"nombre": "Pajilla de Semen", "valor": format_currency(detalle.pajilla_semen)})
        if detalle.fundas_te > 0:
            items.append({"nombre": "Fundas T.E", "valor": format_currency(detalle.fundas_te)})
    
    # Formatear ID del cliente con ceros a la izquierda
    cliente_id_formatted = f"{cliente.id:05d}"
    
    # Construir el contexto para el template
    context = {
        "factura": {
            "id_factura": factura.id_factura,
            "fecha_generacion": fecha_generacion,
            "fecha_pago": fecha_pago,
            "fecha_vencimiento": fecha_vencimiento,
            "estado": factura.estado.value.title(),
            "descripcion": factura.descripcion or "Sin descripción",
            "monto_base": format_currency(factura.monto_base),
            "iva_porcentaje": f"{factura.iva}%" if factura.iva else "0%",
            "valor_iva": format_currency(factura.valor_iva),
            "monto_total": format_currency(factura.monto_pagar),
            "aplica_iva": "Sí" if factura.aplica_iva else "No"
        },
        "cliente": {
            "nombre": cliente.full_name,
            "id_formatted": cliente_id_formatted,
            "email": cliente.email,
            "telefono": cliente.phone,
            "documento": cliente.number_document
        },
        "items": items
    }
    
    return context


def render_factura_html(db: Session, factura_id: int, current_user: Optional[User] = None) -> str:
    """
    Renderiza el HTML de la factura usando el template
    """
    try:
        # Obtener el contexto de datos
        context = fetch_factura_context(db, factura_id, current_user)
        
        # Configurar Jinja2
        env = _get_templates_env()
        template = env.get_template("factura.html")
        
        # Renderizar el HTML
        html_content = template.render(**context)
        
        return html_content
        
    except Exception as e:
        raise ValueError(f"Error renderizando HTML de factura: {str(e)}")


def html_to_pdf_bytes(html: str) -> bytes:
    """
    Convierte HTML a PDF usando Playwright (mismo patrón que informes)
    """
    from playwright.sync_api import sync_playwright, Error as PlaywrightError
    import logging
    
    logger = logging.getLogger(__name__)
    
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except PlaywrightError:
            # Fallback a navegadores del sistema si no se descargó Chromium de Playwright
            try:
                browser = p.chromium.launch(channel="msedge")
            except PlaywrightError:
                browser = p.chromium.launch(channel="chrome")
        
        page = browser.new_page()
        
        # Cargar HTML
        page.set_content(html, wait_until="networkidle", timeout=30000)
        
        # Emular media 'print' para respetar estilos @media print
        page.emulate_media(media="print")
        
        # Configurar PDF con tamaño carta
        pdf_bytes = page.pdf(
            format="Letter",
            print_background=True,
            margin={"top": "0.5in", "right": "0.5in", "bottom": "0.5in", "left": "0.5in"},
            prefer_css_page_size=True,
        )
        
        browser.close()
        return pdf_bytes
