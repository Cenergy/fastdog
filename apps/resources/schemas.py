from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime
from .models import ResourceType

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