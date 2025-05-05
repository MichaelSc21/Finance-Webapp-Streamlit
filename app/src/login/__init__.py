import streamlit as st
from .mongodb_manager import JWTAuthManager, MongoDBManager
import os

# this is most likely not right as it should be accessible to each individual user instead of everyone (Maybe - look into it)
@st.cache_resource
def get_jwt_auth_manager():
    return JWTAuthManager(os.getenv("JWT_SECRET_KEY"))

@st.cache_resource
def get_mongodb_manager():
    return MongoDBManager(os.getenv("MONGODB_URI"), "Streamlit_app")

auth_manager = get_jwt_auth_manager()
db_manager = get_mongodb_manager()


__all__ = [ 'auth_manager', 'db_manager']


