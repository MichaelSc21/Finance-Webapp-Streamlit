import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os





st.set_page_config(page_title="Simple Finance App", page_icon="💰", layout="wide")

login_page = st.Page("src/pages/login_page.py", title="Login Page" )
main_page = st.Page("src/pages/main_page.py", title="Main Dashboard")
waterfall_page = st.Page("src/pages/waterfall.py", title="Waterfall Chart")

print(waterfall_page)


pg = st.navigation([login_page, main_page, waterfall_page])
pg.run()



