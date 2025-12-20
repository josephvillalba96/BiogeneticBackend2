from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime
from app.models.facturacion import Facturacion, Pagos, EstadoFactura, EstadoPago
from app.models.user import User, DocumentType
from app.schemas.pagos_schema import PagoPSECreate, PagoDaviplataCreate, PaymentNotificationData
from app.config import settings
import logging
import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)

class EpaycoConfigService:
    """Servicio de configuración de ePayco - Usa API Apify directamente"""
    
    def __init__(self):
        self.api_key = getattr(settings, 'EPAYCO_PUBLIC_KEY', '')
        self.private_key = getattr(settings, 'EPAYCO_PRIVATE_KEY', '')
        self.apify_base_url = getattr(settings, 'EPAYCO_APIFY_BASE_URL', '').rstrip('/')
        self._token = None
        self._token_expires_at = None
    
    def _get_auth_token(self) -> Optional[str]:
        """
        Obtener token JWT de ePayco usando Basic Auth
        """
        try:
            apify_base_url = getattr(settings, 'EPAYCO_APIFY_BASE_URL', '').rstrip('/')
            if not apify_base_url:
                logger.error("EPAYCO_APIFY_BASE_URL no configurada")
                return None
            
            # Intentar múltiples endpoints de autenticación
            auth_endpoints = [
                f"{apify_base_url}/auth/token",
                f"{apify_base_url}/token",
                f"{apify_base_url}/auth/login",
                f"{apify_base_url}/login"
            ]
            
            for endpoint in auth_endpoints:
                try:
                    response = requests.post(
                        endpoint,
                        auth=HTTPBasicAuth(
                            getattr(settings, 'EPAYCO_PUBLIC_KEY', ''),
                            getattr(settings, 'EPAYCO_PRIVATE_KEY', '')
                        ),
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        token = data.get('token') or data.get('access_token') or data.get('data', {}).get('token')
                        if token:
                            logger.info("✅ Token JWT obtenido exitosamente")
                            return token
                except Exception as e:
                    logger.debug(f"Error al intentar endpoint {endpoint}: {str(e)}")
                    continue
            
            logger.warning("⚠️ No se pudo obtener token JWT de ningún endpoint, usando Basic Auth directo")
            return None
            
        except Exception as e:
            logger.error(f"Error al obtener token de ePayco: {str(e)}")
            return None
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """
        Obtener headers de autenticación (JWT o Basic Auth)
        """
        token = self._get_auth_token()
        if token:
            return {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        else:
            # Fallback a Basic Auth - construir manualmente el header
            import base64
            api_key = getattr(settings, 'EPAYCO_PUBLIC_KEY', '')
            private_key = getattr(settings, 'EPAYCO_PRIVATE_KEY', '')
            credentials = f"{api_key}:{private_key}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            return {
                "Authorization": f"Basic {encoded_credentials}",
                "Content-Type": "application/json"
            }
    
    def get_pse_banks(self) -> Dict[str, Any]:
        """
        Obtener lista de entidades bancarias disponibles para PSE desde la API Apify de ePayco
        NO retorna datos estáticos - todo viene directamente de la API
        """
        try:
            apify_base_url = getattr(settings, 'EPAYCO_APIFY_BASE_URL', '').rstrip('/')
            if not apify_base_url:
                logger.error("EPAYCO_APIFY_BASE_URL no configurada")
                return {
                    "success": False,
                    "banks": [],
                    "message": "EPAYCO_APIFY_BASE_URL no está configurada"
                }
            
            # Intentar múltiples endpoints posibles para obtener bancos
            bank_endpoints = [
                f"{apify_base_url}/payment/banks",
                f"{apify_base_url}/banks",
                f"{apify_base_url}/payment/banks/pse",
                f"{apify_base_url}/banks/pse"
            ]
            
            headers = self._get_auth_headers()
            
            for endpoint in bank_endpoints:
                try:
                    logger.info(f"Intentando obtener bancos desde: {endpoint}")
                    response = requests.get(endpoint, headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        logger.info(f"✅ Respuesta recibida de ePayco API: {data}")
                        
                        # Extraer bancos de diferentes estructuras posibles
                        banks_data = None
                        if isinstance(data, list):
                            banks_data = data
                        elif isinstance(data, dict):
                            banks_data = data.get('data') or data.get('banks') or data.get('bankList') or []
                        
                        if banks_data and len(banks_data) > 0:
                            # Formatear bancos
                            formatted_banks = self._format_banks_data(banks_data)
                            logger.info(f"✅ Bancos formateados: {len(formatted_banks)} de {len(banks_data)}")
                            
                            return {
                                "success": True,
                                "banks": formatted_banks,
                                "message": f"Entidades bancarias obtenidas exitosamente desde ePayco API: {len(formatted_banks)}"
                            }
                        else:
                            logger.warning(f"⚠️ Respuesta vacía o sin bancos desde {endpoint}")
                    else:
                        logger.debug(f"Endpoint {endpoint} retornó status {response.status_code}")
                        
                except Exception as e:
                    logger.debug(f"Error al intentar endpoint {endpoint}: {str(e)}")
                    continue
            
            # Si todos los endpoints fallan, retornar error (NO datos estáticos)
            logger.error("❌ No se pudo obtener bancos de ningún endpoint de ePayco")
            return {
                "success": False,
                "banks": [],
                "message": "No se pudo obtener la lista de bancos desde la API de ePayco. Por favor, intente más tarde."
            }
            
        except Exception as e:
            logger.error(f"Error al obtener entidades bancarias: {str(e)}")
            return {
                "success": False,
                "banks": [],
                "message": f"Error al obtener entidades bancarias: {str(e)}"
            }
    
    def _format_banks_data(self, banks_data: list) -> list:
        """
        Formatear datos de bancos desde la respuesta de ePayco
        Maneja diferentes estructuras posibles de respuesta
        """
        formatted = []
        
        for bank in banks_data:
            try:
                # Intentar extraer bank_id de diferentes campos posibles
                bank_id = None
                if isinstance(bank, dict):
                    bank_id = bank.get('id') or bank.get('bankCode') or bank.get('code') or bank.get('bank_id')
                    # Si bankCode es numérico, convertirlo a string
                    if bank_id and not isinstance(bank_id, str):
                        bank_id = str(bank_id)
                    
                    # Intentar extraer nombre de diferentes campos posibles
                    bank_name = bank.get('bankName') or bank.get('name') or bank.get('bank') or bank.get('nombre')
                    
                    # Si no hay nombre, intentar usar description
                    if not bank_name:
                        bank_name = bank.get('description') or bank.get('descripcion') or f"Banco {bank_id}"
                    
                    # Filtrar bancos placeholder o inválidos
                    if bank_id and bank_name and bank_name.lower() not in ['placeholder', 'test', 'banco test']:
                        formatted.append({
                            "id": bank_id,
                            "name": bank_name.upper() if isinstance(bank_name, str) else str(bank_name).upper(),
                            "code": bank_id,
                            "description": bank.get('description') or bank.get('descripcion') or bank_name
                        })
                elif isinstance(bank, str):
                    # Si es solo un string, usarlo como código y nombre
                    formatted.append({
                        "id": bank,
                        "name": bank,
                        "code": bank,
                        "description": bank
                    })
                    
            except Exception as e:
                logger.warning(f"Error al formatear banco: {bank}, error: {str(e)}")
                continue
        
        return formatted

class PSEPaymentService:
    """Servicio para procesamiento de pagos PSE usando la API Apify de ePayco directamente"""
    
    def __init__(self, db: Session):
        self.db = db
        self.api_key = getattr(settings, 'EPAYCO_PUBLIC_KEY', '')
        self.private_key = getattr(settings, 'EPAYCO_PRIVATE_KEY', '')
        self.apify_base_url = getattr(settings, 'EPAYCO_APIFY_BASE_URL', '').rstrip('/')
        self._token = None
        self._token_expires_at = None
    
    def _get_auth_token(self) -> str:
        """Obtener token JWT de ePayco usando Basic Auth"""
        from datetime import timedelta
        
        # Verificar si el token existe y no ha expirado
        if self._token and self._token_expires_at and datetime.now() < self._token_expires_at:
            return self._token
        
        try:
            logger.info("Obteniendo nuevo token JWT de ePayco...")
            
            # Intentar diferentes endpoints comunes de autenticación
            auth_endpoints = [
                "/auth/token",
                "/token",
                "/auth/login",
                "/login"
            ]
            
            token_data = None
            last_error = None
            
            for endpoint in auth_endpoints:
                try:
                    auth_url = f"{self.apify_base_url}{endpoint}"
                    logger.debug(f"Intentando autenticación en: {auth_url}")
                    
                    response = requests.post(
                        auth_url,
                        auth=HTTPBasicAuth(self.api_key, self.private_key),
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        token_data = response.json()
                        logger.info(f"✅ Token JWT obtenido exitosamente desde: {endpoint}")
                        break
                    elif response.status_code == 404:
                        logger.debug(f"Endpoint {endpoint} no existe (404), probando siguiente...")
                        continue
                    else:
                        logger.warning(f"Respuesta inesperada desde {endpoint}: {response.status_code}")
                        last_error = f"Status {response.status_code}: {response.text[:200]}"
                        continue
                except requests.exceptions.RequestException as e:
                    logger.warning(f"Error de conexión con {endpoint}: {str(e)}")
                    last_error = str(e)
                    continue
            
            if token_data:
                self._token = token_data.get('token', '') or token_data.get('access_token', '') or token_data.get('jwt', '')
                if not self._token:
                    logger.warning(f"Token no encontrado en respuesta. Respuesta completa: {token_data}")
                    raise ValueError("No se encontró token en la respuesta de ePayco")
                
                # Token expira en 1 hora, pero renovamos 5 minutos antes
                self._token_expires_at = datetime.now() + timedelta(minutes=55)
                logger.info("✅ Token JWT obtenido y almacenado exitosamente")
                return self._token
            else:
                error_msg = last_error or "No se pudo obtener token de ningún endpoint"
                logger.error(f"Error al obtener token: {error_msg}")
                raise ValueError(f"Error al obtener token de ePayco: {error_msg}")
        except Exception as e:
            logger.error(f"Error al obtener token JWT: {str(e)}")
            raise ValueError(f"Error al obtener token de ePayco: {str(e)}")
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """
        Obtener headers con autenticación JWT o Basic Auth como fallback
        """
        try:
            token = self._get_auth_token()
            return {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        except Exception as e:
            logger.warning(f"No se pudo obtener token JWT, usando Basic Auth directamente: {str(e)}")
            # Fallback: usar Basic Auth directamente
            import base64
            credentials = f"{self.api_key}:{self.private_key}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            return {
                "Authorization": f"Basic {encoded_credentials}",
                "Content-Type": "application/json"
            }
    
    async def create_pse_payment(self, factura_id: int, user: User, request_ip: str, pse_data: PagoPSECreate) -> Dict[str, Any]:
        """
        Crear pago PSE para una factura específica usando la API Apify de ePayco
        """
        try:
            # 1. Obtener factura
            factura = self.get_factura(factura_id)
            if not factura:
                raise ValueError(f"Factura con ID {factura_id} no encontrada")
            
            # 2. Verificar que la factura no esté pagada
            if factura.estado == EstadoFactura.pagado:
                raise ValueError("La factura ya está pagada")
            
            # 3. Verificar si ya existe un pago pendiente/procesando para esta factura
            existing_payment = self.db.query(Pagos).filter(
                Pagos.factura_id == factura.id,
                Pagos.estado.in_([EstadoPago.pendiente, EstadoPago.procesando])
            ).first()
            
            if existing_payment:
                logger.info(f"Ya existe un pago pendiente/procesando para la factura {factura_id}: {existing_payment.id}")
                return {
                    "pago_id": existing_payment.id,
                    "ref_payco": existing_payment.ref_payco,
                    "bank_url": existing_payment.bank_url,
                    "bank_name": existing_payment.bank_name,
                    "status": existing_payment.estado.value,
                    "message": "Ya existe un pago en proceso para esta factura."
                }
            
            # 4. Preparar datos para ePayco
            payment_data = self.prepare_pse_data(factura, user, request_ip, pse_data)
            
            # 5. GUARDAR PAGO ANTES de enviar a ePayco (solución 3)
            # Esto asegura que el pago siempre esté en la BD, incluso si hay timeout
            logger.info("Guardando pago en BD antes de enviar a ePayco...")
            pago_inicial = self.save_payment_initial(factura, payment_data, user)
            logger.info(f"Pago inicial guardado: {pago_inicial.id}")
            
            # 6. Crear pago en ePayco usando la API Apify (solución 2: asíncrono)
            api_url = f"{self.apify_base_url}/payment/process/pse"
            headers = self._get_auth_headers()
            
            # Asegurar que tax y taxBase sean enteros (no floats, no strings)
            # ePayco rechaza floats explícitamente
            if 'tax' in payment_data:
                if isinstance(payment_data['tax'], float):
                    payment_data['tax'] = int(round(payment_data['tax']))
                elif isinstance(payment_data['tax'], str):
                    payment_data['tax'] = int(float(payment_data['tax']))
                # Si ya es int, dejarlo como está
            if 'taxBase' in payment_data:
                if isinstance(payment_data['taxBase'], float):
                    payment_data['taxBase'] = int(round(payment_data['taxBase']))
                elif isinstance(payment_data['taxBase'], str):
                    payment_data['taxBase'] = int(float(payment_data['taxBase']))
                # Si ya es int, dejarlo como está
            
            # Logging detallado de tipos antes de enviar
            logger.info(f"Enviando pago PSE a ePayco API: {api_url}")
            logger.info(f"Tipo de 'tax': {type(payment_data.get('tax'))}, valor: {payment_data.get('tax')}")
            logger.info(f"Tipo de 'taxBase': {type(payment_data.get('taxBase'))}, valor: {payment_data.get('taxBase')}")
            logger.info(f"Tipo de 'value': {type(payment_data.get('value'))}, valor: {payment_data.get('value')}")
            logger.debug(f"Datos del pago: {payment_data}")
            
            # Enviar con json= para que requests maneje la serialización correctamente
            # CRÍTICO: El bank_url DEBE venir en la respuesta inicial de ePayco
            # Usar timeout largo (180 segundos) para dar tiempo a ePayco de responder
            # Si hay timeout, intentar consultar periódicamente hasta obtener el bank_url
            try:
                # Intentar con timeout de 180 segundos (3 minutos)
                # ePayco puede tardar en responder, pero la transacción se crea
                response = requests.post(
                    api_url,
                    json=payment_data,
                    headers=headers,
                    timeout=180  # 3 minutos para dar tiempo a ePayco
                )
            except requests.exceptions.Timeout:
                # Si hay timeout, ePayco puede haber creado la transacción pero no respondió a tiempo
                # Intentar consultar periódicamente hasta obtener el bank_url
                logger.warning(f"Timeout al crear pago PSE (ePayco tardó más de 180s). Consultando periódicamente...")
                
                # Intentar consultar hasta 5 veces con intervalos de 5 segundos
                max_attempts = 5
                for attempt in range(1, max_attempts + 1):
                    try:
                        logger.info(f"Intento {attempt}/{max_attempts}: Consultando pago por invoice...")
                        import time
                        time.sleep(5)  # Esperar 5 segundos entre intentos
                        
                        payment_data_from_epayco = self.query_payment_by_invoice(factura.id_factura)
                        if payment_data_from_epayco:
                            # Verificar si tiene urlbanco
                            bank_url = payment_data_from_epayco.get('urlbanco') or payment_data_from_epayco.get('bank_url') or payment_data_from_epayco.get('url')
                            if bank_url:
                                # Extraer datos necesarios
                                # Si payment_data_from_epayco tiene estructura completa con 'data', extraerla
                                if 'data' in payment_data_from_epayco and isinstance(payment_data_from_epayco['data'], dict):
                                    epayco_data = payment_data_from_epayco['data']
                                else:
                                    epayco_data = payment_data_from_epayco
                                
                                # Actualizar pago con los datos obtenidos
                                pago_actualizado = self.update_payment_with_response(pago_inicial, epayco_data, payment_data)
                                logger.info(f"✅ Pago actualizado desde ePayco después de timeout: {pago_actualizado.id}, bank_url obtenido")
                                
                                return {
                                    "pago_id": pago_actualizado.id,
                                    "ref_payco": pago_actualizado.ref_payco or "Pendiente",
                                    "bank_url": pago_actualizado.bank_url or "",
                                    "bank_name": pago_actualizado.bank_name or "PSE",
                                    "status": pago_actualizado.estado.value,
                                    "message": "Pago creado exitosamente. Link de pago obtenido."
                                }
                            else:
                                logger.debug(f"Intento {attempt}: Pago encontrado pero sin urlbanco aún")
                    except Exception as e:
                        logger.debug(f"Intento {attempt} falló: {str(e)}")
                        continue
                
                # Si después de todos los intentos no se obtuvo bank_url, retornar error
                # porque sin bank_url el usuario no puede pagar
                logger.error(f"No se pudo obtener bank_url después de {max_attempts} intentos")
                pago_inicial.estado = EstadoPago.fallido
                pago_inicial.response_message = "Timeout: No se pudo obtener link de pago de ePayco"
                self.db.commit()
                raise ValueError("Timeout al crear pago en ePayco. No se pudo obtener el link de pago. Por favor, intenta nuevamente.")
            except Exception as e:
                # Si hay otro error, actualizar el pago a fallido
                logger.error(f"Error al enviar pago a ePayco: {str(e)}")
                pago_inicial.estado = EstadoPago.fallido
                pago_inicial.response_message = f"Error al enviar a ePayco: {str(e)}"
                self.db.commit()
                raise ValueError(f"Error al crear pago en ePayco: {str(e)}")
            
            if response.status_code not in [200, 201]:
                error_text = response.text
                logger.error(f"Error al crear pago en ePayco: {response.status_code} - {error_text}")
                
                # Intentar extraer detalles del error
                try:
                    error_data = response.json()
                    error_details = error_data.get('data', {}).get('error', {})
                    error_codes = error_details.get('errores', [])
                    if error_codes:
                        error_messages = [err.get('errorMessage', '') for err in error_codes]
                        full_error = f"{error_data.get('textResponse', 'Error')} - Detalles: {', '.join(error_messages)}"
                    else:
                        full_error = error_data.get('textResponse', error_text)
                except:
                    full_error = error_text
                
                raise ValueError(f"Error al crear pago en ePayco: {full_error}")
            
            pse_response = response.json()
            logger.info(f"Respuesta de ePayco API: {pse_response}")
            
            # Verificar si la respuesta indica error
            # success es booleano: true (éxito) o false (error)
            if pse_response.get('success') != True:
                error_msg = pse_response.get('textResponse', 'Error desconocido')
                error_data = pse_response.get('data', {})
                error_details = error_data.get('error', {})
                error_codes = error_details.get('errores', [])
                
                # Extraer códigos de error
                error_code_list = [err.get('codError', '') for err in error_codes]
                
                # Si es error E035 (factura duplicada), buscar el pago existente
                if 'E035' in error_code_list:
                    logger.warning(f"Error E035: Factura duplicada. Buscando pago existente para factura {factura_id}")
                    
                    # Buscar pago existente por factura_id
                    existing_payment = self.db.query(Pagos).filter(
                        Pagos.factura_id == factura.id
                    ).order_by(Pagos.fecha_pago.desc()).first()
                    
                    if existing_payment and existing_payment.bank_url:
                        logger.info(f"Pago existente encontrado: {existing_payment.id}, ref_payco: {existing_payment.ref_payco}")
                        return {
                            "pago_id": existing_payment.id,
                            "ref_payco": existing_payment.ref_payco,
                            "bank_url": existing_payment.bank_url,
                            "bank_name": existing_payment.bank_name or "PSE",
                            "status": existing_payment.estado.value,
                            "message": "Ya existe un pago para esta factura. Usando el pago existente."
                        }
                    else:
                        logger.warning(f"No se encontró pago existente con bank_url para factura {factura_id}")
                
                logger.error(f"ePayco rechazó la solicitud: {error_msg}")
                raise ValueError(f"Error al crear pago en ePayco: {error_msg}")
            
            # Extraer datos de la respuesta
            # La respuesta tiene estructura: { "success": true, "data": { ref_payco, urlbanco, ... } }
            response_data = pse_response.get('data', {})
            
            # Extraer ref_payco (viene como número, convertir a string)
            ref_payco = response_data.get('ref_payco') or response_data.get('refPayco')
            if ref_payco:
                ref_payco = str(ref_payco)  # Convertir a string si es número
            
            if not ref_payco:
                logger.error(f"La respuesta de ePayco no contiene ref_payco: {pse_response}")
                raise ValueError("Error al crear pago en ePayco: respuesta inválida - no se encontró ref_payco")
            
            # Extraer urlbanco (bank_url)
            # ePayco retorna: data.urlbanco
            bank_url = response_data.get('urlbanco') or response_data.get('bank_url') or response_data.get('url')
            
            if not bank_url:
                logger.error(f"La respuesta de ePayco no contiene urlbanco. response_data: {response_data}")
                raise ValueError("Error al crear pago en ePayco: No se recibió el link de pago del banco (urlbanco).")
            
            # 7. Actualizar pago inicial con la respuesta de ePayco
            pago = self.update_payment_with_response(pago_inicial, response_data, payment_data)
            
            logger.info(f"✅ Pago PSE creado exitosamente: pago_id={pago.id}, ref_payco={ref_payco}, bank_url={pago.bank_url}")
            
            return {
                "pago_id": pago.id,
                "ref_payco": ref_payco,
                "bank_url": pago.bank_url,
                "bank_name": pago.bank_name or "PSE",
                "status": pago.estado.value,
                "message": "Pago PSE creado exitosamente. Redirigir al banco para completar el pago."
            }
            
        except Exception as e:
            logger.error(f"Error al crear pago PSE: {str(e)}")
            raise ValueError(f"Error al procesar pago PSE: {str(e)}")
    
    def get_factura(self, factura_id: int) -> Optional[Facturacion]:
        """Obtener factura por ID"""
        return self.db.query(Facturacion).filter(Facturacion.id == factura_id).first()
    
    def prepare_pse_data(self, factura: Facturacion, user: User, request_ip: str, pse_data: PagoPSECreate) -> Dict[str, Any]:
        """
        Preparar datos para envío a ePayco PSE
        """
        # Usar los valores de IVA de la factura
        monto_base = factura.monto_base or Decimal('0')
        valor_iva = factura.valor_iva or Decimal('0')
        monto_total = factura.monto_pagar
        
        # Si no hay monto_base calculado, usar el total como base
        if monto_base == 0:
            monto_base = monto_total
            valor_iva = Decimal('0')
        
        # url_response: URL donde ePayco REDIRIGE AL USUARIO después del pago (GET request)
        # El endpoint /api/pagos/response retorna HTML que se muestra al usuario
        # Puede estar en el backend (como ahora) o en el frontend (mejor UX)
        url_response = getattr(settings, 'PAYMENT_RESPONSE_URL', '')
        if not url_response:
            # Si no está configurada, construir URL del backend que retorna HTML
            url_response = f"{getattr(settings, 'BASE_URL', 'http://localhost:8000')}/api/pagos/response"
        
        # url_confirmation: URL del WEBHOOK que ePayco llama automáticamente (POST request, servidor a servidor)
        # DEBE estar en el backend porque es una comunicación servidor-servidor
        # El endpoint /api/pagos/confirmation recibe datos en el body y actualiza el estado del pago
        url_confirmation = getattr(settings, 'PAYMENT_CONFIRMATION_URL', '')
        if not url_confirmation:
            # Construir URL del backend para el webhook
            # Extraer la base URL del backend desde PAYMENT_RESPONSE_URL o usar BASE_URL
            if url_response and url_response.startswith('http'):
                # Extraer dominio del backend desde url_response
                from urllib.parse import urlparse
                parsed = urlparse(url_response)
                api_base = f"{parsed.scheme}://{parsed.netloc}"
            else:
                api_base = getattr(settings, 'BASE_URL', 'http://localhost:8000')
            url_confirmation = f"{api_base}/api/pagos/confirmation"
        
        # Validar que se haya seleccionado un banco
        if not pse_data.bank_id:
            raise ValueError("Debe seleccionar un banco para realizar el pago PSE")
        
        # Separar nombre y apellido del full_name
        name_parts = pse_data.full_name.split(maxsplit=1)
        name = name_parts[0] if name_parts else "Cliente"
        last_name = name_parts[1] if len(name_parts) > 1 else ""
        
        # Convertir Decimal a int (números enteros, no floats)
        # ePayco rechaza floats, necesita enteros
        tax_int = int(round(float(valor_iva))) if valor_iva > 0 else 0
        tax_base_int = int(round(float(monto_base))) if monto_base > 0 else 0
        value_int = int(round(float(monto_total)))
        
        # Validar que value = taxBase + tax
        if value_int != (tax_base_int + tax_int):
            # Recalcular value para que coincida exactamente
            value_int = tax_base_int + tax_int
            logger.warning(f"Valor recalculado: value={value_int} (taxBase={tax_base_int} + tax={tax_int})")
        
        logger.info(f"Valores PSE: value={value_int} (tipo: {type(value_int)}), tax={tax_int} (tipo: {type(tax_int)}), taxBase={tax_base_int} (tipo: {type(tax_base_int)}), docType={pse_data.doc_type}, bank={pse_data.bank_id}")
        
        # Crear diccionario - ePayco espera números enteros para tax y taxBase, no strings ni floats
        payment_dict = {
            "docType": str(pse_data.doc_type),  # camelCase
            "docNumber": str(pse_data.document),  # camelCase
            "name": str(name),
            "lastName": str(last_name),  # camelCase
            "email": str(pse_data.email),
            "indCountry": "57",  # camelCase - código de país Colombia
            "cellPhone": str(pse_data.phone or user.phone),  # camelCase - requerido
            "phone": str(pse_data.phone or user.phone),  # También enviar phone por si acaso
            "country": "CO",
            "city": str(pse_data.city),
            "address": str(pse_data.address),
            "ip": str(request_ip),
            "currency": "COP",
            "description": str(f"Pago factura {factura.id_factura} - {factura.descripcion or 'Servicios BioGenetic'}"),
            "value": str(value_int),  # String para value
            "tax": tax_int,  # ENTERO (no float, no string) - ePayco espera int
            "taxBase": tax_base_int,  # ENTERO (no float, no string) - ePayco espera int
            "ico": "0",
            "bank": str(pse_data.bank_id),  # ID del banco seleccionado - REQUERIDO
            "urlResponse": str(url_response),  # camelCase
            "urlConfirmation": str(url_confirmation),  # camelCase
            "methodConfirmation": "POST",  # camelCase
            "invoice": str(factura.id_factura),  # Número de factura
            "extra1": str(factura.id_factura),
            "extra2": str(factura.id),
            "extra3": str(user.id),
            "extra4": "",
            "extra5": "",
            "extra6": "",
            "extra7": ""
        }
        
        # Verificación final de tipos
        assert isinstance(payment_dict['tax'], int), f"tax debe ser int, es {type(payment_dict['tax'])}"
        assert isinstance(payment_dict['taxBase'], int), f"taxBase debe ser int, es {type(payment_dict['taxBase'])}"
        assert not isinstance(payment_dict['tax'], float), f"tax NO debe ser float, es {type(payment_dict['tax'])}"
        assert not isinstance(payment_dict['taxBase'], float), f"taxBase NO debe ser float, es {type(payment_dict['taxBase'])}"
        
        return payment_dict
    
    def map_document_type(self, doc_type: DocumentType) -> str:
        """Mapear tipo de documento interno a ePayco"""
        mapping = {
            DocumentType.identity_card: "CC",
            DocumentType.passport: "CE",
            DocumentType.other: "CC"
        }
        return mapping.get(doc_type, "CC")
    
    def save_payment_initial(self, factura: Facturacion, payment_data: Dict[str, Any], user: User) -> Pagos:
        """
        Guardar pago inicial en base de datos ANTES de enviar a ePayco
        Esto asegura que el pago siempre esté guardado, incluso si hay timeout
        """
        # Los campos en payment_data están en camelCase
        doc_type = payment_data.get('docType') or payment_data.get('doc_type')
        document = payment_data.get('docNumber') or payment_data.get('document')
        name = payment_data.get('name')
        last_name = payment_data.get('lastName') or payment_data.get('last_name')
        email = payment_data.get('email')
        phone = payment_data.get('cellPhone') or payment_data.get('phone')
        city = payment_data.get('city')
        address = payment_data.get('address')
        url_response = payment_data.get('urlResponse') or payment_data.get('url_response')
        url_confirmation = payment_data.get('urlConfirmation') or payment_data.get('url_confirmation')
        method_confirmation = payment_data.get('methodConfirmation') or payment_data.get('method_confirmation')
        
        pago = Pagos(
            factura_id=factura.id,
            monto=factura.monto_pagar,
            metodo_pago="PSE",
            estado=EstadoPago.pendiente,
            ref_payco=None,  # Se actualizará cuando llegue la respuesta
            bank_name=None,  # Se actualizará cuando llegue la respuesta
            bank_url=None,  # Se actualizará cuando llegue la respuesta
            doc_type=doc_type,
            document=document,
            name=name,
            last_name=last_name,
            email=email,
            phone=phone,
            city=city,
            address=address,
            ip=payment_data.get('ip'),
            currency=payment_data.get('currency'),
            description=payment_data.get('description'),
            value=factura.monto_pagar,
            tax=factura.valor_iva or Decimal('0'),
            tax_base=factura.monto_base or factura.monto_pagar,
            url_response=url_response,
            url_confirmation=url_confirmation,
            method_confirmation=method_confirmation
        )
        
        self.db.add(pago)
        self.db.commit()
        self.db.refresh(pago)
        
        return pago
    
    def update_payment_with_response(self, pago: Pagos, pse_response: Dict[str, Any], payment_data: Dict[str, Any]) -> Pagos:
        """
        Actualizar pago existente con la respuesta de ePayco
        
        pse_response: datos del objeto 'data' de la respuesta de ePayco
        Ejemplo: { "ref_payco": 317998317, "urlbanco": "https://...", "estado": "Pendiente", ... }
        """
        # Extraer ref_payco (viene como número, convertir a string)
        ref_payco = pse_response.get('ref_payco') or pse_response.get('refPayco')
        if ref_payco:
            pago.ref_payco = str(ref_payco)  # Convertir a string si es número
        
        # Extraer urlbanco (bank_url)
        bank_url = pse_response.get('urlbanco') or pse_response.get('bank_url') or pse_response.get('url')
        if bank_url:
            pago.bank_url = bank_url
        
        # Extraer bank_name si está disponible (PSE por defecto)
        bank_name = pse_response.get('bank_name') or pse_response.get('banco') or pse_response.get('bank')
        if bank_name:
            pago.bank_name = bank_name
        
        # Actualizar estado basado en la respuesta
        # ePayco retorna: "estado": "Pendiente" cuando el pago está esperando confirmación
        estado_respuesta = pse_response.get('estado') or pse_response.get('status')
        if estado_respuesta:
            estado_lower = estado_respuesta.lower()
            if estado_lower in ['pendiente', 'pending']:
                pago.estado = EstadoPago.pendiente
            elif estado_lower in ['procesando', 'processing', 'aceptada', 'aprobada']:
                pago.estado = EstadoPago.procesando
            elif estado_lower in ['completado', 'completada', 'exitosa', 'exitoso']:
                pago.estado = EstadoPago.completado
        
        self.db.commit()
        self.db.refresh(pago)
        
        logger.info(f"Pago actualizado: pago_id={pago.id}, ref_payco={pago.ref_payco}, bank_url={'✅' if pago.bank_url else '❌'}")
        
        return pago
    
    def query_payment_by_invoice(self, invoice_number: str) -> Optional[Dict[str, Any]]:
        """
        Consultar pago en ePayco usando el número de factura (invoice)
        Útil cuando hay timeout y necesitamos obtener el bank_url
        """
        try:
            headers = self._get_auth_headers()
            
            # Intentar diferentes endpoints para consultar por invoice
            # ePayco puede usar diferentes formatos de endpoints
            query_endpoints = [
                # Endpoints con invoice en la URL
                f"{self.apify_base_url}/payment/query/invoice/{invoice_number}",
                f"{self.apify_base_url}/payment/invoice/{invoice_number}",
                f"{self.apify_base_url}/transaction/invoice/{invoice_number}",
                f"{self.apify_base_url}/payment/query?invoice={invoice_number}",
                f"{self.apify_base_url}/payment?invoice={invoice_number}",
                # Endpoints con query parameters
                f"{self.apify_base_url}/payment/query?invoiceNumber={invoice_number}",
                f"{self.apify_base_url}/payment/query?invoice_id={invoice_number}",
                f"{self.apify_base_url}/payment/query?idfactura={invoice_number}",
                # Endpoints POST para consultar
                f"{self.apify_base_url}/payment/query",
            ]
            
            for endpoint in query_endpoints:
                try:
                    logger.info(f"Consultando pago por invoice desde: {endpoint}")
                    
                    # Si es el último endpoint (POST), enviar invoice en el body
                    if endpoint.endswith('/payment/query'):
                        response = requests.post(
                            endpoint,
                            json={"invoice": invoice_number, "invoiceNumber": invoice_number, "idfactura": invoice_number},
                            headers=headers,
                            timeout=10
                        )
                    else:
                        response = requests.get(endpoint, headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        logger.info(f"✅ Respuesta recibida: {data}")
                        
                        # Extraer datos de diferentes estructuras posibles
                        if isinstance(data, dict):
                            # Si tiene 'data', usar eso
                            if 'data' in data:
                                payment_data = data['data']
                                # Si data es una lista, tomar el primero
                                if isinstance(payment_data, list) and len(payment_data) > 0:
                                    payment_data = payment_data[0]
                                logger.info(f"✅ Pago encontrado por invoice: {payment_data}")
                                return payment_data
                            # Si no tiene 'data', usar el objeto completo
                            elif 'ref_payco' in data or 'refPayco' in data or 'urlbanco' in data:
                                logger.info(f"✅ Pago encontrado por invoice: {data}")
                                return data
                    
                    elif response.status_code == 404:
                        logger.debug(f"Endpoint {endpoint} no existe (404), probando siguiente...")
                        continue
                    else:
                        logger.debug(f"Endpoint {endpoint} retornó status {response.status_code}: {response.text[:200]}")
                        continue
                except Exception as e:
                    logger.debug(f"Error al intentar endpoint {endpoint}: {str(e)}")
                    continue
            
            logger.warning(f"No se pudo consultar pago por invoice {invoice_number} desde ningún endpoint")
            return None
            
        except Exception as e:
            logger.error(f"Error al consultar pago por invoice: {str(e)}")
            return None
    
    async def refresh_payment_from_epayco(self, pago: Pagos) -> Optional[Pagos]:
        """
        Actualizar pago consultando ePayco si no tiene bank_url
        Útil después de un timeout
        """
        try:
            # Si ya tiene bank_url, no es necesario consultar
            if pago.bank_url:
                return pago
            
            # Obtener factura para tener el invoice number
            factura = self.get_factura(pago.factura_id)
            if not factura:
                logger.warning(f"No se encontró factura para pago {pago.id}")
                return pago
            
            # Intentar consultar por invoice
            payment_data = self.query_payment_by_invoice(factura.id_factura)
            
            if payment_data:
                # Actualizar pago con los datos obtenidos
                ref_payco = payment_data.get('ref_payco') or payment_data.get('refPayco')
                bank_url = payment_data.get('urlbanco') or payment_data.get('bank_url') or payment_data.get('url')
                bank_name = payment_data.get('bank_name') or payment_data.get('banco') or payment_data.get('bank')
                
                if ref_payco:
                    pago.ref_payco = ref_payco
                if bank_url:
                    pago.bank_url = bank_url
                if bank_name:
                    pago.bank_name = bank_name
                
                self.db.commit()
                self.db.refresh(pago)
                
                logger.info(f"✅ Pago {pago.id} actualizado desde ePayco: bank_url={bank_url}")
                return pago
            
            return pago
            
        except Exception as e:
            logger.error(f"Error al refrescar pago desde ePayco: {str(e)}")
            return pago
    
    def save_payment(self, factura: Facturacion, pse_response: Dict[str, Any], payment_data: Dict[str, Any], user: User) -> Pagos:
        """Guardar pago en base de datos"""
        # Extraer ref_payco (puede estar como ref_payco o refPayco)
        ref_payco = pse_response.get('ref_payco') or pse_response.get('refPayco')
        
        # Extraer bank_url (puede estar como urlbanco, bank_url, o url)
        bank_url = pse_response.get('urlbanco') or pse_response.get('bank_url') or pse_response.get('url')
        
        # Extraer bank_name si está disponible
        bank_name = pse_response.get('bank_name') or pse_response.get('banco') or pse_response.get('bank')
        
        # Los campos en payment_data ahora están en camelCase, pero también pueden estar en snake_case
        doc_type = payment_data.get('docType') or payment_data.get('doc_type')
        document = payment_data.get('docNumber') or payment_data.get('document')
        name = payment_data.get('name')
        last_name = payment_data.get('lastName') or payment_data.get('last_name')
        email = payment_data.get('email')
        phone = payment_data.get('cellPhone') or payment_data.get('phone')
        city = payment_data.get('city')
        address = payment_data.get('address')
        url_response = payment_data.get('urlResponse') or payment_data.get('url_response')
        url_confirmation = payment_data.get('urlConfirmation') or payment_data.get('url_confirmation')
        method_confirmation = payment_data.get('methodConfirmation') or payment_data.get('method_confirmation')
        
        pago = Pagos(
            factura_id=factura.id,
            monto=factura.monto_pagar,
            metodo_pago="PSE",
            estado=EstadoPago.pendiente,
            ref_payco=ref_payco,
            bank_name=bank_name,
            bank_url=bank_url,
            doc_type=doc_type,
            document=document,
            name=name,
            last_name=last_name,
            email=email,
            phone=phone,
            city=city,
            address=address,
            ip=payment_data.get('ip'),
            currency=payment_data.get('currency'),
            description=payment_data.get('description'),
            value=factura.monto_pagar,
            tax=factura.valor_iva or Decimal('0'),
            tax_base=factura.monto_base or factura.monto_pagar,
            url_response=url_response,
            url_confirmation=url_confirmation,
            method_confirmation=method_confirmation
        )
        
        self.db.add(pago)
        self.db.commit()
        self.db.refresh(pago)
        
        return pago

class DaviPlataPaymentService:
    """Servicio para procesamiento de pagos DaviPlata usando la API de ePayco directamente"""
    
    def __init__(self, db: Session):
        self.db = db
        self.api_key = getattr(settings, 'EPAYCO_PUBLIC_KEY', '')
        self.private_key = getattr(settings, 'EPAYCO_PRIVATE_KEY', '')
        self.apify_base_url = getattr(settings, 'EPAYCO_APIFY_BASE_URL', '').rstrip('/')
        self._token = None
        self._token_expires_at = None
    
    def _get_auth_token(self) -> str:
        """Obtener token JWT de ePayco usando Basic Auth"""
        from datetime import timedelta
        
        # Verificar si el token existe y no ha expirado
        if self._token and self._token_expires_at and datetime.now() < self._token_expires_at:
            return self._token
        
        try:
            logger.info("Obteniendo nuevo token JWT de ePayco...")
            
            # Intentar diferentes endpoints comunes de autenticación
            auth_endpoints = [
                "/auth/token",
                "/token",
                "/auth/login",
                "/login"
            ]
            
            token_data = None
            last_error = None
            
            for endpoint in auth_endpoints:
                try:
                    auth_url = f"{self.apify_base_url}{endpoint}"
                    logger.debug(f"Intentando autenticación en: {auth_url}")
                    
                    response = requests.post(
                        auth_url,
                        auth=HTTPBasicAuth(self.api_key, self.private_key),
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        token_data = response.json()
                        logger.info(f"✅ Token JWT obtenido exitosamente desde: {endpoint}")
                        break
                    elif response.status_code == 404:
                        logger.debug(f"Endpoint {endpoint} no existe (404), probando siguiente...")
                        continue
                    else:
                        logger.warning(f"Respuesta inesperada desde {endpoint}: {response.status_code}")
                        last_error = f"Status {response.status_code}: {response.text[:200]}"
                        continue
                except requests.exceptions.RequestException as e:
                    logger.warning(f"Error de conexión con {endpoint}: {str(e)}")
                    last_error = str(e)
                    continue
            
            if token_data:
                self._token = token_data.get('token', '') or token_data.get('access_token', '') or token_data.get('jwt', '')
                if not self._token:
                    # Si no hay token en la respuesta, podría ser que el token esté en otro formato
                    logger.warning(f"Token no encontrado en respuesta. Respuesta completa: {token_data}")
                    raise ValueError("No se encontró token en la respuesta de ePayco")
                
                # Token expira en 1 hora, pero renovamos 5 minutos antes
                self._token_expires_at = datetime.now() + timedelta(minutes=55)
                logger.info("✅ Token JWT obtenido y almacenado exitosamente")
                return self._token
            else:
                error_msg = last_error or "No se pudo obtener token de ningún endpoint"
                logger.error(f"Error al obtener token: {error_msg}")
                raise ValueError(f"Error al obtener token de ePayco: {error_msg}")
        except Exception as e:
            logger.error(f"Error al obtener token JWT: {str(e)}")
            raise ValueError(f"Error al obtener token de ePayco: {str(e)}")
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """
        Obtener headers con autenticación JWT o Basic Auth como fallback
        
        Si no se puede obtener token JWT, usa Basic Auth directamente
        """
        try:
            token = self._get_auth_token()
            return {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        except Exception as e:
            logger.warning(f"No se pudo obtener token JWT, usando Basic Auth directamente: {str(e)}")
            # Fallback: usar Basic Auth directamente
            import base64
            credentials = f"{self.api_key}:{self.private_key}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            return {
                "Authorization": f"Basic {encoded_credentials}",
                "Content-Type": "application/json"
            }
    
    async def create_daviplata_payment(self, factura_id: int, user: User, request_ip: str, daviplata_data: PagoDaviplataCreate) -> Dict[str, Any]:
        """
        Crear pago DaviPlata para una factura específica usando la API de ePayco
        """
        try:
            # 1. Obtener factura
            factura = self.db.query(Facturacion).filter(Facturacion.id == factura_id).first()
            if not factura:
                raise ValueError(f"Factura con ID {factura_id} no encontrada")
            
            # 2. Verificar que la factura no esté pagada
            if factura.estado == EstadoFactura.pagado:
                raise ValueError("La factura ya está pagada")
            
            # 2.1. Verificar si ya existe un pago DaviPlata pendiente o en proceso
            pago_existente = self.db.query(Pagos).filter(
                Pagos.factura_id == factura_id,
                Pagos.metodo_pago == "DaviPlata",
                Pagos.estado.in_([EstadoPago.pendiente, EstadoPago.procesando])
            ).first()
            
            if pago_existente:
                logger.warning(f"Ya existe un pago DaviPlata pendiente/procesando para la factura {factura_id}: pago_id={pago_existente.id}")
                return {
                    "pago_id": pago_existente.id,
                    "ref_payco": pago_existente.ref_payco or '',
                    "bank_url": pago_existente.bank_url or '',
                    "bank_name": "DaviPlata",
                    "status": pago_existente.estado.value,
                    "message": "Ya existe un pago DaviPlata pendiente para esta factura.",
                    "existing": True
                }
            
            # 3. Preparar datos para la API de ePayco
            payment_data = self.prepare_daviplata_data(factura, user, request_ip, daviplata_data)
            
            # 4. Crear pago en ePayco usando la API
            api_url = f"{self.apify_base_url}/payment/process/daviplata"
            headers = self._get_auth_headers()
            
            # Filtrar campos internos que no se envían a la API
            api_payment_data = {k: v for k, v in payment_data.items() if not k.startswith('_')}
            
            logger.info(f"Enviando pago DaviPlata a ePayco API: {api_url}")
            logger.debug(f"Datos del pago: {api_payment_data}")
            
            response = requests.post(
                api_url,
                json=api_payment_data,
                headers=headers,
                timeout=30
            )
            
            if response.status_code not in [200, 201]:
                error_text = response.text
                logger.error(f"Error al crear pago en ePayco: {response.status_code} - {error_text}")
                raise ValueError(f"Error al crear pago en ePayco: {response.status_code} - {error_text}")
            
            daviplata_response = response.json()
            logger.info(f"Respuesta de ePayco API: {daviplata_response}")
            
            # Verificar si la respuesta indica error
            if isinstance(daviplata_response, dict) and daviplata_response.get('success') is False:
                error_message = daviplata_response.get('textResponse') or daviplata_response.get('message') or 'Error desconocido'
                errors = daviplata_response.get('data', {}).get('errors', [])
                error_details = []
                error_codes = []
                
                if errors:
                    for err in errors:
                        error_code = err.get('codError', '')
                        error_msg = err.get('errorMessage', '')
                        error_codes.append(error_code)
                        error_details.append(error_msg)
                
                # Manejo específico para errores conocidos
                if 'E035' in error_codes:
                    logger.warning(f"Error E035: Factura duplicada. Buscando pago existente para factura {factura_id}")
                    pago_existente = self.db.query(Pagos).filter(
                        Pagos.factura_id == factura_id,
                        Pagos.metodo_pago == "DaviPlata"
                    ).order_by(Pagos.id.desc()).first()
                    
                    if pago_existente:
                        logger.info(f"Pago existente encontrado: pago_id={pago_existente.id}")
                        return {
                            "pago_id": pago_existente.id,
                            "ref_payco": pago_existente.ref_payco or '',
                            "bank_url": pago_existente.bank_url or '',
                            "bank_name": "DaviPlata",
                            "status": pago_existente.estado.value,
                            "message": "Ya existe un pago DaviPlata pendiente para esta factura.",
                            "existing": True
                        }
                
                full_error = error_message
                if error_details:
                    full_error += f" - Detalles: {', '.join(error_details)}"
                
                logger.error(f"ePayco rechazó la solicitud: {full_error}")
                raise ValueError(f"Error al crear pago en ePayco: {full_error}")
            
            # Extraer datos de la respuesta exitosa
            response_data = daviplata_response.get('data', {}) if isinstance(daviplata_response, dict) else {}
            
            # CRITICAL: Buscar refPayco en camelCase (DaviPlata devuelve refPayco, no ref_payco)
            ref_payco = (
                response_data.get('refPayco') or  # camelCase (DaviPlata)
                response_data.get('ref_payco') or 
                daviplata_response.get('refPayco') or
                daviplata_response.get('ref_payco') or 
                response_data.get('reference') or 
                ''
            )
            
            # Buscar URL de redirección
            bank_url = (
                response_data.get('urlbanco') or
                response_data.get('url') or
                daviplata_response.get('url') or
                ''
            )
            
            if not ref_payco:
                logger.error(f"La respuesta de ePayco no contiene ref_payco. Respuesta: {daviplata_response}")
                raise ValueError("Error al crear pago en ePayco: respuesta inválida - no se encontró ref_payco")
            
            ref_payco = str(ref_payco) if ref_payco else ''
            
            logger.info(f"✅ Pago DaviPlata creado exitosamente: ref_payco={ref_payco}")
            
            # 5. Guardar pago en base de datos
            daviplata_response_combined = {
                **daviplata_response,
                'ref_payco': ref_payco,
                'bank_url': bank_url,
                'bank_name': 'DaviPlata',
                'data': response_data
            }
            
            pago = self.save_payment(factura, daviplata_response_combined, payment_data, user)
            
            logger.info(f"Pago guardado en BD: pago_id={pago.id}, ref_payco={ref_payco}")
            
            return {
                "pago_id": pago.id,
                "ref_payco": ref_payco,
                "bank_url": bank_url,
                "bank_name": "DaviPlata",
                "status": pago.estado.value,
                "message": "Pago DaviPlata creado exitosamente. Revisa tu aplicación DaviPlata para completar el pago."
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error de conexión al crear pago DaviPlata: {str(e)}")
            raise ValueError(f"Error de conexión con ePayco: {str(e)}")
        except Exception as e:
            logger.error(f"Error al crear pago DaviPlata: {str(e)}")
            logger.exception(e)
            raise ValueError(f"Error al procesar pago DaviPlata: {str(e)}")
    
    def get_factura(self, factura_id: int) -> Optional[Facturacion]:
        """Obtener factura por ID"""
        return self.db.query(Facturacion).filter(Facturacion.id == factura_id).first()
    
    def prepare_daviplata_data(self, factura: Facturacion, user: User, request_ip: str, daviplata_data: PagoDaviplataCreate) -> Dict[str, Any]:
        """
        Preparar datos para envío a la API de ePayco DaviPlata
        
        Según el curl proporcionado, los campos requeridos son:
        - docType, document, name, lastName, email, indCountry, phone, country, city, address
        - ip, currency, description, value, tax, taxBase, methodConfirmation
        """
        # Obtener valores de la factura
        monto_base = factura.monto_base or factura.monto_pagar
        valor_iva = factura.valor_iva or Decimal('0')
        monto_total = factura.monto_pagar
        
        # Dividir el nombre completo
        full_name_parts = daviplata_data.full_name.strip().split()
        name = full_name_parts[0] if full_name_parts else "Cliente"
        last_name = " ".join(full_name_parts[1:]) if len(full_name_parts) > 1 else ""
        
        # Mapear el tipo de documento
        doc_type = self.map_document_type_from_string(daviplata_data.doc_type)
        
        # Validar monto mínimo de ePayco
        MONTO_MINIMO_EPAYCO = 10000.0
        monto_total_float = float(monto_total)
        if monto_total_float < MONTO_MINIMO_EPAYCO:
            raise ValueError(f"El monto mínimo para transacciones DaviPlata es ${MONTO_MINIMO_EPAYCO:,.0f} COP. Monto actual: ${monto_total_float:,.0f} COP")
        
        # Convertir valores a strings - DaviPlata requiere strings para value, tax, taxBase
        def to_string_int(value):
            """Convertir cualquier valor numérico a string entero"""
            if value is None:
                return "0"
            if isinstance(value, Decimal):
                return str(int(value))
            if isinstance(value, (int, float)):
                return str(int(value))
            if isinstance(value, str):
                try:
                    return str(int(float(value)))
                except (ValueError, TypeError):
                    return "0"
            return "0"
        
        value_str = to_string_int(monto_total)
        tax_str = to_string_int(valor_iva)
        tax_base_str = to_string_int(monto_base)
        
        logger.info(f"Valores DaviPlata: value={value_str}, tax={tax_str}, taxBase={tax_base_str}, docType={doc_type}")
        
        # Construir el body según la estructura de ePayco para DaviPlata
        payment_data = {
            "docType": doc_type,  # CC, CE, etc. (no forzado a NIT como PSE)
            "document": daviplata_data.document,
            "name": name,
            "lastName": last_name,
            "email": daviplata_data.email,
            "indCountry": "CO",  # Código de país para Colombia
            "phone": daviplata_data.phone,
            "country": "CO",  # País
            "city": daviplata_data.city.lower(),  # Ciudad en minúsculas
            "address": daviplata_data.address,
            "ip": request_ip,
            "currency": "COP",
            "description": f"Pago factura {factura.id_factura} - {factura.descripcion or 'Servicios BioGenetic'}",
            "value": value_str,  # String
            "tax": tax_str,  # String
            "taxBase": tax_base_str,  # String
            "methodConfirmation": "",  # Vacío según el ejemplo del curl
            # Campos adicionales para guardar en BD
            "_factura_id": factura.id,
            "_user_id": user.id,
            "_tax": valor_iva,
            "_taxBase": monto_base
        }
        
        logger.debug(f"Datos preparados para DaviPlata: value={value_str}, tax={tax_str}, taxBase={tax_base_str}, docType={doc_type}")
        
        return payment_data
    
    def map_document_type_from_string(self, doc_type: str) -> str:
        """Mapear tipo de documento desde string"""
        if not doc_type:
            return "CC"
        
        doc_type_upper = doc_type.upper().strip()
        
        if doc_type_upper in ["CC", "CEDULA", "CÉDULA", "CEDULA DE CIUDADANIA", "CÉDULA DE CIUDADANÍA", "IDENTITY_CARD"]:
            return "CC"
        elif doc_type_upper in ["CE", "CEDULA DE EXTRANJERIA", "CÉDULA DE EXTRANJERÍA", "PASAPORTE", "PASSPORT"]:
            return "CE"
        elif doc_type_upper in ["NIT", "NÚMERO DE IDENTIFICACIÓN TRIBUTARIA"]:
            return "NIT"
        elif doc_type_upper in ["PP", "PASAPORTE", "PASSPORT"]:
            return "PP"
        elif doc_type_upper in ["TI", "TARJETA DE IDENTIDAD"]:
            return "TI"
        else:
            return "CC"
    
    def save_payment(self, factura: Facturacion, daviplata_response: Dict[str, Any], payment_data: Dict[str, Any], user: User) -> Pagos:
        """Guardar pago DaviPlata en base de datos"""
        response_data = daviplata_response.get('data', {}) if isinstance(daviplata_response, dict) else {}
        
        # CRITICAL: Buscar refPayco en camelCase (DaviPlata devuelve refPayco, no ref_payco)
        ref_payco = (
            response_data.get('refPayco') or  # camelCase (DaviPlata)
            daviplata_response.get('refPayco') or
            daviplata_response.get('ref_payco') or 
            response_data.get('ref_payco') or 
            response_data.get('reference') or 
            ''
        )
        bank_url = (
            response_data.get('urlbanco') or
            response_data.get('url') or
            daviplata_response.get('url') or
            ''
        )
        
        ref_payco = str(ref_payco) if ref_payco else ''
        
        pago = Pagos(
            factura_id=factura.id,
            monto=factura.monto_pagar,
            metodo_pago="DaviPlata",
            estado=EstadoPago.pendiente,
            ref_payco=ref_payco,
            bank_name="DaviPlata",
            bank_url=bank_url,
            doc_type=payment_data.get('docType', 'CC'),
            document=payment_data.get('document'),
            name=payment_data.get('name'),
            last_name=payment_data.get('lastName'),
            email=payment_data.get('email'),
            phone=payment_data.get('phone'),
            city=payment_data.get('city', ''),
            address=payment_data.get('address'),
            ip=payment_data.get('ip'),
            currency=payment_data.get('currency'),
            description=payment_data.get('description'),
            value=factura.monto_pagar,
            tax=payment_data.get('_tax') or Decimal('0'),
            tax_base=payment_data.get('_taxBase') or factura.monto_pagar,
            url_response="",  # DaviPlata no usa urlResponse
            url_confirmation="",  # DaviPlata usa methodConfirmation vacío
            method_confirmation=payment_data.get('methodConfirmation') or ''
        )
        
        self.db.add(pago)
        self.db.commit()
        self.db.refresh(pago)
        
        return pago
    
    async def confirm_daviplata_otp(self, ref_payco: str, otp: str) -> Dict[str, Any]:
        """
        Confirmar OTP de pago DaviPlata
        
        Args:
            ref_payco: Referencia del pago en ePayco
            otp: Código OTP recibido en la aplicación DaviPlata
        
        Returns:
            Dict con el resultado de la confirmación
        """
        try:
            # 1. Verificar que el pago exista en la base de datos
            pago = self.db.query(Pagos).filter(Pagos.ref_payco == ref_payco).first()
            if not pago:
                raise ValueError(f"Pago con ref_payco {ref_payco} no encontrado")
            
            # 2. Verificar que sea un pago DaviPlata
            if pago.metodo_pago != "DaviPlata":
                raise ValueError(f"El pago {ref_payco} no es un pago DaviPlata")
            
            # 3. Verificar que el pago esté pendiente
            if pago.estado != EstadoPago.pendiente:
                raise ValueError(f"El pago {ref_payco} no está pendiente. Estado actual: {pago.estado.value}")
            
            # 4. Preparar datos para confirmar OTP en ePayco
            api_url = f"{self.apify_base_url}/payment/confirm/daviplata"
            headers = self._get_auth_headers()
            
            # Según el curl, se envía el ref_payco y el OTP
            confirm_data = {
                "ref_payco": ref_payco,
                "otp": otp
            }
            
            logger.info(f"Confirmando OTP DaviPlata para ref_payco: {ref_payco}")
            logger.debug(f"Datos de confirmación: ref_payco={ref_payco}, otp={'*' * len(otp)}")
            
            response = requests.post(
                api_url,
                json=confirm_data,
                headers=headers,
                timeout=30
            )
            
            if response.status_code not in [200, 201]:
                error_text = response.text
                logger.error(f"Error al confirmar OTP en ePayco: {response.status_code} - {error_text}")
                raise ValueError(f"Error al confirmar OTP en ePayco: {response.status_code} - {error_text}")
            
            confirm_response = response.json()
            logger.info(f"Respuesta de confirmación OTP: {confirm_response}")
            
            # 5. Procesar respuesta
            response_data = confirm_response.get('data', {}) if isinstance(confirm_response, dict) else {}
            transaccion = response_data.get('transaccion', {})
            
            # Verificar si la confirmación fue exitosa
            success = confirm_response.get('success', False)
            estado_transaccion = transaccion.get('estado', '')
            cod_respuesta = transaccion.get('cod_respuesta', '')
            
            # 6. Actualizar estado del pago en base de datos
            if success and estado_transaccion == 'Aceptada':
                pago.estado = EstadoPago.completado
                pago.response_code = cod_respuesta
                pago.response_message = transaccion.get('respuesta', 'Pago completado')
                
                # Actualizar estado de la factura
                factura = self.db.query(Facturacion).filter(Facturacion.id == pago.factura_id).first()
                if factura:
                    factura.estado = EstadoFactura.pagado
                    factura.fecha_pago = datetime.now()
            elif estado_transaccion == 'Rechazada' or not success:
                pago.estado = EstadoPago.fallido
                pago.response_code = cod_respuesta
                pago.response_message = transaccion.get('respuesta') or confirm_response.get('text_response', 'Pago rechazado')
            else:
                pago.estado = EstadoPago.procesando
                pago.response_code = cod_respuesta
                pago.response_message = transaccion.get('respuesta', 'Procesando')
            
            self.db.commit()
            self.db.refresh(pago)
            
            logger.info(f"Pago actualizado: ref_payco={ref_payco}, estado={pago.estado.value}")
            
            return {
                "success": success,
                "ref_payco": ref_payco,
                "pago_id": pago.id,
                "estado": pago.estado.value,
                "response_code": cod_respuesta,
                "response_message": pago.response_message,
                "data": {
                    "estado_transaccion": estado_transaccion,
                    "autorizacion": transaccion.get('autorizacion', ''),
                    "recibo": transaccion.get('recibo', ''),
                    "valor_total": transaccion.get('valortotal', ''),
                    "fecha_pago": transaccion.get('fechapago')
                }
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error de conexión al confirmar OTP DaviPlata: {str(e)}")
            raise ValueError(f"Error de conexión con ePayco: {str(e)}")
        except Exception as e:
            logger.error(f"Error al confirmar OTP DaviPlata: {str(e)}")
            logger.exception(e)
            raise ValueError(f"Error al procesar confirmación OTP: {str(e)}")

class PaymentConfirmationService:
    """Servicio para confirmación de pagos usando la API Apify de ePayco directamente"""
    
    def __init__(self, db: Session):
        self.db = db
        self.api_key = getattr(settings, 'EPAYCO_PUBLIC_KEY', '')
        self.private_key = getattr(settings, 'EPAYCO_PRIVATE_KEY', '')
        self.apify_base_url = getattr(settings, 'EPAYCO_APIFY_BASE_URL', '').rstrip('/')
        self._token = None
        self._token_expires_at = None
    
    def _get_auth_token(self) -> str:
        """Obtener token JWT de ePayco usando Basic Auth"""
        from datetime import timedelta
        
        # Verificar si el token existe y no ha expirado
        if self._token and self._token_expires_at and datetime.now() < self._token_expires_at:
            return self._token
        
        try:
            logger.info("Obteniendo nuevo token JWT de ePayco...")
            
            # Intentar diferentes endpoints comunes de autenticación
            auth_endpoints = [
                "/auth/token",
                "/token",
                "/auth/login",
                "/login"
            ]
            
            token_data = None
            last_error = None
            
            for endpoint in auth_endpoints:
                try:
                    auth_url = f"{self.apify_base_url}{endpoint}"
                    logger.debug(f"Intentando autenticación en: {auth_url}")
                    
                    response = requests.post(
                        auth_url,
                        auth=HTTPBasicAuth(self.api_key, self.private_key),
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        token_data = response.json()
                        logger.info(f"✅ Token JWT obtenido exitosamente desde: {endpoint}")
                        break
                    elif response.status_code == 404:
                        logger.debug(f"Endpoint {endpoint} no existe (404), probando siguiente...")
                        continue
                    else:
                        logger.warning(f"Respuesta inesperada desde {endpoint}: {response.status_code}")
                        last_error = f"Status {response.status_code}: {response.text[:200]}"
                        continue
                except requests.exceptions.RequestException as e:
                    logger.warning(f"Error de conexión con {endpoint}: {str(e)}")
                    last_error = str(e)
                    continue
            
            if token_data:
                self._token = token_data.get('token', '') or token_data.get('access_token', '') or token_data.get('jwt', '')
                if not self._token:
                    logger.warning(f"Token no encontrado en respuesta. Respuesta completa: {token_data}")
                    raise ValueError("No se encontró token en la respuesta de ePayco")
                
                # Token expira en 1 hora, pero renovamos 5 minutos antes
                self._token_expires_at = datetime.now() + timedelta(minutes=55)
                logger.info("✅ Token JWT obtenido y almacenado exitosamente")
                return self._token
            else:
                error_msg = last_error or "No se pudo obtener token de ningún endpoint"
                logger.error(f"Error al obtener token: {error_msg}")
                raise ValueError(f"Error al obtener token de ePayco: {error_msg}")
        except Exception as e:
            logger.error(f"Error al obtener token JWT: {str(e)}")
            raise ValueError(f"Error al obtener token de ePayco: {str(e)}")
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """
        Obtener headers con autenticación JWT o Basic Auth como fallback
        """
        try:
            token = self._get_auth_token()
            return {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        except Exception as e:
            logger.warning(f"No se pudo obtener token JWT, usando Basic Auth directamente: {str(e)}")
            # Fallback: usar Basic Auth directamente
            import base64
            credentials = f"{self.api_key}:{self.private_key}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            return {
                "Authorization": f"Basic {encoded_credentials}",
                "Content-Type": "application/json"
            }
    
    async def confirm_payment(self, ref_payco: str) -> Dict[str, Any]:
        """
        Confirmar estado de pago con ePayco usando la API Apify
        """
        try:
            # 1. Consultar estado en ePayco usando la API Apify
            # Intentar diferentes endpoints posibles para consultar el estado
            query_endpoints = [
                f"{self.apify_base_url}/payment/query/{ref_payco}",
                f"{self.apify_base_url}/payment/{ref_payco}",
                f"{self.apify_base_url}/payment/status/{ref_payco}",
                f"{self.apify_base_url}/transaction/{ref_payco}",
                f"{self.apify_base_url}/payment/query?ref_payco={ref_payco}",
                f"{self.apify_base_url}/payment/query?refPayco={ref_payco}",
            ]
            
            headers = self._get_auth_headers()
            payment_status = None
            
            for endpoint in query_endpoints:
                try:
                    logger.info(f"Consultando estado del pago desde: {endpoint}")
                    response = requests.get(endpoint, headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        logger.info(f"✅ Respuesta recibida de ePayco: {data}")
                        
                        # Extraer datos de la respuesta
                        if isinstance(data, dict):
                            # Si tiene 'data', usar eso
                            if 'data' in data:
                                payment_status = data['data']
                                # Si data es una lista, tomar el primero
                                if isinstance(payment_status, list) and len(payment_status) > 0:
                                    payment_status = payment_status[0]
                            # Si no tiene 'data', usar el objeto completo
                            elif 'ref_payco' in data or 'refPayco' in data or 'urlbanco' in data or 'bank_url' in data:
                                payment_status = data
                            else:
                                payment_status = data
                        else:
                            payment_status = data
                        
                        logger.info(f"✅ Estado del pago extraído: {payment_status}")
                        break
                    elif response.status_code == 404:
                        logger.debug(f"Endpoint {endpoint} no existe (404), probando siguiente...")
                        continue
                    else:
                        logger.debug(f"Endpoint {endpoint} retornó status {response.status_code}: {response.text[:200]}")
                        continue
                except Exception as e:
                    logger.debug(f"Error al intentar endpoint {endpoint}: {str(e)}")
                    continue
            
            # Si no se pudo obtener el estado desde la API, usar los datos del pago en BD
            if not payment_status:
                logger.warning(f"No se pudo obtener estado desde API, usando datos de BD para ref_payco: {ref_payco}")
                pago = self.db.query(Pagos).filter(Pagos.ref_payco == ref_payco).first()
                if not pago:
                    raise ValueError(f"Pago con ref_payco {ref_payco} no encontrado")
                
                # Construir payment_status desde los datos del pago
                payment_status = {
                    'x_response': 'Pendiente' if pago.estado == EstadoPago.pendiente else 
                                  'Aceptada' if pago.estado == EstadoPago.completado else
                                  'Rechazada' if pago.estado == EstadoPago.fallido else 'Pendiente',
                    'x_response_reason_text': pago.response_message or 'Pago en proceso',
                    'transaction_id': pago.transaction_id,
                    'ref_payco': pago.ref_payco,
                    'urlbanco': pago.bank_url,
                    'bank_url': pago.bank_url,
                    'bank_name': pago.bank_name
                }
            
            # 2. Actualizar pago en base de datos
            pago = self.update_payment_status(ref_payco, payment_status)
            
            # 3. Extraer y actualizar bank_url si viene en payment_status
            bank_url = payment_status.get('urlbanco') or payment_status.get('bank_url') or payment_status.get('url')
            bank_name = payment_status.get('bank_name') or payment_status.get('banco') or payment_status.get('bank')
            
            if bank_url and not pago.bank_url:
                pago.bank_url = bank_url
                logger.info(f"✅ bank_url actualizado desde consulta: {bank_url}")
            if bank_name and not pago.bank_name:
                pago.bank_name = bank_name
            
            self.db.commit()
            self.db.refresh(pago)
            
            # 4. Actualizar estado de factura si es necesario
            factura_actualizada = False
            x_response = payment_status.get('x_response') or payment_status.get('estado') or payment_status.get('status')
            if x_response in ['Aceptada', 'Aceptada', 'Aprobada', 'Aprobada']:
                factura_actualizada = self.update_factura_status(pago.factura_id, EstadoFactura.pagado)
            
            logger.info(f"Pago confirmado: {ref_payco}, estado: {x_response}, bank_url: {pago.bank_url}")
            
            return {
                "pago_id": pago.id,
                "estado": pago.estado.value,
                "ref_payco": ref_payco,
                "response_code": x_response,
                "response_message": payment_status.get('x_response_reason_text') or payment_status.get('message') or 'Pago procesado',
                "factura_actualizada": factura_actualizada,
                "bank_url": pago.bank_url,
                "bank_name": pago.bank_name
            }
            
        except Exception as e:
            logger.error(f"Error al confirmar pago {ref_payco}: {str(e)}")
            raise ValueError(f"Error al confirmar pago: {str(e)}")
    
    def update_payment_status(self, ref_payco: str, payment_status: Dict[str, Any]) -> Pagos:
        """Actualizar estado del pago basado en respuesta de ePayco"""
        pago = self.db.query(Pagos).filter(Pagos.ref_payco == ref_payco).first()
        
        if not pago:
            raise ValueError(f"Pago con ref_payco {ref_payco} no encontrado")
        
        # Mapear estado de ePayco a estado interno
        epayco_status = payment_status.get('x_response') or payment_status.get('estado') or payment_status.get('status')
        estado_mapping = {
            'Aceptada': EstadoPago.completado,
            'Aprobada': EstadoPago.completado,
            'Pendiente': EstadoPago.procesando,
            'Rechazada': EstadoPago.fallido,
            'Fallida': EstadoPago.fallido
        }
        
        pago.estado = estado_mapping.get(epayco_status, EstadoPago.pendiente)
        pago.response_code = payment_status.get('x_response') or payment_status.get('estado') or payment_status.get('status')
        pago.response_message = payment_status.get('x_response_reason_text') or payment_status.get('message')
        pago.transaction_id = payment_status.get('transaction_id') or payment_status.get('transactionID')
        
        # Actualizar bank_url y bank_name si vienen en payment_status
        bank_url = payment_status.get('urlbanco') or payment_status.get('bank_url') or payment_status.get('url')
        bank_name = payment_status.get('bank_name') or payment_status.get('banco') or payment_status.get('bank')
        
        if bank_url:
            pago.bank_url = bank_url
        if bank_name:
            pago.bank_name = bank_name
        
        self.db.commit()
        self.db.refresh(pago)
        
        return pago
    
    def update_factura_status(self, factura_id: int, nuevo_estado: EstadoFactura) -> bool:
        """Actualizar estado de la factura"""
        try:
            factura = self.db.query(Facturacion).filter(Facturacion.id == factura_id).first()
            if factura:
                factura.estado = nuevo_estado
                if nuevo_estado == EstadoFactura.pagado:
                    factura.fecha_pago = datetime.now()
                self.db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error al actualizar factura {factura_id}: {str(e)}")
            return False
    
    def get_transaction_detail(self, reference_payco: str) -> Optional[Dict[str, Any]]:
        """
        Consultar detalles de una transacción usando referencePayco
        
        Args:
            reference_payco: Referencia de ePayco (ref_payco) de la transacción
            
        Returns:
            Dict con los detalles de la transacción o None si no se encuentra
            
        Example:
            transaction_detail = service.get_transaction_detail("30604419")
        """
        try:
            if not self.apify_base_url:
                logger.error("EPAYCO_APIFY_BASE_URL no configurada")
                return None
            
            # Endpoint para consultar detalles de transacción
            url = f"{self.apify_base_url}/transaction/detail"
            
            # Preparar headers con autenticación
            headers = self._get_auth_headers()
            
            # Preparar body con el filtro
            # Nota: Aunque es un GET, ePayco requiere el body JSON según el curl proporcionado
            payload = {
                "filter": {
                    "referencePayco": reference_payco
                }
            }
            
            logger.info(f"Consultando detalles de transacción: referencePayco={reference_payco}")
            logger.debug(f"URL: {url}")
            logger.debug(f"Payload: {payload}")
            
            # Realizar la petición GET con body JSON
            # Nota: requests.get no soporta body directamente, pero podemos usar requests.request
            response = requests.request(
                method="GET",
                url=url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            logger.info(f"Respuesta de ePayco - Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Detalles de transacción obtenidos exitosamente para referencePayco={reference_payco}")
                logger.debug(f"Datos recibidos: {data}")
                return data
            elif response.status_code == 404:
                logger.warning(f"⚠️ Transacción no encontrada: referencePayco={reference_payco}")
                return None
            elif response.status_code == 401:
                logger.error(f"❌ Error de autenticación al consultar transacción: referencePayco={reference_payco}")
                # Intentar refrescar el token y reintentar una vez
                self._token = None
                self._token_expires_at = None
                headers = self._get_auth_headers()
                response = requests.request(
                    method="GET",
                    url=url,
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"✅ Detalles obtenidos después de refrescar token: referencePayco={reference_payco}")
                    return data
                else:
                    logger.error(f"❌ Error después de refrescar token: {response.status_code}")
                    return None
            else:
                logger.error(f"❌ Error al consultar transacción: Status {response.status_code}, Response: {response.text[:500]}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error(f"❌ Timeout al consultar transacción: referencePayco={reference_payco}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error de conexión al consultar transacción: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"❌ Error inesperado al consultar transacción: {str(e)}", exc_info=True)
            return None

class PaymentNotificationService:
    """Servicio para notificaciones de pago por email"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def send_payment_notification(self, pago: Pagos, factura: Facturacion, user: User):
        """
        Enviar notificación de pago al usuario por email
        """
        try:
            from app.services.email_service import EmailService
            
            email_service = EmailService()
            
            # Preparar datos para el email
            notification_data = PaymentNotificationData(
                pago_id=pago.id,
                factura_id=factura.id,
                user_email=user.email,
                user_name=user.full_name,
                monto=pago.monto,
                estado=pago.estado.value,
                ref_payco=pago.ref_payco,
                bank_name=pago.bank_name
            )
            
            # Enviar email según el estado
            if pago.estado == EstadoPago.pendiente:
                await self.send_pending_payment_email(email_service, notification_data)
            elif pago.estado == EstadoPago.completado:
                await self.send_payment_confirmation_email(email_service, notification_data, factura)
            elif pago.estado == EstadoPago.fallido:
                await self.send_payment_failed_email(email_service, notification_data)
                
        except Exception as e:
            logger.error(f"Error al enviar notificación de pago: {str(e)}")
    
    async def send_pending_payment_email(self, email_service, data: PaymentNotificationData):
        """Enviar email de pago pendiente"""
        subject = f"Pago Pendiente - Factura #{data.factura_id}"
        template = "payment_pending.html"
        context = {
            "user_name": data.user_name,
            "factura_id": data.factura_id,
            "monto": data.monto,
            "ref_payco": data.ref_payco,
            "bank_name": data.bank_name
        }
        
        await email_service.send_email(
            to_email=data.user_email,
            subject=subject,
            template_name=template,
            context=context
        )
    
    async def send_payment_confirmation_email(self, email_service, data: PaymentNotificationData, factura: Facturacion):
        """Enviar email de confirmación de pago"""
        subject = f"Pago Confirmado - Factura #{data.factura_id}"
        template = "payment_confirmed.html"
        context = {
            "user_name": data.user_name,
            "factura_id": data.factura_id,
            "id_factura": factura.id_factura,
            "monto": data.monto,
            "fecha_pago": factura.fecha_pago.strftime("%d/%m/%Y %H:%M") if factura.fecha_pago else "N/A"
        }
        
        await email_service.send_email(
            to_email=data.user_email,
            subject=subject,
            template_name=template,
            context=context
        )
    
    async def send_payment_failed_email(self, email_service, data: PaymentNotificationData):
        """Enviar email de pago fallido"""
        subject = f"Pago Fallido - Factura #{data.factura_id}"
        template = "payment_failed.html"
        context = {
            "user_name": data.user_name,
            "factura_id": data.factura_id,
            "monto": data.monto,
            "ref_payco": data.ref_payco
        }
        
        await email_service.send_email(
            to_email=data.user_email,
            subject=subject,
            template_name=template,
            context=context
        )
