from sqlalchemy import Column, Integer, String, Float, ForeignKey, Enum, DateTime, Text
from sqlalchemy.orm import relationship
from app.models.base_model import Base, BaseModel
import enum
from datetime import datetime
from sqlalchemy import Numeric  # Asegúrate de tener esto importado

class InputStatus(enum.Enum):
    pending = "Pending"
    processing = "Processing"
    completed = "Completed"
    cancelled = "Cancelled"

class Input(Base, BaseModel):
    __tablename__ = "inputs"
    
    
    escalarilla = Column(String(100), nullable=False) # Esto se lo asigna un usuario administrador 
    bull_id = Column(Integer, ForeignKey("bulls.id"), nullable=False)
    status_id = Column(Enum(InputStatus), default=InputStatus.pending, nullable=False)
    lote = Column(String(50), nullable=False)  # Esto se lo asigna un usuario administrador 
    fv = Column(DateTime, nullable=False)   # Esto se lo asigna un usuario administrador 
  
    quantity_received = Column(Numeric(10, 2), nullable=False)
    quantity_taken = Column(Numeric(10, 2), nullable=False)
    total = Column(Numeric(10, 2), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relaciones
    bull = relationship("Bull", back_populates="inputs")
    user = relationship("User", back_populates="inputs")
    outputs = relationship("Output", back_populates="input", lazy="dynamic")
    
    def __repr__(self):
        return f"<Input {self.id} - Bull: {self.bull_id}>"

class Output(Base, BaseModel):
    __tablename__ = "outputs"
    
    input_id = Column(Integer, ForeignKey("inputs.id"), nullable=False)
    output_date = Column(DateTime, default=datetime.now, nullable=False)
    quantity_output =  Column(Numeric(10, 2), nullable=False)
    remark = Column(Text, nullable=True)
    
    # Relaciones
    input = relationship("Input", back_populates="outputs")
    producciones_embrionarias = relationship("ProduccionEmbrionaria", secondary="produccion_embrionaria_output", back_populates="outputs")
    
    def __repr__(self):
        return f"<Output {self.id} - Input: {self.input_id}>" 