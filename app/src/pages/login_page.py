import streamlit as st
from streamlit_oauth import OAuth2Component
import jwt
import os
from datetime import datetime, timedelta
from functools import wraps
import base64
import json

# Static typing
from typing import Optional, Dict, Any
# DB and Session Management
from src.login import auth_manager, db_manager


# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = "http://localhost:8501"  # Change for production



# --- Decorators ---
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
    

    st.subheader("Sign in with Google")

    oauth2 = OAuth2Component(
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        authorize_endpoint="https://accounts.google.com/o/oauth2/v2/auth",
        token_endpoint="https://oauth2.googleapis.com/token",
        refresh_token_endpoint="https://oauth2.googleapis.com/token",
        revoke_token_endpoint="https://oauth2.googleapis.com/revoke"
    )

    redirect_uri = os.environ["GOOGLE_REDIRECT_URI"]
    scope = "openid email profile"

    google_API_result = oauth2.authorize_button(
        name="Continue with Google",
        redirect_uri=redirect_uri,
        scope=scope,
        icon=None,
        use_container_width=True,
        key="google-login",
        pkce="S256",
        extras_params={"prompt": "consent", "access_type": "offline"}
    )



    if google_API_result and 'token' in google_API_result:
        try:
            id_token = jwt.decode(
                google_API_result['token']['id_token'],
                options={"verify_signature": False}
            )
        
            # Get or create user in db
            user = db_manager.get_or_create_user_from_google(id_token)

            # Create session
            st.session_state.user = {
                "email": id_token["email"],
                "name": id_token["name"],
                "picture": id_token["picture"],
                "google_id": id_token["sub"]
            }

            # Create JWT token
            st.session_state.token = auth_manager.create_token(
                google_id=id_token["sub"],
                email=id_token["email"],
            )

            st.rerun()
    
        except Exception as e:
            st.error(f"Login failed: {str(e)}")



def main() -> None:
    """Main application flow"""
    if 'user' not in st.session_state:
        login_page()
    else:
        try:
            if auth_manager.verify_token(st.session_state.token):
                return
            login_page()

        except Exception as e:
            print(f"Error got was {str(e)}")
            login_page()

if __name__ == '__main__':
    main()