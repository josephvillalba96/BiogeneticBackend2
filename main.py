from fastapi import FastAPI, Depends, Security, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from app.routes.api import router as api_router
from app.database.base import engine
# Importar todos los modelos para asegurar que se registren correctamente
from app.models import Base, verify_all_models
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from app.utils.security import AuthenticationMiddleware
from fastapi.responses import HTMLResponse
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# No crear las tablas automáticamente al iniciar la aplicación
# ya que esto lo manejamos con Alembic
# Base.metadata.create_all(bind=engine)

# Verificar que todos los modelos estén mapeados correctamente
verify_all_models()

# Configuración de seguridad para Swagger
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login", auto_error=False)
security_bearer = HTTPBearer(auto_error=False)

app = FastAPI(
    title="BioGenetic API",
    description="API para el proyecto BioGenetic",
    version="0.1.0",
    swagger_ui_parameters={
        "persistAuthorization": True,
        "displayRequestDuration": True,
        "tryItOutEnabled": True,
        "syntaxHighlight.theme": "monokai",
        "defaultModelsExpandDepth": -1,
        "docExpansion": "list",
        "filter": True,
        "withCredentials": True,
    },
)

# Configuración de seguridad para Swagger
app.swagger_ui_oauth2_redirect_url = "/oauth2-redirect"
app.swagger_ui_init_oauth = {
    "usePkceWithAuthorizationCodeGrant": False,
    "useBasicAuthenticationWithAccessCodeGrant": False,
    "clientId": "swagger",
}

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Agregar el middleware de autenticación
app.add_middleware(AuthenticationMiddleware)

# Incluir rutas
app.include_router(api_router)

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>BioGenetic API</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {
                font-family: Arial, sans-serif;
                line-height: 1.6;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                text-align: center;
            }
            h1 {
                color: #4a4a4a;
                margin-bottom: 20px;
            }
            .container {
                margin-top: 30px;
            }
            .button {
                display: inline-block;
                background-color: #4CAF50;
                color: white;
                padding: 10px 20px;
                margin: 10px;
                text-decoration: none;
                border-radius: 4px;
                font-weight: bold;
            }
            .button:hover {
                background-color: #45a049;
            }
        </style>
    </head>
    <body>
        <h1>Bienvenido a la API de BioGenetic</h1>
        
        <p>API para el proyecto BioGenetic, gestión de toros y registros genéticos.</p>
        
        <div class="container">
            <a href="/docs" class="button">Documentación API (Swagger)</a>
            <a href="/auth-help" class="button">Ayuda de Autenticación</a>
        </div>
    </body>
    </html>
    """

@app.get("/auth-help", response_class=HTMLResponse)
async def auth_help():
    """Página de ayuda para configurar la autenticación JWT"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Ayuda de Autenticación BioGenetic API</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {
                font-family: Arial, sans-serif;
                line-height: 1.6;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }
            h1 {
                color: #4a4a4a;
                border-bottom: 1px solid #eaeaea;
                padding-bottom: 10px;
            }
            pre {
                background-color: #f5f5f5;
                padding: 15px;
                border-radius: 5px;
                overflow-x: auto;
            }
            .container {
                margin-top: 20px;
            }
            label {
                display: block;
                margin-bottom: 5px;
                font-weight: bold;
            }
            input[type="text"] {
                width: 100%;
                padding: 8px;
                margin-bottom: 10px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            button {
                background-color: #4CAF50;
                color: white;
                padding: 10px 15px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
            }
            button:hover {
                background-color: #45a049;
            }
            .note {
                background-color: #fff3cd;
                border-left: 4px solid #ffc107;
                padding: 10px;
                margin: 15px 0;
            }
        </style>
    </head>
    <body>
        <h1>Configuración de Autenticación para BioGenetic API</h1>
        
        <div class="note">
            <p>Esta página te ayudará a configurar el token JWT para usar toda la API.</p>
        </div>

        <h2>Pasos para autenticarse:</h2>
        <ol>
            <li>Primero, inicia sesión con <code>/api/auth/login</code> para obtener un token JWT</li>
            <li>Copia ese token y pégalo en el campo debajo</li>
            <li>Haz clic en "Configurar Token" para guardar el token en una cookie</li>
            <li>Regresa a la documentación Swagger para usar la API</li>
        </ol>

        <div class="container">
            <form id="tokenForm">
                <label for="token">Token JWT:</label>
                <input type="text" id="token" name="token" placeholder="Pega aquí tu token JWT" required>
                <button type="submit">Configurar Token</button>
            </form>
        </div>

        <script>
            document.getElementById('tokenForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const token = document.getElementById('token').value.trim();
                
                try {
                    const response = await fetch('/api/auth/token-to-cookie', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            token: token,
                            redirect_url: '/docs'
                        })
                    });
                    
                    const data = await response.json();
                    
                    if (data.status === 'success') {
                        alert('Token configurado correctamente. Serás redirigido a la documentación API.');
                        window.location.href = data.redirect || '/docs';
                    } else {
                        alert('Error al configurar el token: ' + data.message);
                    }
                } catch (error) {
                    alert('Error al procesar la solicitud: ' + error.message);
                }
            });
        </script>
    </body>
    </html>
    """

# Personalizar la documentación OpenAPI para usar autorización simplificada
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    logger.info("Generando esquema OpenAPI personalizado")
        
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Modificar la configuración de seguridad
    openapi_schema["components"]["securitySchemes"] = {
        "Bearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Ingresa el token JWT sin el prefijo 'Bearer'. Todos los endpoints quedarán autenticados automáticamente."
        }
    }
    
    # Aplicar seguridad globalmente a todos los endpoints
    openapi_schema["security"] = [{"Bearer": []}]
    
    # Asegurarse de que todos los paths tengan configuración de seguridad
    # excepto login y register
    for path in openapi_schema["paths"]:
        # Excluir rutas de autenticación
        if path.endswith("/auth/login") or path.endswith("/auth/register") or path == "/":
            continue
            
        for method in openapi_schema["paths"][path]:
            if method.lower() != "options":  # No aplicar a CORS preflight
                if path not in ["/api/auth/login", "/api/auth/register", "/"]:
                    # Aplicar seguridad explícitamente a cada endpoint
                    openapi_schema["paths"][path][method]["security"] = [{"Bearer": []}]
                    
                    # Asegurarse de que los parámetros no dupliquen la autorización
                    if "parameters" in openapi_schema["paths"][path][method]:
                        # Filtrar parámetros duplicados de autorización
                        openapi_schema["paths"][path][method]["parameters"] = [
                            param for param in openapi_schema["paths"][path][method]["parameters"]
                            if not (param.get("name") == "Authorization" and param.get("in") == "header")
                        ]
    
    logger.info("Esquema OpenAPI personalizado generado correctamente")
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 