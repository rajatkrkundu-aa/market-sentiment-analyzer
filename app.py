import streamlit as st
from modules.config import AppConfig
from modules.screen_manager import NiftyDashboardScreen


st.set_page_config(page_title="Nifty 50 - 5s Live Analyzer", layout="wide")

config = AppConfig()
screen = NiftyDashboardScreen(config)
screen.render()
