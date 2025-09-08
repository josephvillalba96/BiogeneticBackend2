from typing import Optional, TYPE_CHECKING
from pydantic import BaseModel, Field
from app.schemas.base_schema import BaseSchema
from enum import Enum
from app.models.bull import BullStatus
from datetime import datetime

if TYPE_CHECKING:
    from app.models.bull import Bull

class RaceSchema(BaseSchema):
    name: str
    description: str
    code: str

class RaceCreate(BaseModel):
    name: str
    description: str
    code: str

class SexSchema(BaseSchema):
    name: str
    code: int

class SexCreate(BaseModel):
    name: str
    code: int

class BullBase(BaseModel):
    name: str
    registration_number: Optional[str] = None
    race_id: int
    sex_id: int
    status: Optional[BullStatus] = BullStatus.active
    lote: Optional[str] = None
    escalerilla: Optional[str] = None
    description: Optional[str] = None

    class Config:
        from_attributes = True
        use_enum_values = True
        populate_by_name = True
        

class BullCreate(BullBase):
    pass

class BullUpdate(BullBase):
    name: Optional[str] = None
    registration_number: Optional[str] = None
    race_id: Optional[int] = None
    sex_id: Optional[int] = None
    status: Optional[BullStatus] = None
    lote: Optional[str] = None
    escalerilla: Optional[str] = None
    description: Optional[str] = None

class BullSchema(BaseSchema, BullBase):
    user_id: int
    class Config:
        from_attributes = True
        use_enum_values = True
        populate_by_name = True

class UserInfoSchema(BaseModel):
    id: int
    full_name: str
    email: str
    number_document: str
    phone: str
    type_document: Optional[str] = None
    specialty: Optional[str] = None

class BullDetailSchema(BaseModel):
    id: int
    name: str
    registration_number: Optional[str] = None
    race_id: int
    race_name: Optional[str] = None
    sex_id: int
    sex_name: Optional[str] = None
    status: Optional[BullStatus] = None
    lote: Optional[str] = None
    escalerilla: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    user: UserInfoSchema
    
    class Config:
        from_attributes = True
        use_enum_values = True
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class BullWithAvailableSamplesSchema(BaseModel):
    id: int
    name: str
    registration_number: Optional[str] = None
    race_id: int
    race_name: Optional[str] = None
    sex_id: int
    sex_name: Optional[str] = None
    status: Optional[BullStatus] = None
    lote: Optional[str] = None
    escalerilla: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    total_available: float = Field(description="Cantidad total de muestras disponibles")
    
    class Config:
        from_attributes = True
        use_enum_values = True
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        } 