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
from src.login.schemas import UserCreate, UserResponse
from src.login.models import UserInDB

from src.login import auth_manager, db_manager





# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = "http://localhost:8501"  # Change for production


# --- Helper Functions ---
def create_user_response(user: UserInDB) -> UserResponse:
    """Convert UserInDB to safe UserResponse schema"""
    return UserResponse(
        username=user.username,
        email=user.email,
        created_at=user.created_at,
        updated_at=user.updated_at,
        categories=user.categories if hasattr(user, 'categories') else {"Uncategorised": []}
    )


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
    
    # Tab interface
    login_tab, register_tab = st.tabs(["Login", "Register"])
    
    with login_tab:
        render_login_form()

        # Add Google Login Button
        st.divider()
        st.markdown("Or")
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
        print("authorize_button google_API_result:", json.dumps(google_API_result, sort_keys=True, indent=4), type(google_API_result))

        if google_API_result and "token" in google_API_result:
            decoded_id_token = jwt.decode(google_API_result['token']['id_token'], 
                options={"verify_signature": False})
            google_API_result['id_token'] = decoded_id_token

            st.session_state.decoded_id_token = decoded_id_token
            st.session_state.token = google_API_result["token"]
            st.session_state.user = "google_user"  # You can parse more from google_API_result['id_token'] if needed
            
            st.success("Google login successful!")
            print("authorize_button google_API_result:", json.dumps(google_API_result, sort_keys=True, indent=4), type(google_API_result))
            print("\n\n\n\n")
            print(st.session_state.user)

            google_login_flow()
            print(st.session_state.user_info)

    
    with register_tab:
        render_register_form()


def render_google_login_button() -> None:
    """Renders the Google login button"""
    google_login = st.button("Login with Google")
    
    if google_login:
        google_login_flow()


def google_login_flow() -> None:
    """Handles the Google login process"""

    # If the user is not logged in but the id_token is present from OAuth flow
    if "token" in st.session_state and "user_info" not in st.session_state:
        try:
            # Decode ID token to get user info (already stored during OAuth flow)
            id_token = st.session_state.decoded_id_token

            user_info = {
                "email": id_token["email"],
                "name": id_token.get("name", id_token["email"].split("@")[0]),
            }

            # Save user info to session
            st.session_state.user_info = user_info

            # Persist to database
            print(f"[DEBUG] Creating or getting user: {user_info['email']}")
            user = db_manager.get_or_create_user_from_google(user_info["email"], user_info["name"])
            st.session_state.username = user.username

            # Create JWT
            token = auth_manager.create_token(user.username)
            st.session_state.token = token

            st.success("Login successful!")
              # Now it's safe to rerun since everything is stored
            print(db_manager.display_user_info("Mike_Mike"))

        except Exception as e:
            st.error(f"Login failed: {e}")
            st.stop()

    # If the user is fully logged in
    elif "user_info" in st.session_state:
        user_info = st.session_state.user_info
        st.write(f"Logged in as: {user_info['name']} ({user_info['email']})")

    else:
        st.info("Please log in using Google.")


# --- Page Component ---
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
                    user = db_manager.verify_user(username, password)
                    if user:
                        user_response = create_user_response(user)
                        st.session_state.user  = user_response.model_dump()
                        st.session_state.token = auth_manager.create_token(
                            username = user.username,
                            extra_data={"email": user.email}
                        )
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