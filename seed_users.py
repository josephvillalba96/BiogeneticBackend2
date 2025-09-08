from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.utils.security import get_password_hash
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crear el motor de la base de datos
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Crear una clase de sesión para la base de datos
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_role_by_name(db, role_name):
    """Obtener un rol por su nombre"""
    from app.models.user import Role
    return db.query(Role).filter(Role.name == role_name).first()

def seed_admin_user():
    """Crear un usuario administrador por defecto si no existe"""
    from app.models.user import User
    
    admin_data = {
        "number_document": "1234567890",
        "specialty": "Administrador",
        "email": "admin@biogenetic.com",
        "phone": "1234567890",
        "full_name": "Administrador",
        "type_document": "identity_card",
        "pass_hash": get_password_hash("admin123")
    }
    
    db = SessionLocal()
    try:
        # Verificar si ya existe
        existing_user = db.query(User).filter(User.email == admin_data["email"]).first()
        if not existing_user:
            # Crear el usuario
            admin_user = User(**admin_data)
            # Asignar rol de administrador
            admin_role = get_role_by_name(db, "Admin")
            if admin_role:
                admin_user.roles.append(admin_role)
            db.add(admin_user)
            db.commit()
            logger.info(f"Creado usuario administrador: {admin_data['email']}")
        else:
            logger.info(f"El usuario administrador {admin_data['email']} ya existe")
    except Exception as e:
        logger.error(f"Error al crear usuario administrador: {e}")
        db.rollback()
    finally:
        db.close()

def seed_regular_user():
    """Crear un usuario regular por defecto si no existe"""
    from app.models.user import User
    
    user_data = {
        "number_document": "9876543210",
        "specialty": "Veterinario",
        "email": "user@biogenetic.com",
        "phone": "9876543210",
        "full_name": "Usuario Normal",
        "type_document": "identity_card",
        "pass_hash": get_password_hash("user123")
    }
    
    db = SessionLocal()
    try:
        # Verificar si ya existe
        existing_user = db.query(User).filter(User.email == user_data["email"]).first()
        if not existing_user:
            # Crear el usuario
            regular_user = User(**user_data)
            # Asignar rol de usuario
            user_role = get_role_by_name(db, "User")
            if user_role:
                regular_user.roles.append(user_role)
            db.add(regular_user)
            db.commit()
            logger.info(f"Creado usuario regular: {user_data['email']}")
        else:
            logger.info(f"El usuario regular {user_data['email']} ya existe")
    except Exception as e:
        logger.error(f"Error al crear usuario regular: {e}")
        db.rollback()
    finally:
        db.close()

def seed_client_user():
    """Crear un usuario cliente por defecto si no existe"""
    from app.models.user import User
    
    client_data = {
        "number_document": "5678901234",
        "specialty": "Ganadero",
        "email": "client@biogenetic.com",
        "phone": "5678901234",
        "full_name": "Cliente Regular",
        "type_document": "identity_card",
        "pass_hash": get_password_hash("client123")
    }
    
    db = SessionLocal()
    try:
        # Verificar si ya existe
        existing_user = db.query(User).filter(User.email == client_data["email"]).first()
        if not existing_user:
            # Crear el usuario
            client_user = User(**client_data)
            # Asignar rol de cliente
            client_role = get_role_by_name(db, "Client")
            if client_role:
                client_user.roles.append(client_role)
            db.add(client_user)
            db.commit()
            logger.info(f"Creado usuario cliente: {client_data['email']}")
        else:
            logger.info(f"El usuario cliente {client_data['email']} ya existe")
    except Exception as e:
        logger.error(f"Error al crear usuario cliente: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_admin_user()
    seed_regular_user()
    seed_client_user() 