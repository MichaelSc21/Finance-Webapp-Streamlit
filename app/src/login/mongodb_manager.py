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

import json

# For static typing
from src.login.schemas import UserInDB, TokenData
from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, Field, SecretStr

# Import logging
from src.logger import logger

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
                google_id: str,
                email: str, 
                extra_data: Optional[Dict[str, Any]] = None) -> str:
        """Create a JWT token for the user"""
        payload = TokenData(
            sub=google_id,
            email=email,
            exp=datetime.utcnow() + timedelta(days=self.token_expiry_days),
            iat=datetime.utcnow()
        )

        return jwt.encode(payload.model_dump(), self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Optional[TokenData]:
        """Verify a JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return TokenData(**payload)
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError:
            st.error("Invalid token")
            raise ValueError("Invalid token")





class MongoDBManager:
    def __init__(self, connection_string: str, db_name: str) -> None:
        self.client = MongoClient(connection_string)
        self.db = self.client[db_name]
        self.users_collection = self.db['users']
        
    
    def get_or_create_user_from_google(
        self,
        id_token: dict
    ) -> UserInDB:
        

        try:
            google_id = id_token["sub"]
            email = id_token["email"]
            name = id_token["name"]

            user_data = self.users_collection.find_one({"google_id": google_id})

            #TODO: Add funcionality to update the user information in the db regardless of creating a new user or not, so that the db is up-to-date with the latest data of the user's google account
            if not user_data:
                user_data = {
                    "google_id": google_id,
                    "email": email,
                    "name": name,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                    "picture": id_token.get("picture"),
                    "categories": {"Uncategorised": []}
                }
                self.users_collection.insert_one(user_data)
            logger.log("INFO", str(json.dumps(user_data, indent=4, sort_keys=True )))
            return UserInDB(**user_data)
            
        except Exception as e:
            logger.log("ERROR", str(e))        

    # Adding categories to DB
    def get_user_categories(
        self, 
        google_id: str
        ) -> Dict[str, List[str]]:
        """
        Get a user's transaction categories
        
        Args:
            google_id: Google ID of the user to lookup
            
        Returns:
            Dictionary of categories with their keywords
            Defaults to {"Uncategorised": []} if no categories exist
        """
        try:
            user = self.users_collection.find_one({'google_id': google_id})
            if not user:
                logger.warning(f"No user found with google_id: {google_id}")
                return {"Uncategorised": []}
            
            categories = user.get("categories", {"Uncategorised": []})
            return categories
        
        except Exception as e:
            logger.error(f"Error getting categories for {google_id}: {str(e)}")
            return {"Uncategorised": []}


    def save_user_categories(
        self, 
        google_id: str, 
        categories: Dict[str, List[str]]
        ) -> bool:
        """
        Save a user's transaction categories
        
        Args:
            username: Username to save for
            categories: Dictionary of categories with their keywords
            
        Returns:
            True if operation was successful
        """
        try:
            self.users_collection.update_one(
                {'google_id': google_id},
                {'$set': {'categories': categories}},
                upsert=True
            )
            return True
        except PyMongoError as e:
            st.error(f"Error saving categories: {str(e)}")
            logger.log("ERROR", str(e))
            return False

    def add_category_keyword(
        self, 
        google_id: str, 
        category: str, 
        keyword: str
        ) -> bool:
        """
        Add a keyword to a category
        
        Args:
            username: Username to update
            category: Category to add to
            keyword: Keyword to add
            
        Returns:
            True if keyword was added successfully
        """
        keyword = keyword.strip()
        if not keyword:
            return False
            
        try:
            # If the user already has a categories field, it adds the keyword to that corresponding category
            result = self.db['categories'].update_one(
                {'google_id': google_id, f"categories.{category}": {'$exists': True}},
                {'$addToSet': {f"categories.{category}": keyword}}
            )
            
            # If there is no categories field, it creates the categories field and adds the keyword to it
            if result.matched_count == 0:
                # Category doesn't exist, create it
                self.db['categories'].update_one(
                    {'google_id': google_id},
                    {'$set': {f"categories.{category}": [keyword]}},
                    upsert=True
                )
                
            return True
        except PyMongoError as e:
            st.error(f"Error adding keyword: {str(e)}")
            logger.log("ERROR", str(e))
            return False
        

    def display_user_info(self, username: str) -> str:
        """
        Returns a string representation of a user's data for debugging/display purposes.
        
        Args:
            username: The username to look up
            
        Returns:
            A formatted string with user information
        """
        user_data = self.users_collection.find_one({'username': username})
        
        if not user_data:
            return f"No user found with username: {username}"
        
        try:
            # Create a safe copy without sensitive data
            display_data = {
                'username': user_data.get('username'),
                'email': user_data.get('email'),
                'created_at': user_data.get('created_at'),
                'updated_at': user_data.get('updated_at'),
                'categories': user_data.get('categories')  # Check if categories exist
            }
            
            # Format the output string
            output = [f"User: {display_data['username']}"]
            output.append(f"Email: {display_data['email']}")
            output.append(f"Created: {display_data['created_at']}")
            output.append(f"Updated: {display_data['updated_at']}")
            output.append(f"Has categories: {display_data['categories']}")
            
            return "\n".join(output)
            
        except Exception as e:
            logger.log("ERROR", str(e))
            return f"Error formatting user data: {str(e)}"