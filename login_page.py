import streamlit as st
import jwt
import os
from datetime import datetime, timedelta
from functools import wraps

# Static typing
from typing import Optional, Dict, Any
from models import UserCreate, UserInDB, TokenData


from mongodb_manager import JWTAuthManager, MongoDBManager

auth_manager = JWTAuthManager(os.getenv("JWT_SECRET_KEY"))
db_manager = MongoDBManager(os.getenv("MONGODB_URI"), "Streamlit_app")


def login_required(func):
    """Decorator to ensure user is logged in with valid token"""
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        if 'token' not in st.session_state:
            st.warning("Please login first")
            login_page()
            st.stop()
            
        try:
            token_data: Optional[TokenData] = auth_manager.verify_token(st.session_state.token)
            if not token_data:
                st.error("Invalid or expired session")
                login_page()
                st.stop()
                
            return func(*args, **kwargs)
        except ValueError as e:
            st.error(str(e))
            login_page()
            st.stop()
            
        return wrapper


def login_page() -> None:
    """Main login page with login and registration tabs"""
    st.title("🔒 Secure Authentication")
    
    # Initialize session state
    st.session_state.setdefault('token', None)
    st.session_state.setdefault('user', None)
    
    # Redirect if already logged in
    if st.session_state.token:
        try:
            if auth_manager.verify_token(st.session_state.token):
                st.rerun()
        except ValueError:
            pass
    
    # Tab interface
    login_tab, register_tab = st.tabs(["Login", "Register"])
    
    with login_tab:
        render_login_form()
    
    with register_tab:
        render_register_form()


def render_login_form() -> None:
    """Renders the login form with validation"""
    with st.form("Login Form", clear_on_submit=True):
        st.subheader("Sign In")
        
        username: str = st.text_input("Username", key="login_username")
        password: str = st.text_input("Password", 
            type="password", 
            key="login_password")
        
        if st.form_submit_button("Login"):
            with st.spinner("Authenticating..."):
                try:
                    user: Optional[UserInDB] = db_manager.verify_user(username, password)
                    if user:
                        token: str = auth_manager.create_token(username)
                        st.session_state.token = token
                        st.session_state.user = username
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid credentials")
                except Exception as e:
                    st.error(f"Authentication failed: {str(e)}")


def render_register_form() -> None:
    """Renders the registration form with validation"""
    with st.form("Register Form", clear_on_submit=True):
        st.subheader("Create Account")
        
        username: str = st.text_input("Username", 
            key="reg_username",
            help="3-20 characters, letters and numbers only")
        email: str = st.text_input("Email", 
            key="reg_email",
            help="We'll never share your email")
        password: str = st.text_input("Password", 
            type="password", 
            key="reg_password",
            help="Minimum 8 characters")
        confirm_password: str = st.text_input("Confirm Password", 
            type="password", 
            key="reg_confirm_password")

        if st.form_submit_button("Register"):
            if password != confirm_password:
                st.error("Passwords do not match!")
            elif len(password) < 8:
                st.error("Password must be at least 8 characters")
            else:
                with st.spinner("Creating account..."):
                    try:
                        new_user = UserCreate(
                            username=username,
                            password=password,
                            email=email if email else None
                        )
                        if db_manager.add_user(new_user):
                            st.success("Account created successfully! Please login.")
                        else:
                            st.error("Username already exists")
                    except ValueError as e:
                        st.error(f"Invalid data: {str(e)}")
                    except Exception as e:
                        st.error(f"Registration failed: {str(e)}")


def register_form():
    """Registration form component"""
    with st.form("Register Form"):
        st.subheader("Create New Account")
        
        username = st.text_input("Username", key="reg_username")
        email = st.text_input("Email", key="reg_email")
        password = st.text_input("Password", type="password", key="reg_password")
        confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm_password")
        submitted = st.form_submit_button("Register")
        
        if submitted:
            if password != confirm_password:
                st.error("Passwords don't match!")
            elif len(password) < 6:
                st.error("Password must be at least 6 characters")
            else:
                with st.spinner("Creating account..."):
                    if db_manager.add_user(username, password, email):
                        st.success("Registration successful! Please login.")
                    else:
                        st.error("Username already exists")



def main() -> None:
    """Main application flow"""
    if 'token' not in st.session_state:
        login_page()
    else:
        try:
            if auth_manager.verify_token(st.session_state.token):
                return
            else:
                login_page()
        except ValueError:
            login_page()

if __name__ == '__main__':
    main()