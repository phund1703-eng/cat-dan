import streamlit as st
import os

st.set_page_config(
    page_title="AutoVideoFactory",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for dark theme/styling
st.markdown("""
<style>
    .reportview-container {
        background: #0e1117;
    }
    .sidebar .sidebar-content {
        background: #262730;
    }
</style>
""", unsafe_allow_html=True)

# Application entry point - simply sets up the config. 
# Streamlit will naturally run the pages in `pages/` directory.

st.title("AutoVideoFactory Dashboard 🎬")
st.write("Vui lòng chọn chức năng từ menu bên trái.")

st.info("Hệ thống đang hoạt động bình thường. 🟢")
