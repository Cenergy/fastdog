# Files module for handling all file types
# This module provides comprehensive file management functionality
# including upload, processing, and metadata extraction for various file formats

from .models import FileManager, FileCategory, FileFormat
from .admin import FileModelAdmin, FileCategoryModelAdmin
from .schemas import (
    FileCategoryBase, FileCategoryCreate, FileCategoryUpdate, FileCategoryResponse,
    FileBase, FileCreate, FileUpdate, FileResponse,
    FileUploadRequest, FileUploadResponse,
    FileBatchDeleteRequest, FileBatchUpdateRequest, FileBatchResponse,
    FileSearchRequest, FileSearchResponse,
    FileStatsResponse
)
from . import crud
from . import routes

__all__ = [
    # Models
    "FileManager",
    "FileCategory", 
    "FileFormat",
    # Admin
    "FileModelAdmin",
    "FileCategoryModelAdmin",
    # Schemas
    "FileCategoryBase", "FileCategoryCreate", "FileCategoryUpdate", "FileCategoryResponse",
    "FileBase", "FileCreate", "FileUpdate", "FileResponse",
    "FileUploadRequest", "FileUploadResponse",
    "FileBatchDeleteRequest", "FileBatchUpdateRequest", "FileBatchResponse",
    "FileSearchRequest", "FileSearchResponse",
    "FileStatsResponse",
    # Modules
    "crud",
    "routes"
]