import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import io

# Importaciones para generacion de PDF con formato de informe tecnico oficial
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# --- CONFIGURACION DE PAGINA ---
st.set_page_config(
    page_title="Informe Tecnico // Calculo y Verificacion Electrica",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo CSS Empresarial / Tecnico Profesional
st.markdown("""
<style>
    .stApp {
        background-color: #FFFFFF;
        color: #0F172A;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    section[data-testid="stSidebar"] {
        background-color: #F8FAFC;
        border-right: 1px solid #E2E8F0;
    }
    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #CBD5E1;
        border-top: 3px solid #1E293B;
        padding: 12px 16px;
        border-radius: 2px;
    }
    div[data-testid="stMetricLabel"] {
        color: #475569;
        font-family: 'Inter', sans-serif;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    div[data-testid="stMetricValue"] {
        color: #0F172A;
        font-family: 'Courier New', monospace;
        font-size: 1.25rem;
        font-weight: 700;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 0px;
        background-color: #F1F5F9;
        border-bottom: 2px solid #CBD5E1;
        border-radius: 4px 4px 0 0;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #F1F5F9;
        border: none;
        color: #475569;
        padding: 10px 24px;
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .stTabs [aria-selected="true"] {
        background-color: #FFFFFF;
        color: #0F172A;
        border-top: 3px solid #1E293B;
    }
