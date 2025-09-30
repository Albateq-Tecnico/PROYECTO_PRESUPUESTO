import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
from PIL import Image
from datetime import date, timedelta
from utils import load_data, clean_numeric_column, calcular_peso_estimado, calcular_curva_mortalidad, reconstruir_tabla_base, style_kpi_df

# --- CONFIGURACIÓN DE PÁGINA ---
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
    logo = Image.open(BASE_DIR / "ARCHIVOS" / "log_PEQ.png")
    st.sidebar.image(logo, width=150)
except Exception:
    st.sidebar.warning("Logo no encontrado.")

st.sidebar.subheader("Datos del Lote")
st.session_state.aves_programadas = st.sidebar.number_input("# Aves Programadas", 0, value=10000, step=1000)
st.session_state.fecha_llegada = st.sidebar.date_input("Fecha de llegada", date.today())
st.session_state.costo_pollito = st.sidebar.number_input("Costo del Pollito ($/ave)", 0.0, 5000.0, 2000.0, format="%.2f")

st.sidebar.subheader("Línea Genética")
razas = sorted(df_referencia['RAZA'].unique()) if df_referencia is not None else ["ROSS 308 AP", "COBB", "HUBBARD", "ROSS"]
sexos = sorted(df_referencia['SEXO'].unique()) if df_referencia is not None else ["MIXTO", "HEMBRA", "MACHO"]
st.session_state.raza_seleccionada = st.sidebar.selectbox("RAZA", razas)
st.session_state.sexo_seleccionado = st.sidebar.selectbox("SEXO", sexos)

st.sidebar.subheader("Objetivos del Lote")
st.session_state.peso_objetivo = st.sidebar.number_input("Peso Objetivo (gramos)", 0, value=2500, step=50)
st.session_state.mortalidad_objetivo = st.sidebar.number_input("Mortalidad Objetivo %", 0.0, 100.0, 5.0, 0.5, format="%.2f")

st.sidebar.subheader("Condiciones de Granja")
st.session_state.tipo_granja = st.sidebar.radio("Tipo de GRANJA", ["TUNEL", "MEJORADA", "NATURAL"], index=2)
productividad_options = {"TUNEL": 100.0, "MEJORADA": 97.5, "NATURAL": 95.0}
st.session_state.productividad = st.sidebar.number_input("Productividad (%)", 0.0, 110.0, productividad_options[st.session_state.tipo_granja], 0.1, format="%.2f", help=f"Productividad teórica: {productividad_options}")
st.session_state.asnm = st.sidebar.radio("Altitud (ASNM)", ["ALTA >2000 msnm", "MEDIA <2000 y >1000 msnm", "BAJA < 1000 msnm"], index=2)

st.sidebar.subheader("Programa de Alimentación")
restriccion_map = {"ALTA >2000 msnm": 20, "MEDIA <2000 y >1000 msnm": 10, "BAJA < 1000 msnm": 0}
max_restriccion = restriccion_map[st.session_state.asnm]
st.sidebar.info(f"Recomendación: Máxima restricción del {max_restriccion}%.")
st.session_state.restriccion_programada = st.sidebar.number_input("% Restricción Programado", 0, 100, max_restriccion, 1)
if st.session_state.restriccion_programada > max_restriccion:
    st.sidebar.warning(f"Advertencia: La restricción supera el {max_restriccion}% recomendado.")
st.session_state.pre_iniciador = st.sidebar.number_input("Pre-iniciador (gr/ave)", 0, 300, 150, 10)
st.session_state.iniciador = st.sidebar.number_input("Iniciador (gr/ave)", 1, 2000, 1200, 10)
st.session_state.retiro = st.sidebar.number_input("Retiro (gr/ave)", 0, 2000, 500, 10)
st.sidebar.markdown("_El **Engorde** se calcula por diferencia._")

st.sidebar.subheader("Estructura de Costos Directos")
st.session_state.unidades_calculo = st.sidebar.selectbox("Unidades de Cálculo Alimento", ["Kilos", "Bultos x 40 Kilos"])
st.session_state.val_pre_iniciador = st.sidebar.number_input("Costo Pre-iniciador ($/Kg)", 0.0, 5200.0, 2200.0, format="%.2f")
st.session_state.val_iniciador = st.sidebar.number_input("Costo Iniciador ($/Kg)", 0.0, 5200.0, 2200.0, format="%.2f")
st.session_state.val_engorde = st.sidebar.number_input("Costo Engorde ($/Kg)", 0.0, 5200.0, 2200.0, format="%.2f")
st.session_state.val_retiro = st.sidebar.number_input("Costo Retiro ($/Kg)", 0.0, 5200.0, 2200.0, format="%.2f")
st.session_state.otros_costos_ave = st.sidebar.number_input("Otros Costos Estimados ($/ave)", 0.0, 10000.0, 1500.0, format="%.2f", help="Incluye mano de obra, sanidad, energía, depreciación, etc.")

st.sidebar.markdown("---")
if st.sidebar.button("Generar Presupuesto", type="primary", use_container_width=True):
    st.session_state.start_calculation = True

# =============================================================================
# --- ÁREA PRINCIPAL ---
# =============================================================================
col1_header, col2_header = st.columns([1, 4])
with col1_header:
    try:
        logo_main = Image.open(BASE_DIR / "ARCHIVOS" / "log_PEQ.png")
        st.image(logo_main, width=150)
    except Exception:
        pass
with col2_header:
    st.title("ALBATEQ S. A. - Dirección Técnica")
    st.subheader("Simulador de Presupuesto para Pollo de Engorde")

if 'start_calculation' not in st.session_state or not st.session_state.start_calculation:
    st.info("👈 Para empezar, ajusta los parámetros en el Panel de Control y luego haz clic en 'Generar Presupuesto'.")
else:
    st.markdown("---")
    if st.session_state.aves_programadas <= 0 or st.session_state.peso_objetivo <= 0:
        st.error("Por favor, asegúrate de que las 'Aves Programadas' y el 'Peso Objetivo' sean mayores a cero.")
    else:
        try:
            st.header("Resultados del Presupuesto")
            
            tabla_proyeccion = st.session_state.resultados_base.get('tabla_proyeccion')
            if tabla_proyeccion is None or tabla_proyeccion.empty:
                 raise ValueError("La tabla de proyección no se generó. Haz clic en 'Generar Presupuesto' de nuevo.")

            resultados = st.session_state.resultados_base
            
            st.markdown(f"### Tabla de Proyección para {st.session_state.aves_programadas:,.0f} aves ({st.session_state.raza_seleccionada} - {st.session_state.sexo_seleccionado})")
            
            # Mostrar indicadores clave
            st.subheader("Indicadores de Eficiencia Clave")
            kpi_cols = st.columns(3)
            kpi_cols[0].metric("Costo Total por Kilo", f"${resultados['costo_total_por_kilo']:,.2f}")
            kpi_cols[1].metric("Conversión Alimenticia", f"{resultados['conversion_alimenticia']:.3f}")
            kpi_cols[2].metric("Costo por Mortalidad", f"${resultados['costo_total_mortalidad']:,.2f}", help="Costo total de alimento, pollito y otros insumos perdidos debido a la mortalidad.")
            
            # Mostrar la tabla de proyección
            # ... (código para mostrar la tabla de proyección, resumen de fases, KPIs detallados y gráficos)
        
        except Exception as e:
            st.error(f"Ocurrió un error al mostrar los resultados: {e}")
            st.exception(e)

# --- FIN DEL SCRIPT ---
