import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os
from src.logger import logger




st.set_page_config(page_title="Simple Finance App", page_icon="💰", layout="wide")

login_page = st.Page("src/pages/login_page.py", title="Login Page" )
main_page = st.Page("src/pages/main_page.py", title="Main Dashboard")
waterfall_page = st.Page("src/pages/waterfall.py", title="Waterfall Chart") 
session_state_page = st.Page("src/pages/show_session_state.py", title="Show Session State")


pg = st.navigation([login_page, main_page, waterfall_page, session_state_page])
pg.run()



