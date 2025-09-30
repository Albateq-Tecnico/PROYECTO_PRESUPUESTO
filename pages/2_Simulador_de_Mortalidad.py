# Contenido COMPLETO y CORREGIDO para: pages/2_Simulador_de_Mortalidad.py

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from PIL import Image
from utils import load_data, clean_numeric_column, calcular_peso_estimado, calcular_curva_mortalidad, reconstruir_tabla_base

st.set_page_config(page_title="Análisis de Mortalidad", page_icon="💀", layout="wide")

# --- LOGO EN SIDEBAR ---
BASE_DIR = Path(__file__).resolve().parent.parent 
try:
    logo = Image.open(BASE_DIR / "ARCHIVOS" / "log_PEQ.png")
    st.sidebar.image(logo, width=150)
except Exception:
    st.sidebar.warning("Logo no encontrado.")
st.sidebar.markdown("---")

# --- FUNCIÓN DE CÁLCULO ACTUALIZADA ---
def calcular_escenario_completo(tabla_base, tipo_mortalidad, porcentaje_curva, mortalidad_objetivo_porc, st_session_state):
    tabla_escenario = tabla_base.copy()
    
    # ... (cálculos de Saldo y Consumo) ...
    
    # --- MODIFICACIÓN: Se añaden cálculos de costo por mortalidad ---
    tabla_escenario['Costo_Kg_Dia'] = tabla_escenario['Fase_Alimento'].map(costos_kg_map)
    tabla_escenario['Costo_Alimento_Diario_Ave'] = (tabla_escenario['Cons_Diario_Ave_gr'] / 1000) * tabla_escenario['Costo_Kg_Dia']
    tabla_escenario['Costo_Alimento_Acum_Ave'] = tabla_escenario['Costo_Alimento_Diario_Ave'].cumsum()
    tabla_escenario['Mortalidad_Diaria'] = tabla_escenario['Mortalidad_Acumulada'].diff().fillna(tabla_escenario['Mortalidad_Acumulada'].iloc[0])
    
    costo_alimento_desperdiciado = (tabla_escenario['Mortalidad_Diaria'] * tabla_escenario['Costo_Alimento_Acum_Ave']).sum()
    
    aves_muertas_total = st_session_state.aves_programadas - aves_producidas
    costo_pollitos_perdidos = aves_muertas_total * st_session_state.costo_pollito
    costo_otros_perdidos = aves_muertas_total * st_session_state.otros_costos_ave
    
    resultados_kpi = {}
    if kilos_totales_producidos > 0:
        resultados_kpi = {
            # ... (otros KPIs) ...
            "costo_alimento_mortalidad_total": costo_alimento_desperdiciado,
            "costo_pollito_mortalidad_total": costo_pollitos_perdidos,
            "costo_otros_mortalidad_total": costo_otros_perdidos,
            "costo_alimento_mortalidad_kilo": costo_alimento_desperdiciado / kilos_totales_producidos,
            "costo_pollito_mortalidad_kilo": costo_pollitos_perdidos / kilos_totales_producidos,
            "costo_otros_mortalidad_kilo": costo_otros_perdidos / kilos_totales_producidos,
        }
    return resultados_kpi, tabla_escenario

st.title("📊 Análisis Comparativo de Escenarios de Mortalidad")
# ... (El resto del código hasta el final del try...except) ...
try:
    # ... (reconstrucción de tabla_base_final y cálculo de los 3 escenarios) ...

    st.header("1. Tabla Comparativa de Curvas de Mortalidad")
    if kpis_lineal and kpis_inicio and kpis_final:
        # ... (código para la tabla comparativa principal) ...
        st.dataframe(df_comparative.style.format("${:,.2f}"))

        # --- TABLA DE DESGLOSE DE MORTALIDAD RESTAURADA ---
        st.subheader("Desglose del Costo por Mortalidad")
        
        costo_mortalidad_data = {
            "Componente de Costo": ["Costo Alimento Perdido", "Costo Pollito Perdido", "Otros Costos Perdidos", "**Costo Total por Mortalidad**"],
            "Lineal ($)": [
                kpis_lineal.get("costo_alimento_mortalidad_total", 0), kpis_lineal.get("costo_pollito_mortalidad_total", 0),
                kpis_lineal.get("costo_otros_mortalidad_total", 0), 
                kpis_lineal.get("costo_alimento_mortalidad_total", 0) + kpis_lineal.get("costo_pollito_mortalidad_total", 0) + kpis_lineal.get("costo_otros_mortalidad_total", 0)
            ],
            "Lineal ($/kg)": [
                kpis_lineal.get("costo_alimento_mortalidad_kilo", 0), kpis_lineal.get("costo_pollito_mortalidad_kilo", 0),
                kpis_lineal.get("costo_otros_mortalidad_kilo", 0), 
                kpis_lineal.get("costo_alimento_mortalidad_kilo", 0) + kpis_lineal.get("costo_pollito_mortalidad_kilo", 0) + kpis_lineal.get("costo_otros_mortalidad_kilo", 0)
            ],
            "M. Inicial ($)": [
                kpis_inicio["costo_alimento_mortalidad_total"], kpis_inicio["costo_pollito_mortalidad_total"],
                kpis_inicio["costo_otros_mortalidad_total"], 
                kpis_inicio["costo_alimento_mortalidad_total"] + kpis_inicio["costo_pollito_mortalidad_total"] + kpis_inicio["costo_otros_mortalidad_total"]
            ],
            "M. Inicial ($/kg)": [
                kpis_inicio["costo_alimento_mortalidad_kilo"], kpis_inicio["costo_pollito_mortalidad_kilo"],
                kpis_inicio["costo_otros_mortalidad_kilo"], 
                kpis_inicio["costo_alimento_mortalidad_kilo"] + kpis_inicio["costo_pollito_mortalidad_kilo"] + kpis_inicio["costo_otros_mortalidad_kilo"]
            ],
             "M. Final ($)": [
                kpis_final["costo_alimento_mortalidad_total"], kpis_final["costo_pollito_mortalidad_total"],
                kpis_final["costo_otros_mortalidad_total"], 
                kpis_final["costo_alimento_mortalidad_total"] + kpis_final["costo_pollito_mortalidad_total"] + kpis_final["costo_otros_mortalidad_total"]
            ],
            "M. Final ($/kg)": [
                kpis_final["costo_alimento_mortalidad_kilo"], kpis_final["costo_pollito_mortalidad_kilo"],
                kpis_final["costo_otros_mortalidad_kilo"], 
                kpis_final["costo_alimento_mortalidad_kilo"] + kpis_final["costo_pollito_mortalidad_kilo"] + kpis_final["costo_otros_mortalidad_kilo"]
            ]
        }
        df_mortalidad = pd.DataFrame(costo_mortalidad_data).set_index("Componente de Costo")
        
        st.dataframe(df_mortalidad.style.format("${:,.2f}"))

        # --- GRÁFICOS DE CURVAS DE MORTALIDAD ---
        st.markdown("---")
        # ... (código de los 3 gráficos de curvas) ...

        # --- GRÁFICOS ORGANIZADOS EN UN CONTENEDOR ---
        st.markdown("---")
        st.header("3. Comparación de Estructura de Costos por Kilo")
        with st.container(border=True):
            col_pie1, col_pie2, col_pie3 = st.columns(3)
            # ... (código para los 3 gráficos de pastel, cada uno dentro de su 'with col_pieX:') ...

        # --- ANÁLISIS DE SENSIBILIDAD ---
        st.markdown("---")
        # ... (código para la tabla de sensibilidad) ...

    else:
        st.warning("No se pudieron calcular los KPIs para la comparación.")

except Exception as e:
    st.error("Ocurrió un error inesperado.")
    st.exception(e)
