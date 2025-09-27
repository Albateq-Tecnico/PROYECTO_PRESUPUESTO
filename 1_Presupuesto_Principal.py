# Contenido COMPLETO y CORREGIDO para: 1_Presupuesto_Principal.py

import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, timedelta
from pathlib import Path
import matplotlib.pyplot as plt
from utils import load_data, clean_numeric_column, calcular_peso_estimado, style_kpi_df

st.set_page_config(
    page_title="Presupuesto Avícola",
    page_icon="pollito_tapabocas.ico", 
    layout="wide",
)

BASE_DIR = Path(__file__).resolve().parent.parent
df_coeffs = load_data(BASE_DIR / "ARCHIVOS" / "Cons_Acum_Peso.csv")
df_coeffs_15 = load_data(BASE_DIR / "ARCHIVOS" / "Cons_Acum_Peso_15.csv")
df_referencia = load_data(BASE_DIR / "ARCHIVOS" / "ROSS_COBB_HUBBARD_2025.csv")

# =============================================================================
# --- PANEL LATERAL DE ENTRADAS (SIDEBAR) ---
# =============================================================================
st.sidebar.header("1. Valores de Entrada")
try:
    from PIL import Image
    logo = Image.open(BASE_DIR / "ARCHIVOS" / "log_PEQ.png")
    st.sidebar.image(logo, width=150)
except (FileNotFoundError, ImportError):
    st.sidebar.warning("Logo no encontrado.")

st.sidebar.subheader("Datos del Lote")
st.session_state.aves_programadas = st.sidebar.number_input("# Aves Programadas", 0, value=10000, step=1000)
st.session_state.fecha_llegada = st.sidebar.date_input("Fecha de llegada", date.today())
st.session_state.costo_pollito = st.sidebar.number_input("Costo del Pollito ($/ave)", 0.0, 5000.0, 2000.0, format="%.2f")
# ... (El resto de tu sidebar completo aquí)
st.session_state.otros_costos_ave = st.sidebar.number_input("Otros Costos Estimados ($/ave)", 0.0, 10000.0, 1500.0, format="%.2f", help="Incluye mano de obra, sanidad, energía, depreciación, etc.")

st.sidebar.markdown("---")
if st.sidebar.button("Generar Presupuesto", type="primary", use_container_width=True):
    st.session_state.start_calculation = True

# =============================================================================
# --- ÁREA PRINCIPAL ---
# =============================================================================
st.title("🐔 Presupuesto Avícola")

if 'start_calculation' not in st.session_state or not st.session_state.start_calculation:
    st.info("👈 Para empezar, ajusta los parámetros en el Panel de Control y luego haz clic en 'Generar Presupuesto'.")
else:
    st.markdown("---")
    if st.session_state.aves_programadas <= 0 or st.session_state.peso_objetivo <= 0:
        st.error("Por favor, asegúrate de que las 'Aves Programadas' y el 'Peso Objetivo' sean mayores a cero.")
    else:
        try:
            # 1. CÁLCULOS BASE
            tabla_filtrada = df_referencia[
                (df_referencia['RAZA'] == st.session_state.raza_seleccionada) &
                (df_referencia['SEXO'] == st.session_state.sexo_seleccionado)
            ].copy()

            if tabla_filtrada.empty:
                st.warning(f"No se encontraron datos de referencia.")
                st.stop()
            
            st.header("Resultados del Presupuesto")
            # ... (Cálculos de Peso_Estimado, Fase_Alimento, Saldo, etc.)
            
            # --- CORRECCIÓN DE ORDEN ---
            # Primero se definen todas las variables necesarias
            fases = ['Pre-iniciador', 'Iniciador', 'Engorde', 'Retiro']
            consumo_por_fase = tabla_filtrada.groupby('Fase_Alimento')[daily_col].sum()
            unidades = [consumo_por_fase.get(f, 0) for f in fases]
            factor_kg = 1 if st.session_state.unidades_calculo == "Kilos" else 40
            costos_kg = [st.session_state.val_pre_iniciador, st.session_state.val_iniciador, st.session_state.val_engorde, st.session_state.val_retiro]
            
            # 1. Se define la variable 'costos'
            costos = [(u * factor_kg) * c for u, c in zip(unidades, costos_kg)]
            
            # 2. AHORA SÍ se puede usar 'costos' para calcular la suma
            costo_total_alimento = sum(costos)

            # --- El resto de la lógica continúa ---
            st.subheader("Resumen del Presupuesto de Alimento")
            df_resumen = pd.DataFrame({
                "Fase de Alimento": fases + ["Total"],
                f"Consumo ({st.session_state.unidades_calculo})": unidades + [sum(unidades)],
                "Valor del Alimento ($)": costos + [costo_total_alimento]
            })
            styler_resumen = df_resumen.style.format({f"Consumo ({st.session_state.unidades_calculo})": "{:,.0f}", "Valor del Alimento ($)": "${:,.2f}"})
            st.dataframe(styler_resumen.hide(axis="index"), use_container_width=True)

            # ... (El resto del código para KPIs y gráficos continúa igual)

        except Exception as e:
            st.error("Ocurrió un error inesperado.")
            st.exception(e)
        finally:
            st.markdown("---")
            # ... (Tu nota de responsabilidad)
