# Contenido COMPLETO y FINAL para: pages/2_Simulador_de_Mortalidad.py

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from utils import load_data, clean_numeric_column, calcular_peso_estimado, calcular_curva_mortalidad

# ... (La función 'calcular_escenario_completo' permanece igual) ...

st.title("📊 Análisis Comparativo de Escenarios de Mortalidad")
# ... (El resto del código de la página permanece igual hasta el cálculo de escenarios) ...

try:
    # ... (Reconstrucción de tabla_base_final como antes) ...

    # --- PASO 2: CALCULAR ESCENARIOS ---
    mortalidad_base = st.session_state.mortalidad_objetivo
    
    # --- CAMBIO: Lee los resultados base en lugar de recalcularlos ---
    kpis_lineal = st.session_state.get('resultados_base') 
    _, tabla_lineal = calcular_escenario_completo(tabla_base_final, "Lineal (Uniforme)", 50, mortalidad_base, st.session_state)
    
    # Solo calcula los dos escenarios variables
    kpis_inicio, tabla_inicio = calcular_escenario_completo(tabla_base_final, "Concentrada al Inicio (Semana 1)", 90, mortalidad_base, st.session_state)
    kpis_final, tabla_final = calcular_escenario_completo(tabla_base_final, "Concentrada al Final (Última Semana)", 90, mortalidad_base, st.session_state)

    st.header("1. Tabla Comparativa de Curvas de Mortalidad")
    if kpis_lineal and kpis_inicio and kpis_final:
        # Ahora la columna "Lineal (Base)" usa la 'única fuente de verdad'
        comparative_data = {
            "Concepto": ["Costo Alimento / Kilo ($)", "Costo Pollito / Kilo ($)", "Otros Costos / Kilo ($)", "**COSTO TOTAL POR KILO ($)**"],
            "Lineal (Base)": [
                kpis_lineal["costo_alimento_kilo"], kpis_lineal["costo_pollito_kilo"],
                kpis_lineal["costo_otros_kilo"], kpis_lineal["costo_total_por_kilo"]
            ],
            "Mortalidad Inicial": [
                kpis_inicio["costo_alimento_kilo"], kpis_inicio["costo_pollito_kilo"],
                kpis_inicio["costo_otros_kilo"], kpis_inicio["costo_total_por_kilo"]
            ],
            "Mortalidad Final": [
                kpis_final["costo_alimento_kilo"], kpis_final["costo_pollito_kilo"],
                kpis_final["costo_otros_kilo"], kpis_final["costo_total_por_kilo"]
            ]
        }
        # ... (El resto del código del simulador permanece igual) ...
    # ...
except Exception as e:
    st.error("Ocurrió un error inesperado.")
    st.exception(e)
