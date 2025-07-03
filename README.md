# BioGenetic API

API para el proyecto BioGenetic.

## Requisitos

- Python 3.9+
- pip (gestor de paquetes de Python)
- MySQL 5.7+ o MariaDB 10.3+

## Instalación

1. Clonar el repositorio:
```bash
git clone <url-del-repositorio>
cd BioGeneticFastApi
```

2. Crear un entorno virtual:
```bash
python -m venv venv
```

3. Activar el entorno virtual:

En Windows:
```bash
venv\Scripts\activate
```

En macOS/Linux:
```bash
source venv/bin/activate
```

4. Instalar dependencias:
```bash
pip install -r requirements.txt
```

5. Configurar la base de datos MySQL:

   a. Crear la base de datos:
   ```sql
   CREATE DATABASE biogenetic CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

   b. Crear un usuario (opcional, puede usar root):
   ```sql
   CREATE USER 'biogenetic_user'@'localhost' IDENTIFIED BY 'password';
   GRANT ALL PRIVILEGES ON biogenetic.* TO 'biogenetic_user'@'localhost';
   FLUSH PRIVILEGES;
   ```

   c. Configurar las variables de entorno en un archivo `.env` en la raíz del proyecto:
   ```
   DEBUG=True
   API_HOST=0.0.0.0
   API_PORT=8000
   SECRET_KEY=b9ee2529f3e77b0e32c24b8774f15e8fa7c1058e1f2427f4d0b0063ed23abf2f
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   
   # Configuración MySQL
   DB_HOST=localhost
   DB_PORT=3306
   DB_USER=root
   DB_PASSWORD=your_password
   DB_NAME=biogenetic
   ```

## Migración de la Base de Datos

La aplicación usa SQLAlchemy como ORM y Alembic para las migraciones.

### Inicializar Alembic (Primera vez)

```bash
# Instalar Alembic si no está instalado
pip install alembic

# Inicializar la configuración de Alembic
alembic init migrations
```

### Configurar Alembic

Editar `migrations/env.py` para cargar los modelos y la configuración:

```python
# Agregar al principio de env.py:
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.models.base_model import Base
from app.models.user import User, Role
from app.models.bull import Bull, Race, Sex
from app.models.input_output import Input, Output
from app.config import settings

# Usar la URL de conexión desde la configuración de la aplicación
config.set_main_option("sqlalchemy.url", 
                       f"mysql+pymysql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")

# También en env.py, actualizar la variable target_metadata:
target_metadata = Base.metadata
```

### Crear una migración

```bash
# Generar una migración automática basada en los modelos
alembic revision --autogenerate -m "Migración inicial"
```

### Aplicar migraciones

```bash
# Aplicar todas las migraciones pendientes
alembic upgrade head

# Alternativamente, retroceder a una versión específica
alembic downgrade <revision_id>
```

### Ver historial de migraciones

```bash
# Ver migraciones aplicadas y pendientes
alembic history
```

## Ejecución

### Versión sencilla (funciona con todas las versiones de Python):

```bash
python simple_api.py
```

### Versión FastAPI (si tienes Python 3.11 o 3.12):

```bash
python main.py
```

O también:
```bash
uvicorn main:app --reload
```

## Endpoints API

### Autenticación
- `POST /api/auth/register` - Registrar un nuevo usuario
- `POST /api/auth/login` - Iniciar sesión y obtener token
- `GET /api/auth/me` - Obtener perfil de usuario actual

### Usuarios
- `GET /api/users/` - Listar todos los usuarios
- `GET /api/users/{id}` - Obtener un usuario por ID
- `PUT /api/users/{id}` - Actualizar un usuario
- `DELETE /api/users/{id}` - Eliminar un usuario

### Roles
- `GET /api/users/roles/` - Listar todos los roles
- `POST /api/users/roles/` - Crear un nuevo rol
- `PUT /api/users/{user_id}/roles/{role_id}` - Asignar rol a usuario
- `DELETE /api/users/{user_id}/roles/{role_id}` - Quitar rol de usuario

## Notas

- La API estará disponible en: http://localhost:8000
- Las rutas disponibles son:
  - `/`: Mensaje de bienvenida
  - `/api/status`: Estado del servicio 