from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crear el motor de la base de datos
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Crear una clase de sesión para la base de datos
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def seed_roles():
    """Insertar roles básicos para la aplicación"""
    from app.models.user import Role
    
    roles = [
        {"name": "Admin"},
        {"name": "Veterinarian"},
        {"name": "Client"}
    ]
    
    db = SessionLocal()
    try:
        for role_data in roles:
            # Verificar si ya existe
            existing_role = db.query(Role).filter(Role.name == role_data["name"]).first()
            if not existing_role:
                role = Role(**role_data)
                db.add(role)
                logger.info(f"Agregado rol: {role_data['name']}")
            else:
                logger.info(f"El rol {role_data['name']} ya existe")
        
        db.commit()
        logger.info("Roles insertados correctamente")
    except Exception as e:
        logger.error(f"Error al insertar roles: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_roles() 