from pymongo import MongoClient
from pymongo.errors import PyMongoError
from pymongo.collection import Collection
from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, Field, SecretStr
import bcrypt
import jwt
from datetime import datetime, timedelta
from functools import wraps
import os
from dotenv import load_dotenv


load_dotenv()


class UserBase(BaseModel):
    """Base Model for user data"""
    username: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_]+$")
    email: Optional[str] = Field(None, pattern=r"^[^@\s]+@[^@\s]+.[^@\s]+$")
    create_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class UserCreate(UserBase):
    """Model for user creation with password"""
    password: SecretStr = Field(..., min_length=8)

class UserInDB(UserBase):
    """Model for user data stored in database"""
    password: bytes
    extra_data: Optional[Dict[str, Any]] = None

class TokenData(BaseModel):
    """Model for JWT token payload"""
    username: str
    exp: datetime
    iat: datetime


