from sqlalchemy import Column, Integer, String, Date, ForeignKey, Time
from sqlalchemy.orm import relationship
from app.models.base_model import Base, BaseModel
from app.models.user import User
from app.models.bull import Bull
from datetime import date


class ProduccionEmbrionaria(Base, BaseModel):
    __tablename__ = "produccion_embrionaria"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    fecha_opu = Column(Date, nullable=False)
    lugar = Column(String(100), nullable=False)
    finca = Column(String(100), nullable=False)
    hora_inicio = Column(Time, nullable=True)
    hora_final = Column(Time, nullable=True)
    envase = Column(String(100), nullable=False)
    fecha_transferencia = Column(Date, nullable=False)  # Se debe calcular al guardar
    
    # Relaciones
    cliente = relationship("User", back_populates="producciones_embrionarias")
    opus = relationship("Opus", back_populates="produccion_embrionaria", cascade="all, delete-orphan")
    outputs = relationship("Output", secondary="produccion_embrionaria_output", back_populates="producciones_embrionarias")



class Opus(Base, BaseModel):
    __tablename__ = "opus"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    # donante_id = Column(Integer, ForeignKey("bulls.id"), nullable=True)
    toro_id = Column(Integer, ForeignKey("bulls.id"), nullable=False)
    fecha = Column(Date, nullable=False)
    toro = Column(String(100), nullable=False)
    race = Column(String(50), nullable=False)
    donante_code = Column(String(100), nullable=False)
    gi = Column(Integer, nullable=False)
    gii = Column(Integer, nullable=False)
    giii = Column(Integer, nullable=False)
    viables = Column(Integer, nullable=False)
    otros = Column(Integer, nullable=False)
    total_oocitos = Column(Integer, nullable=False)
    ctv = Column(Integer, nullable=False)
    clivados = Column(Integer, nullable=False)
    porcentaje_cliv = Column(String(10), nullable=False)
    prevision = Column(Integer, nullable=False)
    porcentaje_prevision = Column(String(10), nullable=False)
    empaque = Column(Integer, nullable=False)
    porcentaje_empaque = Column(String(10), nullable=False)
    vt_dt = Column(Integer, nullable=True)
    porcentaje_vtdt = Column(String(10), nullable=True)
    total_embriones = Column(Integer, nullable=False)
    porcentaje_total_embriones = Column(String(10), nullable=False)

    lugar = Column(String(100), nullable=True)
    finca = Column(String(100), nullable=True)
    order = Column(Integer, nullable=True) #default = 0

    # Relación con Producción Embrionaria
    produccion_embrionaria_id = Column(Integer, ForeignKey("produccion_embrionaria.id"), nullable=False)
    produccion_embrionaria = relationship("ProduccionEmbrionaria", back_populates="opus")
    # cliente = relationship("User", back_populates="opus")
    # toro_rel = relationship("Bull", foreign_keys=[toro_id], back_populates="opus_toro")

    def __repr__(self):
        return f"<Opus(id={self.id}, cliente_id={self.cliente_id}, fecha={self.fecha})>"

