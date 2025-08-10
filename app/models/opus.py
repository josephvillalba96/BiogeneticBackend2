from sqlalchemy import Column, Integer, String, Date, ForeignKey, Time, Text, Boolean
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
    observacion = Column(Text, nullable=True)  # Nuevo campo para observaciones
    
    # Relaciones
    cliente = relationship("User", back_populates="producciones_embrionarias")
    opus = relationship("Opus", back_populates="produccion_embrionaria", cascade="all, delete-orphan")
    outputs = relationship("Output", secondary="produccion_embrionaria_output", back_populates="producciones_embrionarias")
    transferencias = relationship("Transferencia", back_populates="produccion_embrionaria", cascade="all, delete-orphan")



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


class Transferencia(Base, BaseModel):
    __tablename__ = "transferencias"

    id = Column(Integer, primary_key=True, index=True)
    fecha_transferencia = Column(Date, nullable=False)
    veterinario_responsable = Column(String(100), nullable=False)
    fecha = Column(Date, nullable=False)
    lugar = Column(String(100), nullable=False)
    finca = Column(String(100), nullable=False)
    observacion = Column(Text, nullable=True)
    produccion_embrionaria_id = Column(Integer, ForeignKey("produccion_embrionaria.id"), nullable=False)
    cliente_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    initial_report = Column(Boolean, nullable=False, default=True)

    produccion_embrionaria = relationship("ProduccionEmbrionaria", back_populates="transferencias")
    cliente = relationship("User")
    reportes = relationship("ReportTransfer", back_populates="transferencia", cascade="all, delete-orphan")

class ReportTransfer(Base, BaseModel):
    __tablename__ = "report_transfers"

    id = Column(Integer, primary_key=True, index=True)
    donadora = Column(String(100), nullable=False)
    raza_donadora = Column(String(100), nullable=False)
    toro = Column(String(100), nullable=False)
    toro_raza = Column(String(100), nullable=False)
    estado = Column(String(100), nullable=False)
    receptora = Column(String(100), nullable=False)
    horario = Column(String(100), nullable=False)
    dx = Column(String(100), nullable=False)
    dxx = Column(String(100), nullable=False)
    dxxx = Column(String(100), nullable=False)
    transferencia_id = Column(Integer, ForeignKey("transferencias.id"), nullable=False)

    transferencia = relationship("Transferencia", back_populates="reportes")

