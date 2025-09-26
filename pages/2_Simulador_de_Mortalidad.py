# Contenido FINAL y DEFINITIVO para: pages/2_Simulador_de_Mortalidad.py

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import timedelta
from pathlib import Path
from utils import load_data, clean_numeric_column, calcular_peso_estimado, calcular_curva_mortalidad, style_kpi_df

st.set_page_config(page_title="Simulador de Mortalidad", page_icon="💀", layout="wide")

st.title("💀 Simulador de Escenarios de Mortalidad")

# --- Verificar si los parámetros base existen ---
if 'aves_programadas' not in st.session_state:
    st.warning("👈 Por favor, configura y ejecuta un cálculo en la página 'Presupuesto Principal' primero.")
    st.stop()

# --- Cargar datos (necesario porque reconstruimos la tabla) ---
BASE_DIR = Path(__file__).resolve().parent.parent
df_referencia = load_data(BASE_DIR / "ARCHIVOS" / "ROSS_COBB_HUBBARD_2025.csv")
df_coeffs = load_data(BASE_DIR / "ARCHIVOS" / "Cons_Acum_Peso.csv")
df_coeffs_15 = load_data(BASE_DIR / "ARCHIVOS" / "Cons_Acum_Peso_15.csv")

st.header("1. Define el Escenario de Mortalidad")
tipo_escenario = st.radio(...)
porcentaje_escenario = st.slider(...) if tipo_escenario != "Lineal (Uniforme)" else 50

try:
    # --- RECONSTRUCCIÓN COMPLETA DE LA TABLA BASE ---
    tabla_base = df_referencia[
        (df_referencia['RAZA'] == st.session_state.raza_seleccionada) &
        (df_referencia['SEXO'] == st.session_state.sexo_seleccionado)
    ].copy()

    if tabla_base.empty:
        st.warning("No se encontraron datos de referencia para la simulación.")
        st.stop()

    tabla_base['Cons_Acum'] = clean_numeric_column(tabla_base['Cons_Acum'])
    tabla_base['Peso'] = clean_numeric_column(tabla_base['Peso'])
    factor_ajuste = 1 - (st.session_state.restriccion_programada / 100.0)
    tabla_base['Cons_Acum_Ajustado'] = tabla_base['Cons_Acum'] * factor_ajuste

    dias_1_14 = tabla_base['Dia'] <= 14
    dias_15_adelante = tabla_base['Dia'] >= 15
    tabla_base.loc[dias_1_14, 'Peso_Estimado'] = calcular_peso_estimado(tabla_base[dias_1_14], df_coeffs_15, st.session_state.raza_seleccionada, st.session_state.sexo_seleccionado)
    tabla_base.loc[dias_15_adelante, 'Peso_Estimado'] = calcular_peso_estimado(tabla_base[dias_15_adelante], df_coeffs, st.session_state.raza_seleccionada, st.session_state.sexo_seleccionado)
    tabla_base['Peso_Estimado'] *= (st.session_state.productividad / 100.0)

    closest_idx = (tabla_base['Peso_Estimado'] - st.session_state.peso_objetivo).abs().idxmin()
    tabla_simulada = tabla_base.loc[:closest_idx].copy()
    
    # --- A partir de aquí, la lógica es la misma que ya teníamos ---
    dia_obj = tabla_simulada['Dia'].iloc[-1]
    
    # Asignar fase de alimento
    consumo_total_objetivo_ave = np.interp(...)
    # ... (código para asignar Fase_Alimento) ...
    tabla_simulada['Fase_Alimento'] = np.select(...)

    # --- SIMULACIÓN DE MORTALIDAD ---
    total_mortalidad_aves = st.session_state.aves_programadas * (st.session_state.mortalidad_objetivo / 100.0)
    mortalidad_acum_simulada = calcular_curva_mortalidad(dia_obj, total_mortalidad_aves, tipo_escenario, porcentaje_escenario)
    tabla_simulada['Mortalidad_Acumulada'] = mortalidad_acum_simulada
    tabla_simulada['Saldo'] = st.session_state.aves_programadas - tabla_simulada['Mortalidad_Acumulada']

    # --- RECALCULO DE CONSUMO Y KPIS (como en la última versión) ---
    # ... (todo el bloque final de cálculo de Kilos Diarios, costos, KPIs y gráficos) ...

except Exception as e:
    st.error(f"Ocurrió un error en la simulación: {e}")
    st.exception(e)
