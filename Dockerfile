# Utilizar la versión oficial de Playwright para Python que coincide con requirements.txt (v1.45.0)
# Esta imagen basada en Ubuntu ya tiene todas las dependencias del sistema y los navegadores (Chromium) preinstalados.
FROM mcr.microsoft.com/playwright/python:v1.45.0-jammy

# Evitar que Python escriba archivos .pyc en el disco y habilitar el búfer de salida sin búfer
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Directorio de trabajo en el contenedor
WORKDIR /app

# Instalar dependencias del sistema adicionales necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    mysql-client \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente del proyecto al contenedor
COPY . .

# Exponer el puerto por el cual el contenedor recibirá tráfico (Easypanel detecta/asigna esto)
EXPOSE 8000

# Esperar a que la base de datos esté lista, aplicar migraciones de Alembic y finalmente iniciar la aplicación con Uvicorn
CMD sh -c "python scripts/wait_for_db.py && alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"
