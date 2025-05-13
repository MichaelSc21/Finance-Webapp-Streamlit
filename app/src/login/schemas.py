from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime


class UserBase(BaseModel):
    """Base user model with common fields"""
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        pattern="^[a-zA-Z0-9_]+$",
        description="Username must be alphanumeric with underscores"
    )
    email: Optional[str] = Field(
        None,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
        description="Must be a valid email address"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)



class UserCategories(BaseModel):
    """Model for user transaction categories"""
    categories: Dict[str, List[str]] = Field(
        default_factory=lambda: {"Uncategorised": []},
        description="Dictionary of categories and their keywords"
    )

    @validator('categories')
    def validate_categories(cls, v):
        """Ensure categories dictionary has proper structure"""
        for category, keywords in v.items():
            if not isinstance(category, str):
                raise ValueError("Category names must be strings")
            if not isinstance(keywords, list):
                raise ValueError("Keywords must be a list")
            for keyword in keywords:
                if not isinstance(keyword, str):
                    raise ValueError("All keywords must be strings")
        return v


# This model is not needed as the password is no longer stored in the database
class UserInDB(UserBase, UserCategories):
    """Complete user model for database storage"""
    extra_data: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional user metadata"
    )


# Delete this in the future if it is not being used
class UserResponse(UserBase, UserCategories):
    """Model for returning user data (without sensitive info)"""
    pass


class TokenData(BaseModel):
    """Model for JWT token payload"""
    sub: str
    email: str
    exp: datetime
    iat: datetime


class CategoryUpdate(BaseModel):
    """Model for updating categories"""
    category_name: str = Field(..., description="Name of the category")
    keywords: List[str] = Field(
        default_factory=list,
        description="List of keywords for this category"
    )

    @validator('category_name')
    def validate_category_name(cls, v):
        if not v.strip():
            raise ValueError("Category name cannot be empty")
        return v.strip()


class KeywordOperation(BaseModel):
    """Model for adding/removing keywords"""
    keyword: str = Field(..., description="The keyword to add/remove")

    @validator('keyword')
    def validate_keyword(cls, v):
        if not v.strip():
            raise ValueError("Keyword cannot be empty")
        return v.strip()



class DatabaseStatus(BaseModel):
    """Model for database connection status"""
    connected: bool
    database_name: str
    collections: List[str]
    users_count: int