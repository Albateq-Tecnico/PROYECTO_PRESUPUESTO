# -*- coding: utf-8 -*-
"""
Created on Mon Sep 22 10:43:19 2025
@author: juan.leyton
"""

import streamlit as st
import pandas as pd
import numpy as np
from PIL import Image
from datetime import date, timedelta
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.offsetbox import OffsetImage, AnnotationBbox

# --- CONFIGURACIÓN DE LA PÁGINA (Debe ser el primer comando de Streamlit) ---
st.set_page_config(
    page_title="Presupuesto Avícola",
    page_icon="🐔",
    layout="wide",
)

# --- DEFINIR RUTA BASE (Buena práctica) ---
BASE_DIR = Path(__file__).resolve().parent

# =============================================================================
# --- FUNCIONES AUXILIARES ---
# =============================================================================

@st.cache_data
def load_data(file_path):
    """Carga datos desde un archivo CSV de forma robusta."""
    try:
        return pd.read_csv(file_path)
    except FileNotFoundError:
        st.error(f"Error Crítico: No se encontró el archivo de datos en: {file_path}")
        return None
    except Exception as e:
        st.error(f"Error Crítico al cargar el archivo {file_path.name}: {e}")
        return None

def clean_numeric_column(series):
    """Convierte una columna a tipo numérico, manejando comas como decimales."""
    if series.dtype == 'object':
        return pd.to_numeric(series.str.replace(',', '.', regex=False), errors='coerce')
    return series

def calcular_peso_estimado(data, coeffs_df, raza, sexo):
    """Calcula el peso estimado usando coeficientes de regresión polinomial."""
    if coeffs_df is None: return pd.Series(0, index=data.index)
    coeffs_seleccion = coeffs_df[(coeffs_df['RAZA'] == raza) & (coeffs_df['SEXO'] == sexo)]
    if not coeffs_seleccion.empty:
        params = coeffs_seleccion.iloc[0]
        x = data['Cons_Acum_Ajustado']
        return (params['Intercept'] + params['Coef_1'] * x + params['Coef_2'] * (x**2) + 
                params['Coef_3'] * (x**3) + params['Coef_4'] * (x**4))
    st.warning(f"No se encontraron coeficientes de peso para {raza} - {sexo}.")
    return pd.Series(0, index=data.index)

def style_kpi_df(df):
    """Aplica formato condicional a un DataFrame de KPIs de forma eficiente."""
    def formatter(val, metric_name):
        if metric_name == "Conversión Alimenticia": return f"{val:,.3f}"
        if "($)" in metric_name: return f"${val:,.2f}"
        return f"{val:,.0f}"
    df_styled = df.copy()
    df_styled['Valor'] = [formatter(val, name) for name, val in df['Valor'].items()]
    return df_styled

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
except FileNotFoundError:
    st.sidebar.warning("Logo no encontrado.")

# --- DATOS DEL LOTE ---
st.sidebar.subheader("Datos del Lote")
st.session_state.fecha_llegada = st.sidebar.date_input("Fecha de llegada", date.today())
st.session_state.aves_programadas = st.sidebar.number_input("# Aves Programadas", 0, value=10000, step=1000, format="%d")

# --- GENÉTICA ---
st.sidebar.subheader("Línea Genética")
razas = sorted(df_referencia['RAZA'].unique()) if df_referencia is not None else ["ROSS 308 AP", "COBB", "HUBBARD", "ROSS"]
sexos = sorted(df_referencia['SEXO'].unique()) if df_referencia is not None else ["MIXTO", "HEMBRA", "MACHO"]
st.session_state.raza_seleccionada = st.sidebar.selectbox("RAZA", razas)
st.session_state.sexo_seleccionado = st.sidebar.selectbox("SEXO", sexos)

# --- OBJETIVOS ---
st.sidebar.subheader("Objetivos del Lote")
st.session_state.peso_objetivo = st.sidebar.number_input("Peso Objetivo (gramos)", 0, value=2500, step=50, format="%d")
st.session_state.mortalidad_objetivo = st.sidebar.number_input("Mortalidad Objetivo %", 0.0, 100.0, 5.0, 0.5, format="%.2f")

# --- CONDICIONES DE GRANJA ---
st.sidebar.subheader("Condiciones de Granja")
st.session_state.tipo_granja = st.sidebar.radio("Tipo de GRANJA", ["TUNEL", "MEJORADA", "NATURAL"], index=2)
productividad_options = {"TUNEL": 100.0, "MEJORADA": 97.5, "NATURAL": 95.0}
st.session_state.productividad = st.sidebar.number_input("Productividad (%)", 0.0, 110.0, productividad_options[st.session_state.tipo_granja], 0.1, format="%.2f", help=f"Productividad teórica: {productividad_options}")

st.session_state.asnm = st.sidebar.radio("Altitud (ASNM)", ["ALTA >2000 msnm", "MEDIA <2000 y >1000 msnm", "BAJA < 1000 msnm"], index=2)

# --- PROGRAMA DE ALIMENTACIÓN ---
st.sidebar.subheader("Programa de Alimentación")
restriccion_map = {"ALTA >2000 msnm": 20, "MEDIA <2000 y >1000 msnm": 10, "BAJA < 1000 msnm": 0}
max_restriccion = restriccion_map[st.session_state.asnm]
st.sidebar.info(f"Recomendación: Máxima restricción del {max_restriccion}%.")
st.session_state.restriccion_programada = st.sidebar.number_input("% Restricción Programado", 0, 100, max_restriccion, 1, format="%d")
if st.session_state.restriccion_programada > max_restriccion:
    st.sidebar.warning(f"Advertencia: La restricción supera el {max_restriccion}% recomendado.")

st.session_state.pre_iniciador = st.sidebar.number_input("Pre-iniciador (gr/ave)", 0, 300, 150, 10, format="%d")
st.session_state.iniciador = st.sidebar.number_input("Iniciador (gr/ave)", 1, 2000, 1200, 10, format="%d")
st.session_state.retiro = st.sidebar.number_input("Retiro (gr/ave)", 0, 2000, 500, 10, format="%d")
st.sidebar.markdown("_El **Engorde** se calcula por diferencia._")

# --- UNIDADES Y COSTOS ---
st.sidebar.subheader("Unidades y Costos")
st.session_state.unidades_calculo = st.sidebar.selectbox("Unidades de Cálculo", ["Kilos", "Bultos x 40 Kilos"])
st.session_state.val_pre_iniciador = st.sidebar.number_input("Costo Pre-iniciador ($/Kg)", 0.0, 2200.0, 0.01, format="%.2f")
st.session_state.val_iniciador = st.sidebar.number_input("Costo Iniciador ($/Kg)", 0.0, 2200.0, 0.01, format="%.2f")
st.session_state.val_engorde = st.sidebar.number_input("Costo Engorde ($/Kg)", 0.0, 2200.0, 0.01, format="%.2f")
st.session_state.val_retiro = st.sidebar.number_input("Costo Retiro ($/Kg)", 0.0, 2200.0, 0.01, format="%.2f")
st.session_state.porcentaje_participacion_alimento = st.sidebar.number_input("Participación Alimento en Costo Total (%)", 0.0, 100.0, 65.0, 0.01, format="%.2f")

# =============================================================================
# --- ÁREA PRINCIPAL ---
# =============================================================================

st.title("🐔 Presupuesto Avícola")
st.markdown("---")

if df_referencia is None:
    st.error("No se pueden mostrar resultados porque el archivo de referencia principal no se cargó.")
    st.stop()

# --- Usar las variables desde st.session_state para consistencia ---
aves_programadas = st.session_state.aves_programadas
peso_objetivo = st.session_state.peso_objetivo

if aves_programadas <= 0 or peso_objetivo <= 0:
    st.info("👈 Ingrese un '# Aves Programadas' y un 'Peso Objetivo' mayores a 0 para ver los resultados.")
    st.stop()

try:
    # 1. FILTRAR DATOS
    tabla_filtrada = df_referencia[
        (df_referencia['RAZA'] == st.session_state.raza_seleccionada) &
        (df_referencia['SEXO'] == st.session_state.sexo_seleccionado)
    ].copy()

    if tabla_filtrada.empty:
        st.warning(f"No se encontraron datos de referencia para {st.session_state.raza_seleccionada} - {st.session_state.sexo_seleccionado}.")
        st.stop()
    
    st.header("Resultados del Presupuesto")
    
    tabla_filtrada['Cons_Acum'] = clean_numeric_column(tabla_filtrada['Cons_Acum'])
    tabla_filtrada['Peso'] = clean_numeric_column(tabla_filtrada['Peso'])

    # 2. CÁLCULOS SECUENCIALES
    factor_ajuste = 1 - (st.session_state.restriccion_programada / 100.0)
    tabla_filtrada['Cons_Acum_Ajustado'] = tabla_filtrada['Cons_Acum'] * factor_ajuste

    dias_1_14 = tabla_filtrada['Dia'] <= 14
    dias_15_adelante = tabla_filtrada['Dia'] >= 15
    tabla_filtrada.loc[dias_1_14, 'Peso_Estimado'] = calcular_peso_estimado(tabla_filtrada[dias_1_14], df_coeffs_15, st.session_state.raza_seleccionada, st.session_state.sexo_seleccionado)
    tabla_filtrada.loc[dias_15_adelante, 'Peso_Estimado'] = calcular_peso_estimado(tabla_filtrada[dias_15_adelante], df_coeffs, st.session_state.raza_seleccionada, st.session_state.sexo_seleccionado)
    tabla_filtrada['Peso_Estimado'] *= (st.session_state.productividad / 100.0)

    closest_idx = (tabla_filtrada['Peso_Estimado'] - peso_objetivo).abs().idxmin()
    dia_obj = tabla_filtrada.loc[closest_idx, 'Dia']
    peso_obj_final = tabla_filtrada.loc[closest_idx, 'Peso_Estimado']
    
    tabla_filtrada = tabla_filtrada.loc[:closest_idx].copy()
    
    # --- CAMBIO CLAVE: Guardar la tabla base para el simulador ---
    st.session_state['tabla_base_calculada'] = tabla_filtrada

    df_interp = tabla_filtrada.drop_duplicates(subset=['Peso_Estimado']).sort_values('Peso_Estimado')
    consumo_total_objetivo_ave = np.interp(peso_objetivo, df_interp['Peso_Estimado'], df_interp['Cons_Acum_Ajustado'])
    
    limite_pre = st.session_state.pre_iniciador
    limite_ini = st.session_state.pre_iniciador + st.session_state.iniciador
    limite_ret = consumo_total_objetivo_ave - st.session_state.retiro if st.session_state.retiro > 0 else np.inf
    conditions = [
        tabla_filtrada['Cons_Acum_Ajustado'] <= limite_pre,
        tabla_filtrada['Cons_Acum_Ajustado'].between(limite_pre, limite_ini, inclusive='right'),
        tabla_filtrada['Cons_Acum_Ajustado'] > limite_ret
    ]
    choices = ['Pre-iniciador', 'Iniciador', 'Retiro']
    tabla_filtrada['Fase_Alimento'] = np.select(conditions, choices, default='Engorde')
    
    total_mortalidad_aves = aves_programadas * (st.session_state.mortalidad_objetivo / 100.0)
    mortalidad_diaria = total_mortalidad_aves / dia_obj if dia_obj > 0 else 0
    tabla_filtrada['Mortalidad_Acumulada'] = (tabla_filtrada['Dia'] * mortalidad_diaria).apply(np.floor)
    tabla_filtrada['Saldo'] = aves_programadas - tabla_filtrada['Mortalidad_Acumulada']

    tabla_filtrada['Fecha'] = tabla_filtrada['Dia'].apply(lambda d: st.session_state.fecha_llegada + timedelta(days=d - 1))
    
    if st.session_state.unidades_calculo == "Kilos":
        total_col, daily_col = "Kilos Totales", "Kilos Diarios"
        tabla_filtrada[total_col] = (tabla_filtrada['Cons_Acum_Ajustado'] * tabla_filtrada['Saldo']) / 1000
    else:
        total_col, daily_col = "Bultos Totales", "Bultos Diarios"
        tabla_filtrada[total_col] = np.ceil((tabla_filtrada['Cons_Acum_Ajustado'] * tabla_filtrada['Saldo']) / 40000)
    
    tabla_filtrada[daily_col] = tabla_filtrada[total_col].diff().fillna(tabla_filtrada[total_col])

    # 3. VISUALIZACIONES
    st.subheader(f"Tabla de Proyección para {aves_programadas} aves ({st.session_state.raza_seleccionada} - {st.session_state.sexo_seleccionado})")
    # ... (El resto del código sigue igual y ya es correcto)

except Exception as e:
    st.error("Ocurrió un error inesperado durante el procesamiento.")
    st.exception(e)

# ... (El bloque finally y la nota de responsabilidad siguen igual)
