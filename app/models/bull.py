from sqlalchemy import Column, Integer, String, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.models.base_model import Base, BaseModel
import enum

class BullStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"

class Race(Base, BaseModel):
    __tablename__ = "races"
    
    name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    code = Column(String(10), unique=True, index=True, nullable=False)
    
    # Relaciones
    bulls = relationship("Bull", back_populates="race")
    
    def __repr__(self):
        return f"<Race {self.name}>"

class Sex(Base, BaseModel):
    __tablename__ = "sexes"
    
    name = Column(String(50), nullable=False)
    code = Column(Integer, unique=True, index=True, nullable=False)
    
    # Relaciones
    bulls = relationship("Bull", back_populates="sex")
    
    def __repr__(self):
        return f"<Sex {self.name}>"

class Bull(Base, BaseModel):
    __tablename__ = "bulls"
    
    name = Column(String(100), nullable=False)
    registration_number = Column(String(50), nullable=True)
    lote = Column(String(100), nullable=True)  # Esto se lo asigna un usuario administrador
    escalerilla = Column(String(100), nullable=True) 
    description = Column(String(255), nullable=True)
    race_id = Column(Integer, ForeignKey("races.id"), nullable=False)
    sex_id = Column(Integer, ForeignKey("sexes.id"), nullable=False)
    status = Column(Enum(BullStatus), default=BullStatus.active, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relaciones
    race = relationship("Race", back_populates="bulls")
    sex = relationship("Sex", back_populates="bulls")
    user = relationship("User", back_populates="bulls")
    inputs = relationship("Input", back_populates="bull", lazy="dynamic")
    # opus_donante = relationship("Opus", foreign_keys="[Opus.donante_id]", back_populates="donante")
    opus_toro = relationship("Opus", foreign_keys="[Opus.toro_id]", back_populates="toro_rel")
    
    def __repr__(self):
        return f"<Bull {self.name}>" 