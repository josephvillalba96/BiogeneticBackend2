from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from app.schemas.base_schema import BaseSchema
from enum import Enum

class RoleSchema(BaseSchema):
    name: str

class RoleCreate(BaseModel):
    name: str

class UserStatus(str, Enum):
    active = "Active"
    inactive = "Inactive"

class DocumentType(str, Enum):
    identity_card = "identity_card"
    passport = "passport"
    other = "other"

class UserBase(BaseModel):
    number_document: str
    specialty: str
    email: EmailStr
    phone: str
    full_name: str
    type_document: DocumentType
    profile_image_url: Optional[str] = None

class UserCreate(UserBase):
    password: str
    is_admin: Optional[bool] = False
    profile_image_url: Optional[str] = None

class UserCreateByAdmin(UserCreate):
    roles: List[int] = []  # IDs de los roles a asignar

class UserUpdate(BaseModel):
    number_document: Optional[str] = None
    specialty: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    full_name: Optional[str] = None
    type_document: Optional[DocumentType] = None
    password: Optional[str] = None
    profile_image_url: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserSchema(UserBase, BaseSchema):
    roles: List[RoleSchema] = []
    
    class Config:
        from_attributes = True

class RoleUserSchema(BaseSchema):
    user_id: int
    role_id: int

class RoleUserCreate(BaseModel):
    user_id: int
    role_id: int

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: Optional[int] = None 