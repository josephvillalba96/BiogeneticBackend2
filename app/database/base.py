# Aquí se configurará la conexión a la base de datos
# Por ahora solo es un esqueleto

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings
import pymysql

# URL de la base de datos MySQL
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

# Crear el motor de la base de datos
engine = create_engine(
    SQLALCHEMY_DATABASE_URL
)

# Crear una clase de sesión para la base de datos
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Importar todos los modelos
from app.models import Base, User, Role, Bull, Race, Sex, Opus
from app.models.relationships import setup_relationships

# Configurar las relaciones
setup_relationships()

# Función para obtener una sesión de la base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class Database:
    def __init__(self):
        self.connected = False
        
    def connect(self):
        # Lógica para conectar a la base de datos
        self.connected = True
        return self.connected
        
    def disconnect(self):
        # Lógica para desconectar de la base de datos
        self.connected = False

db = Database() 