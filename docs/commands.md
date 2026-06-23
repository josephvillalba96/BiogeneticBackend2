# Comandos para el proyecto BioGenetic FastAPI

## Configuración inicial

### 1. Crear un entorno virtual

Para Windows:
```bash
python -m venv venv
venv\Scripts\activate
```

Para macOS/Linux:
```bash
python -m venv venv
source venv/bin/activate
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

## Ejecución del proyecto

### 1. Ejecución con Python

```bash
python main.py
```

### 2. Ejecución con Uvicorn (recomendada para desarrollo)

```bash
uvicorn main:app --reload
```

### 3. Ejecución para producción

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Comandos para desarrollo

### 1. Actualizar dependencias

```bash
pip freeze > requirements.txt
```

### 2. Ejecutar pruebas (cuando se implementen)

```bash
pytest
```

### 3. Verificar formato de código (opcional)

```bash
black .
flake8
``` 