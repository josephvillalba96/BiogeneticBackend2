from sqlalchemy import Column, Integer, String, Enum, DateTime, Boolean
from sqlalchemy.orm import relationship
from app.models.base_model import Base, BaseModel
import enum
from datetime import datetime

class DocumentType(str, enum.Enum):
    identity_card = "identity_card"
    passport = "passport"
    other = "other"

class Role(Base, BaseModel):
    __tablename__ = "roles"
    name = Column(String(50), unique=True, index=True, nullable=False)
    
    def __repr__(self):
        return f"<Role {self.name}>"

class User(Base, BaseModel):
    __tablename__ = "users"
    
    number_document = Column(String(20), unique=True, index=True, nullable=False)
    specialty = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    phone = Column(String(20), nullable=False)
    full_name = Column(String(100), nullable=False)
    type_document = Column(Enum(DocumentType), nullable=False)
    pass_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    profile_image_url = Column(String(255), nullable=True)
    
    # Relaciones
    bulls = relationship("Bull", back_populates="user")
    opus = relationship("Opus", back_populates="cliente")
    roles = relationship("Role", secondary="role_user", back_populates="users")
    inputs = relationship("Input", back_populates="user")
    # Producciones embrionarias asociadas a este usuario
    producciones_embrionarias = relationship("ProduccionEmbrionaria", back_populates="cliente", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User {self.email}>" 