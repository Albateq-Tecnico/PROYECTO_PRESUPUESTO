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

BASE_DIR = Path(__file__).resolve().parent
df_coeffs = load_data(BASE_DIR / "ARCHIVOS" / "Cons_Acum_Peso.csv")
df_coeffs_15 = load_data(BASE_DIR / "ARCHIVOS" / "Cons_Acum_Peso_15.csv")
df_referencia = load_data(BASE_DIR / "ARCHIVOS" / "ROSS_COBB_HUBBARD_2025.csv")

# =============================================================================
# --- PANEL LATERAL DE ENTRADAS (SIDEBAR) ---
# (El código del sidebar no cambia y se omite por brevedad)
# ...
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
            # ... (Toda la lógica de cálculo de tabla_filtrada hasta el final de la sección 3 permanece igual) ...

            # 4. ANÁLISIS ECONÓMICO
            st.subheader("Resumen del Presupuesto de Alimento")
            # ... (código para la tabla de resumen de alimento) ...
            
            # --- CÁLCULO DE KPIS Y GUARDADO EN SESIÓN ---
            costo_total_alimento = sum(costos)
            costo_total_pollitos = st.session_state.aves_programadas * st.session_state.costo_pollito
            costo_total_otros = st.session_state.aves_programadas * st.session_state.otros_costos_ave
            costo_total_lote = costo_total_alimento + costo_total_pollitos + costo_total_otros

            aves_producidas = tabla_filtrada['Saldo'].iloc[-1]
            peso_obj_final = tabla_filtrada['Peso_Estimado'].iloc[-1]
            kilos_totales_producidos = (aves_producidas * peso_obj_final) / 1000 if aves_producidas > 0 else 0
            consumo_total_kg = tabla_filtrada[daily_col].sum() * factor_kg
            
            if kilos_totales_producidos > 0:
                costo_total_kilo = costo_total_lote / kilos_totales_producidos
                conversion_alimenticia = consumo_total_kg / kilos_totales_producidos
                costo_alimento_kilo = costo_total_alimento / kilos_totales_producidos
                costo_pollito_kilo = costo_total_pollitos / kilos_totales_producidos
                costo_otros_kilo = costo_total_otros / kilos_totales_producidos
                
                # --- CORRECCIÓN: Se añaden las claves que faltaban al diccionario ---
                st.session_state['resultados_base'] = {
                    "kilos_totales_producidos": kilos_totales_producidos,
                    "consumo_total_kg": consumo_total_kg,
                    "costo_total_alimento": costo_total_alimento,
                    "costo_total_pollitos": costo_total_pollitos,
                    "costo_total_otros": costo_total_otros,
                    "costo_total_lote": costo_total_lote,
                    "costo_alimento_kilo": costo_alimento_kilo,
                    "costo_pollito_kilo": costo_pollito_kilo,
                    "costo_otros_kilo": costo_otros_kilo,
                    "costo_total_por_kilo": costo_total_kilo,
                    "conversion_alimenticia": conversion_alimenticia
                }

                # ... (El resto del código para mostrar KPIs y gráficos permanece igual) ...
            else:
                st.warning("No se pueden calcular KPIs: los kilos producidos son cero.")

        except Exception as e:
            st.error("Ocurrió un error inesperado durante el procesamiento.")
            st.exception(e)
    
        finally:
            st.markdown("---")
            st.markdown("""
            <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; border: 1px solid #ccc;">
            <b>Nota de Responsabilidad:</b> Esta es una herramienta de apoyo para uso en granja. La utilización de los resultados es de su exclusiva responsabilidad. No sustituye la asesoría profesional y Albateq S.A. no se hace responsable por las decisiones tomadas con base en la información aquí presentada...
            </div>
            <div style="text-align: center; margin-top: 15px;">
            Desarrollado por la Dirección Técnica de Albateq | dtecnico@albateq.com
            </div>
            """, unsafe_allow_html=True)
