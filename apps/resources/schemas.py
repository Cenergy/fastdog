from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime
from .models import ResourceType, ModelFormat

class ResourceBase(BaseModel):
    name: str
    description: Optional[str] = None
    type: ResourceType
    url: HttpUrl
    image_url: Optional[HttpUrl] = None
    is_active: bool = True

class ResourceCreate(ResourceBase):
    pass

class ResourceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[ResourceType] = None
    url: Optional[HttpUrl] = None
    image_url: Optional[HttpUrl] = None
    is_active: Optional[bool] = None

class ResourceInDB(ResourceBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Model3DCategory schemas
class Model3DCategoryBase(BaseModel):
    name: str
    description: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True

class Model3DCategoryCreate(Model3DCategoryBase):
    pass

class Model3DCategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None

class Model3DCategoryInDB(Model3DCategoryBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Model3D schemas
class Model3DBase(BaseModel):
    name: str
    description: Optional[str] = None
    model_file_url: Optional[str] = None
    binary_file_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    is_active: bool = True
    is_public: bool = True

class Model3DCreate(Model3DBase):
    category_id: Optional[int] = None

class Model3DUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[int] = None
    model_file_url: Optional[str] = None
    binary_file_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    is_active: Optional[bool] = None
    is_public: Optional[bool] = None

class Model3DInDB(Model3DBase):
    id: int
    uuid: str
    category_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True