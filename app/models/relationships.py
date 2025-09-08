"""
Este módulo maneja todas las relaciones entre modelos para evitar dependencias circulares.
"""

from sqlalchemy.orm import relationship
from sqlalchemy import Table, Column, Integer, ForeignKey, DateTime
from datetime import datetime
from app.models.base_model import Base

# Tabla de relación entre usuarios y roles
role_user = Table(
    "role_user",
    Base.metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("user_id", Integer, ForeignKey("users.id"), nullable=False),
    Column("role_id", Integer, ForeignKey("roles.id"), nullable=False),
    Column("created_at", DateTime, default=datetime.now),
    Column("updated_at", DateTime, default=datetime.now, onupdate=datetime.now)
)

# Tabla de relación entre ProduccionEmbrionaria y Output
produccion_embrionaria_output = Table(
    "produccion_embrionaria_output",
    Base.metadata,
    Column("produccion_embrionaria_id", Integer, ForeignKey("produccion_embrionaria.id"), primary_key=True),
    Column("output_id", Integer, ForeignKey("outputs.id"), primary_key=True)
)

def setup_relationships():
    """Configura todas las relaciones entre modelos"""
    from app.models.user import User, Role
    from app.models.bull import Bull
    from app.models.opus import Opus, ProduccionEmbrionaria
    from app.models.input_output import Output

    # Relaciones de Role
    Role.users = relationship("User", secondary=role_user, back_populates="roles")

    # Relaciones de User
    User.roles = relationship("Role", secondary=role_user, back_populates="users")
    User.bulls = relationship("Bull", back_populates="user")
    User.opus = relationship("Opus", back_populates="cliente")
    User.producciones_embrionarias = relationship("ProduccionEmbrionaria", back_populates="cliente")

    # Relaciones de Bull
    Bull.user = relationship("User", back_populates="bulls")
    Bull.race = relationship("Race", back_populates="bulls")
    Bull.sex = relationship("Sex", back_populates="bulls")
    # Bull.opus_donante = relationship("Opus", foreign_keys="[Opus.donante_id]", back_populates="donante")
    Bull.opus_toro = relationship("Opus", foreign_keys="[Opus.toro_id]", back_populates="toro_rel")

    # Relaciones de Opus
    Opus.cliente = relationship("User", back_populates="opus")
    # Opus.donante = relationship("Bull", foreign_keys="[Opus.donante_id]", back_populates="opus_donante")
    Opus.toro_rel = relationship("Bull", foreign_keys="[Opus.toro_id]", back_populates="opus_toro")

    # Relaciones de ProduccionEmbrionaria
    ProduccionEmbrionaria.cliente = relationship("User", back_populates="producciones_embrionarias")
    ProduccionEmbrionaria.opus = relationship("Opus", back_populates="produccion_embrionaria", cascade="all, delete-orphan")
    ProduccionEmbrionaria.outputs = relationship("Output", secondary=produccion_embrionaria_output, back_populates="producciones_embrionarias")

    # Relaciones de Output
    Output.producciones_embrionarias = relationship("ProduccionEmbrionaria", secondary=produccion_embrionaria_output, back_populates="outputs") 