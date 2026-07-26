import streamlit as st
from modules.app_menu import AppMenu
from modules.config import AppConfig
from modules.oi_screen import NiftyOiScreen
from modules.screen_manager import NiftyDashboardScreen


st.set_page_config(page_title="Nifty 50 - 5s Live Analyzer", layout="wide")

config = AppConfig()
menu = AppMenu()

selected_menu_key = menu.render()

if selected_menu_key == "oi":
	screen = NiftyOiScreen(config)
else:
	screen = NiftyDashboardScreen(config)

screen.render()
