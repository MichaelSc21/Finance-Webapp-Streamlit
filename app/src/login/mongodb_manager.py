from pymongo import MongoClient
from pymongo.errors import PyMongoError
import streamlit as st
import bcrypt

# Dependencies for managing tokens
from datetime import datetime, timedelta
from dotenv import load_dotenv
import jwt
import os
from functools import wraps

# For static typing
from .models import UserBase, UserCreate, UserInDB, TokenData
from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, Field, SecretStr

# Load environment variables
load_dotenv()


class JWTAuthManager:
    def __init__(self, 
                secret_key: str, 
                algorithm: str ='HS256', 
                token_expiry_days: int = 1) -> None:
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.token_expiry_days = token_expiry_days


    def create_token(
                self, 
                username: str, 
                extra_data: Optional[Dict[str, Any]] = None) -> str:
        """Create a JWT token for the user"""
        payload = TokenData(
            username=username,
            exp=datetime.utcnow() + timedelta(days=self.token_expiry_days),
            iat=datetime.utcnow()
        ).model_dump()
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Optional[TokenData]:
        """Verify a JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            st.error("Token has expired")
            return None
        except jwt.InvalidTokenError:
            st.error("Invalid token")
            return None





class MongoDBManager:
    def __init__(self, connection_string: str, db_name: str) -> None:
        self.client = MongoClient(connection_string)
        self.db = self.client[db_name]
        self.users_collection = self.db['users']
        
    @staticmethod
    def _hash_password(password: Union[str, SecretStr]) -> bytes:
        """
        Hash a password for storing.
        
        Args:
            password: Plain text password
            
        Returns:
            bytes: Hashed password
        """
        if isinstance(password, SecretStr):
            password = password.get_secret_value()
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    @staticmethod
    def _check_password(hashed_password: bytes, 
                    user_password: Union[str, SecretStr]) -> bool:
        """
        Verify a stored password against one provided by user
        
        Args:
            hashed_password: bytes - Password hash from database
            user_password: str - Password provided by user
            
        Returns:
            bool: True if passwords match, False otherwise
        """
        if isinstance(user_password, SecretStr):
            user_password = user_password.get_secret_value()
        return bcrypt.checkpw(user_password.encode('utf-8'), hashed_password)



    def add_user(self, 
                user_data: UserCreate,
                extra_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Add a new user with hashed password
        
        Args:
            user_data: UserCreate model with username, email, and password
            extra_data: Additional user data
            
        Returns:
            True if user was created successfully
        """
        if self.users_collection.find_one({'username': user_data.username}):
            return False
            
        hashed_password = self._hash_password(user_data.password)
        
        user_in_db = UserInDB(
            **user_data.model_dump(exclude={'password'}),
            password=hashed_password,
            extra_data=extra_data
        )
        
        try:
            self.users_collection.insert_one(user_in_db.dict())
            return True
        except PyMongoError as e:
            raise RuntimeError(f"Database error: {str(e)}")
        
        
    def verify_user(
        self, 
        username: str, 
        password: Union[str, SecretStr]
        ) -> Optional[UserInDB]:
        """
        Verify user credentials
        
        Args:
            username: Username to verify
            password: Password to verify
            
        Returns:
            UserInDB if valid, None otherwise
        """
        user_data = self.users_collection.find_one({'username': username})
        if not user_data:
            return None
            
        try:
            user = UserInDB(**user_data)
            if self._check_password(user.password, password):
                return user
            return None
        except Exception:
            return None
    
    def update_user_password(
        self, 
        username: str, 
        new_password: Union[str, SecretStr]
        ) -> bool:
        """
        Update a user's password
        
        Args:
            username: Username to update
            new_password: New plain text password
            
        Returns:
            bool: True if update was successful
        """
        hashed_password = self._hash_password(new_password)
        result = self.users_collection.update_one(
            {'username': username},
            {'$set': {
                'password': hashed_password,
                'updated_at': datetime.utcnow()
            }}
        )
        return result.modified_count > 0


    def get_user_data(
        self,
        username: str,
        exclude_password: bool = True
    ) -> Optional[UserBase]:
        """
        Get user data
        
        Args:
            username: Username to lookup
            exclude_password: Whether to exclude password
            
        Returns:
            User data without password by default
        """
        projection = {'password': 0} if exclude_password else None
        user_data = self.users_collection.find_one(
            {'username': username},
            projection
        )
        return UserBase(**user_data) if user_data else None


    def update_user(
        self,
        username: str,
        update_data: Dict[str, Any]
    ) -> bool:
        """
        Update user information
        
        Args:
            username: Username to update
            update_data: Dictionary of fields to update
            
        Returns:
            True if update was successful
        """
        update_data['updated_at'] = datetime.utcnow()
        result = self.users_collection.update_one(
            {'username': username},
            {'$set': update_data}
        )
        return result.modified_count > 0
    
    
    def delete_user(self, username: str) -> bool:
        """
        Delete a user
        
        Args:
            username: Username to delete
            
        Returns:
            True if deletion was successful
        """
        result = self.users_collection.delete_one({'username': username})
        return result.deleted_count > 0
    
    
    def add_data(
        self,
        collection_name: str,
        data: Dict[str, Any]
    ) -> str:
        """
        Add data to any collection
        
        Args:
            collection_name: Name of the collection
            data: Data to insert
            
        Returns:
            ID of the inserted document
        """
        collection = self.db[collection_name]
        result = collection.insert_one(data)
        return str(result.inserted_id)
    
    
    def get_data(
        self,
        collection_name: str,
        query: Dict[str, Any] = {},
        projection: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get data from any collection
        
        Args:
            collection_name: Name of the collection
            query: Query filter
            projection: Fields to include/exclude
            
        Returns:
            List of matching documents
        """
        collection = self.db[collection_name]
        return list(collection.find(query, projection))

    
    def update_data(
        self,
        collection_name: str,
        query: Dict[str, Any],
        update_data: Dict[str, Any]
    ) -> int:
        """
        Update data in any collection
        
        Args:
            collection_name: Name of the collection
            query: Query filter
            update_data: Fields to update
            
        Returns:
            Number of modified documents
        """
        collection = self.db[collection_name]
        result = collection.update_many(query, {'$set': update_data})
        return result.modified_count
    
    
    def delete_data(
        self,
        collection_name: str,
        query: Dict[str, Any]
    ) -> int:
        """
        Delete data from any collection
        
        Args:
            collection_name: Name of the collection
            query: Query filter
            
        Returns:
            Number of deleted documents
        """
        collection = self.db[collection_name]
        result = collection.delete_many(query)
        return result.deleted_count 
    

    def get_or_create_user_from_google(
        self,
        email: str, 
        name: str 
    ) -> UserInDB:
        
        existing_user = self.users_collection.find_one({'email': email})
        if existing_user:
            return UserInDB(**existing_user)
        
        new_user = UserInDB(
            username=name.replace(" ", "_"),
            email=email,
            password=b'',
            extra_data={'provided': 'google'}
        )
        print("it has created a document for the google user")
        self.users_collection.insert_one(new_user.model_dump())
        return new_user