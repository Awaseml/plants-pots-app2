import streamlit as st
import psycopg2
from fpdf import FPDF

def get_conn():
    return psycopg2.connect(
        st.secrets["DATABASE_URL"]
    )

conn = get_conn()

st.title("Plants Pots App")

st.success("Database connected successfully!")
