from typing import Optional, List, Dict, Any, TYPE_CHECKING
from pydantic import BaseModel, Field, validator
from app.schemas.base_schema import BaseSchema
from datetime import datetime
from decimal import Decimal
from enum import Enum
from app.models.input_output import InputStatus as ModelInputStatus

if TYPE_CHECKING:
    from app.models.input_output import Input

class InputStatus(str, Enum):
    pending = "Pending"
    processing = "Processing"
    completed = "Completed"
    cancelled = "Cancelled"

    @classmethod
    def from_model(cls, status: ModelInputStatus) -> "InputStatus":
        if status == ModelInputStatus.pending:
            return cls.pending
        elif status == ModelInputStatus.processing:
            return cls.processing
        elif status == ModelInputStatus.completed:
            return cls.completed
        elif status == ModelInputStatus.cancelled:
            return cls.cancelled
        return cls.pending

    def to_model(self) -> ModelInputStatus:
        if self == InputStatus.pending:
            return ModelInputStatus.pending
        elif self == InputStatus.processing:
            return ModelInputStatus.processing
        elif self == InputStatus.completed:
            return ModelInputStatus.completed
        elif self == InputStatus.cancelled:
            return ModelInputStatus.cancelled
        return ModelInputStatus.pending

class InputBase(BaseModel):
    quantity_received: Decimal = Field(..., gt=0)
    bull_id: int
    user_id: int
    quantity_taken: Decimal = Field(Decimal("0.00"), ge=0)
    escalarilla: Optional[str] = None
    lote: Optional[str] = None
    fv: Optional[datetime] = None

    @validator('quantity_taken')
    def validate_quantity_taken(cls, v, values):
        if 'quantity_received' in values and values['quantity_received'] is not None:
            if Decimal(v) > Decimal(values['quantity_received']):
                raise ValueError(f"La cantidad tomada ({v}) no puede ser mayor que la cantidad recibida ({values['quantity_received']})")
        return v

class InputCreate(InputBase):
    pass

class InputUpdate(BaseModel):
    quantity_received: Optional[Decimal] = Field(None, gt=0)
    escalarilla: Optional[str] = None
    bull_id: Optional[int] = None
    status_id: Optional[InputStatus] = None
    lote: Optional[str] = None
    fv: Optional[datetime] = None
    quantity_taken: Optional[Decimal] = Field(None, ge=0)

    @validator('quantity_taken')
    def validate_quantity_taken(cls, v, values):
        if v is not None and 'quantity_received' in values and values['quantity_received'] is not None:
            if Decimal(v) > Decimal(values['quantity_received']):
                raise ValueError(f"La cantidad tomada ({v}) no puede ser mayor que la cantidad recibida ({values['quantity_received']})")
        return v

class InputFilter(BaseModel):
    document_number: Optional[str] = None
    user_name: Optional[str] = None
    bull_name: Optional[str] = None
    bull_register: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None

class InputDetailSchema(BaseModel):
    input_id: int
    quantity_received: Decimal
    escalarilla: str
    status_id: str
    lote: str
    fv: datetime
    quantity_taken: Decimal
    total: Decimal
    created_at: datetime
    bull_name: str
    register_number: Optional[str]
    race_name: str
    client_name: str
    client_document: str

    class Config:
        orm_mode = True
        json_encoders = {Decimal: lambda v: str(v)}

class BullSchema(BaseModel):
    id: int
    name: str
    registration_number: Optional[str]
    race_name: Optional[str] = None

    class Config:
        orm_mode = True
        populate_by_name = True

class InputSchema(BaseSchema):
    quantity_received: Decimal
    escalarilla: str
    bull_id: int
    status_id: InputStatus
    lote: str
    fv: datetime
    quantity_taken: Decimal
    total: Decimal
    user_id: int
    bull: Optional[BullSchema] = None

    class Config:
        orm_mode = True
        json_encoders = {Decimal: lambda v: str(v)}
        populate_by_name = True

    @classmethod
    def from_orm(cls, input_obj: "Input"):
        if not input_obj:
            return None
        try:
            input_dict = {
                "id": input_obj.id,
                "quantity_received": Decimal(input_obj.quantity_received),
                "escalarilla": input_obj.escalarilla,
                "bull_id": input_obj.bull_id,
                "lote": input_obj.lote,
                "fv": input_obj.fv,
                "quantity_taken": Decimal(input_obj.quantity_taken),
                "total": Decimal(input_obj.total),
                "user_id": input_obj.user_id,
                "created_at": input_obj.created_at,
                "updated_at": input_obj.updated_at
            }

            input_dict["status_id"] = InputStatus.from_model(input_obj.status_id) if hasattr(input_obj, "status_id") and input_obj.status_id else InputStatus.pending

            if hasattr(input_obj, "bull") and input_obj.bull:
                input_dict["bull"] = {
                    "id": input_obj.bull.id,
                    "name": input_obj.bull.name,
                    "registration_number": input_obj.bull.registration_number,
                    "race_name": input_obj.bull.race.name if input_obj.bull.race else None
                }

            return cls(**input_dict)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error al convertir Input a InputSchema: {str(e)}")
            logger.error(f"Input: {input_obj.__dict__ if input_obj else None}")
            return None

class OutputBase(BaseModel):
    input_id: int
    quantity_output: Decimal = Field(..., gt=0)
    remark: Optional[str] = None

class OutputCreate(BaseModel):
    quantity_output: Decimal = Field(..., gt=0)
    output_date: Optional[datetime] = None
    remark: Optional[str] = None

class OutputUpdate(BaseModel):
    quantity_output: Optional[Decimal] = Field(None, gt=0)
    output_date: Optional[datetime] = None
    remark: Optional[str] = None

class OutputSchema(BaseSchema):
    id: int
    input_id: int
    output_date: datetime
    quantity_output: Decimal
    remark: Optional[str] = None

    class Config:
        orm_mode = True
        json_encoders = {Decimal: lambda v: str(v)}

class OutputDetailSchema(BaseModel):
    output_id: int
    input_id: int
    output_date: datetime
    quantity_output: Decimal
    remark: Optional[str] = None
    escalarilla: str
    lote: str
    quantity_received: Decimal
    bull_id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
        json_encoders = {Decimal: lambda v: str(v)}
