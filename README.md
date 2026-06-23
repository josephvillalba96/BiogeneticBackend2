# BioGenetic API

API para el proyecto BioGenetic, encargada de la gestión de toros, registros genéticos y facturación.

---

## 🚀 Requisitos e Instalación Rápida

1. **Requisitos:** Python 3.9+ y MySQL.
2. **Clonar e instalar dependencias:**
   ```bash
   git clone <url-del-repositorio>
   cd BiogeneticBackend
   python -m venv .venv
   
   # Activar entorno virtual
   # En Windows (PowerShell):
   .\.venv\Scripts\activate
   # En macOS/Linux:
   source .venv/bin/activate

   pip install -r requirements.txt
   ```

3. **Configuración de Variables de Entorno (`.env`):**
   Crea un archivo `.env` en la raíz del proyecto basándote en la siguiente configuración básica:
   ```ini
   # Base de Datos MySQL
   DATABASE_URL=mysql+pymysql://root:password@localhost/biogenetic

   # Seguridad
   SECRET_KEY=clave_secreta_jwt

   # Google Drive Backup (Opcional)
   GOOGLE_DRIVE_FOLDER_ID=tu_folder_id_de_google_drive
   GOOGLE_DRIVE_CREDENTIALS_FILE=credentials/google_drive_key.json
   ```

---

## 🗄️ Base de Datos y Migraciones (Alembic)

La aplicación utiliza SQLAlchemy como ORM y Alembic para gestionar el esquema de base de datos MySQL.

```bash
# Aplicar todas las migraciones pendientes en tu base de datos
alembic upgrade head

# Crear una nueva migración (tras modificar modelos en app/models/)
alembic revision --autogenerate -m "descripción de cambios"

# Ver historial de migraciones
alembic history
```

---

## ⚡ Ejecución en Desarrollo

Inicia el servidor de desarrollo de Uvicorn con recarga automática:
```bash
uvicorn main:app --reload
```
La aplicación estará disponible en `http://localhost:8000`.

---

## 📦 Copias de Seguridad Automáticas (Backups)

El backend cuenta con una tarea asíncrona en segundo plano que realiza un backup de la base de datos MySQL diariamente a la medianoche (00:00:00) y lo sube automáticamente a la carpeta de Google Drive configurada en tu `.env`.

Para probar el flujo del backup manualmente y diagnosticar posibles errores de conexión, herramientas o credenciales:
```bash
python scripts/run_backup_test.py
```
*Consulta la guía detallada de configuración de Google Cloud Console en el archivo de documentación.*

---

## 📖 Documentación de la API

La documentación interactiva de los endpoints y modelos (Swagger UI) está disponible en:
- **`http://localhost:8000/docs`** (Swagger)
- **`http://localhost:8000/redoc`** (ReDoc)
 