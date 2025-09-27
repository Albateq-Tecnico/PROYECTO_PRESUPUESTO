# Contenido COMPLETO y FINAL para: APP_Presupuesto.py

import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, timedelta
from pathlib import Path
import matplotlib.pyplot as plt
from utils import load_data, clean_numeric_column, calcular_peso_estimado, style_kpi_df

st.set_page_config(page_title="Presupuesto Avícola", page_icon="pollito_tapabocas.ico", layout="wide")

BASE_DIR = Path(__file__).resolve().parent
df_coeffs = load_data(BASE_DIR / "ARCHIVOS" / "Cons_Acum_Peso.csv")
df_coeffs_15 = load_data(BASE_DIR / "ARCHIVOS" / "Cons_Acum_Peso_15.csv")
df_referencia = load_data(BASE_DIR / "ARCHIVOS" / "ROSS_COBB_HUBBARD_2025.csv")

# =============================================================================
# --- PANEL LATERAL DE ENTRADAS (SIDEBAR) ---
# =============================================================================
st.sidebar.header("1. Valores de Entrada")
# ... (Todo el código del sidebar permanece igual) ...

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
            # ... (cálculos de tabla_filtrada, Peso_Estimado, Fase_Alimento) ...

            # 2. CÁLCULOS DE MORTALIDAD Y CONSUMO (ESCENARIO BASE: LINEAL)
            # ... (cálculos de Saldo, Kilos Diarios, etc.) ...
            
            # 3. VISUALIZACIONES
            st.subheader(f"Tabla de Proyección...")
            # ... (código para mostrar la tabla de proyección) ...

            # 4. ANÁLISIS ECONÓMICO
            st.subheader("Resumen del Presupuesto de Alimento")
            # ... (código para mostrar el resumen de alimento) ...

            st.subheader("Indicadores Clave de Desempeño (KPIs)")
            
            # --- CÁLCULO Y GUARDADO DE LA 'ÚNICA FUENTE DE VERDAD' ---
            costo_total_alimento = sum(costos)
            costo_total_pollitos = st.session_state.aves_programadas * st.session_state.costo_pollito
            costo_total_otros = st.session_state.aves_programadas * st.session_state.otros_costos_ave
            costo_total_lote = costo_total_alimento + costo_total_pollitos + costo_total_otros
            
            aves_producidas = tabla_filtrada['Saldo'].iloc[-1]
            peso_obj_final = tabla_filtrada['Peso_Estimado'].iloc[-1]
            kilos_totales_producidos = (aves_producidas * peso_obj_final) / 1000
            consumo_total_kg = tabla_filtrada[daily_col].sum() * factor_kg

            if kilos_totales_producidos > 0:
                # Calculamos todos los KPIs del escenario base
                costo_total_kilo = costo_total_lote / kilos_totales_producidos
                conversion_alimenticia = consumo_total_kg / kilos_totales_producidos
                costo_alimento_kilo = costo_total_alimento / kilos_totales_producidos
                costo_pollito_kilo = costo_total_pollitos / kilos_totales_producidos
                costo_otros_kilo = costo_total_otros / kilos_totales_producidos
                
                # ... (cálculo de costo_desperdicio_total) ...

                # Guardamos los resultados clave en un diccionario en la sesión
                st.session_state['resultados_base'] = {
                    "costo_alimento_kilo": costo_alimento_kilo,
                    "costo_pollito_kilo": costo_pollito_kilo,
                    "costo_otros_kilo": costo_otros_kilo,
                    "costo_total_por_kilo": costo_total_kilo,
                    "conversion_alimenticia": conversion_alimenticia
                }

                # La visualización en esta página usa los valores que acabamos de calcular
                st.subheader("Indicadores de Eficiencia Clave")
                # ... (código para los st.metric) ...

                st.markdown("---")
                st.subheader("Análisis de Costos Detallado")
                # ... (código para la tabla de KPIs detallados) ...

                st.markdown("---")
                st.subheader("Gráficos de Resultados")
                # ... (código para los gráficos de crecimiento y pastel) ...
            else:
                st.warning("No se pueden calcular KPIs: los kilos producidos son cero.")

        except Exception as e:
            st.error("Ocurrió un error inesperado.")
            st.exception(e)
        finally:
            st.markdown("---")
            st.markdown("""...""", unsafe_allow_html=True) # Tu nota de responsabilidad
