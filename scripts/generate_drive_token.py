import sys
import os
from pathlib import Path

# Agregar el directorio raíz al PATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Intentar instalar dependencias necesarias si faltan
try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print("Instalando 'google-auth-oauthlib' para poder autenticar en el navegador...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "google-auth-oauthlib"], check=True)
    from google_auth_oauthlib.flow import InstalledAppFlow

from app.config import BASE_DIR

SCOPES = ['https://www.googleapis.com/auth/drive.file']

def main():
    print("=== CONFIGURACIÓN DE CREDENCIALES OAUTH 2.0 PARA GOOGLE DRIVE ===")
    
    credentials_dir = BASE_DIR / "credentials"
    os.makedirs(credentials_dir, exist_ok=True)
    
    token_path = credentials_dir / "google_drive_token.json"
    
    # Buscar archivos que empiecen con client_secret*.json o client_secrets.json
    secrets_files = list(credentials_dir.glob("client_secret*.json"))
    if not secrets_files:
        secrets_files = list(credentials_dir.glob("client_secrets.json"))
        
    if not secrets_files:
        secrets_path = credentials_dir / "client_secrets.json"
        print(f"\n[ERROR] No se encontró ningún archivo de credenciales de cliente OAuth (ej. '{secrets_path}')")
        print("\nPara generar este archivo:")
        print("1. Ve a Google Cloud Console (https://console.cloud.google.com/).")
        print("2. Ve a 'APIs y Servicios' > 'Credenciales'.")
        print("3. Haz clic en 'Crear credenciales' > 'ID de cliente de OAuth'.")
        print("   * Si te lo pide, primero configura la Pantalla de Consentimiento de OAuth externa y agrega tu correo como usuario de prueba.")
        print("4. Selecciona tipo de aplicación: 'Aplicación de escritorio' (Desktop App).")
        print("5. Descarga el archivo JSON de credenciales, renombralo como 'client_secrets.json' o déjalo con su nombre original y colócalo en la carpeta 'credentials/'.")
        sys.exit(1)
        
    secrets_path = secrets_files[0]
    print(f"\n[OK] Archivo de secretos encontrado: '{secrets_path.name}'")
        
    print(f"\nLeyendo '{secrets_path}'...")
    try:
        # Ejecutar el flujo de autenticación abriendo el navegador del usuario
        flow = InstalledAppFlow.from_client_secrets_file(str(secrets_path), SCOPES)
        print("\nAbrir el navegador para iniciar sesión y conceder permisos...")
        creds = flow.run_local_server(port=0)
        
        # Guardar las credenciales
        with open(token_path, 'w') as token_file:
            token_file.write(creds.to_json())
            
        print(f"\n[SUCCESS] Credenciales guardadas en: {token_path}")
        print("Ahora la aplicación utilizará estas credenciales de usuario y no tendrás problemas de límite de cuota (Storage Quota Exceeded).")
        
    except Exception as e:
        print(f"\n[ERROR] Ocurrió un error durante la autenticación: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
