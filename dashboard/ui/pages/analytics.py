import streamlit as st
import requests
import os
import pandas as pd
import plotly.express as px

API_URL = os.getenv('API_URL', 'http://localhost:8000')

st.title("Thống Kê Analytics")

try:
    res = requests.get(f"{API_URL}/jobs")
    res.raise_for_status()
    jobs = res.json()
    
    if not jobs:
        st.info("Chưa có dữ liệu thống kê.")
    else:
        df = pd.DataFrame(jobs)
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Tổng số Video", len(df))
        col2.metric("Đã hoàn thành", len(df[df['status'] == 'done']))
        col3.metric("Đã đăng", len(df[df['status'] == 'published']))
        
        st.markdown("---")
        c1, c2 = st.columns(2)
        
        with c1:
            st.subheader("Video theo phong cách")
            style_counts = df['style'].value_counts().reset_index()
            style_counts.columns = ['style', 'count']
            fig_style = px.pie(style_counts, values='count', names='style')
            st.plotly_chart(fig_style, use_container_width=True)
            
        with c2:
            st.subheader("Video theo trạng thái")
            status_counts = df['status'].value_counts().reset_index()
            status_counts.columns = ['status', 'count']
            fig_status = px.bar(status_counts, x='status', y='count')
            st.plotly_chart(fig_status, use_container_width=True)
            
except Exception as e:
    st.error(f"Lỗi tải dữ liệu thống kê: {str(e)}")
