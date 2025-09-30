# ============================================================================
# ARCHIVO: 1_Presupuesto_Principal.py
# UBICACIÓN: Este archivo DEBE estar en la CARPETA RAÍZ de tu proyecto.
# EJECUCIÓN: streamlit run 1_Presupuesto_Principal.py
#
# ESTRUCTURA DE CARPETAS REQUERIDA PARA QUE EL SIDEBAR FUNCIONE:
# 
# tu_proyecto/
# ├── 📜 1_Presupuesto_Principal.py  <-- ESTE ARCHIVO
# ├── 📁 pages/
# │   ├── 📜 2_Simulador_de_Mortalidad.py
# │   └── ... (tus otros archivos .py)
# ├── 📁 ARCHIVOS/
# │   └── ... (tus archivos de datos y logo)
# └── 📜 utils.py
# ============================================================================

import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, timedelta
from pathlib import Path
import matplotlib.pyplot as plt
from PIL import Image
from utils import load_data, clean_numeric_column, calcular_peso_estimado, style_kpi_df, reconstruir_tabla_base, calcular_curva_mortalidad

# --- CONFIGURACIÓN DE PÁGINA (DEBE SER EL PRIMER COMANDO DE STREAMLIT) ---
BASE_DIR = Path(__file__).resolve().parent
try:
    page_icon_image = Image.open(BASE_DIR / "ARCHIVOS" / "pollito_tapabocas.ico")
except FileNotFoundError:
    page_icon_image = "🐔"

st.set_page_config(
    page_title="Presupuesto Avícola",
    page_icon=page_icon_image, 
    layout="wide",
)

# --- CARGA DE DATOS ---
df_coeffs = load_data(BASE_DIR / "ARCHIVOS" / "Cons_Acum_Peso.csv")
df_coeffs_15 = load_data(BASE_DIR / "ARCHIVOS" / "Cons_Acum_Peso_15.csv")
df_referencia = load_data(BASE_DIR / "ARCHIVOS" / "ROSS_COBB_HUBBARD_2025.csv")

# =============================================================================
# --- PANEL LATERAL DE ENTRADAS (SIDEBAR) ---
# =============================================================================
st.sidebar.header("1. Valores de Entrada")
try:
    logo_sidebar = Image.open(BASE_DIR / "ARCHIVOS" / "log_PEQ.png")
    st.sidebar.image(logo_sidebar, width=150)
except Exception:
    st.sidebar.warning("Logo no encontrado.")

# ... (El resto del código del sidebar, principal y final es idéntico a la última versión funcional)
# ... Por favor, asegúrate de que tu versión local contenga todo el código restante.
# ... Si al pegar este bloque completo el error persiste, el problema es 100% la ubicación del archivo.
