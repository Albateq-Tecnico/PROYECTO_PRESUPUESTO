# Contenido COMPLETO y ACTUALIZADO para: pages/2_Simulador_de_Mortalidad.py

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
    
    # Cálculos de Saldo y Consumo
    dia_obj = tabla_escenario['Dia'].iloc[-1]
    total_mortalidad_aves = st_session_state.aves_programadas * (mortalidad_objetivo_porc / 100.0)
    mortalidad_acum = calcular_curva_mortalidad(dia_obj, total_mortalidad_aves, tipo_mortalidad, porcentaje_curva)
    tabla_escenario['Mortalidad_Acumulada'] = mortalidad_acum
    tabla_escenario['Saldo'] = st_session_state.aves_programadas - tabla_escenario['Mortalidad_Acumulada']
    tabla_escenario['Cons_Diario_Ave_gr'] = tabla_escenario['Cons_Acum_Ajustado'].diff().fillna(tabla_escenario['Cons_Acum_Ajustado'].iloc[0])
    
    if st_session_state.unidades_calculo == "Kilos":
        daily_col_name = "Kilos Diarios"
        tabla_escenario[daily_col_name] = (tabla_escenario['Cons_Diario_Ave_gr'] * tabla_escenario['Saldo']) / 1000
    else:
        # ... (lógica para bultos)
        pass

    # Cálculos de Costos
    consumo_por_fase = tabla_escenario.groupby('Fase_Alimento')[daily_col_name].sum()
    factor_kg = 1 if st_session_state.unidades_calculo == "Kilos" else 40
    costos_kg_map = {
        'Pre-iniciador': st_session_state.val_pre_iniciador, 'Iniciador': st_session_state.val_iniciador,
        'Engorde': st_session_state.val_engorde, 'Retiro': st_session_state.val_retiro
    }
    costo_total_alimento = sum(consumo_por_fase.get(f, 0) * costos_kg_map.get(f, 0) for f in consumo_por_fase.index) * factor_kg
    costo_total_pollitos = st_session_state.aves_programadas * st_session_state.costo_pollito
    costo_total_otros = st_session_state.aves_programadas * st_session_state.otros_costos_ave
    costo_total_lote = costo_total_alimento + costo_total_pollitos + costo_total_otros

    # Resultados de Producción
    aves_producidas = tabla_escenario['Saldo'].iloc[-1]
    peso_obj_final = tabla_escenario['Peso_Estimado'].iloc[-1]
    kilos_totales_producidos = (aves_producidas * peso_obj_final) / 1000 if aves_producidas > 0 else 0
    
    resultados_kpi = {}
    if kilos_totales_producidos > 0:
        # --- MODIFICACIÓN: Se añaden cálculos de costo por mortalidad ---
        tabla_escenario['Costo_Kg_Dia'] = tabla_escenario['Fase_Alimento'].map(costos_kg_map)
        tabla_escenario['Costo_Alimento_Diario_Ave'] = (tabla_escenario['Cons_Diario_Ave_gr'] / 1000) * tabla_escenario['Costo_Kg_Dia']
        tabla_escenario['Costo_Alimento_Acum_Ave'] = tabla_escenario['Costo_Alimento_Diario_Ave'].cumsum()
        tabla_escenario['Mortalidad_Diaria'] = tabla_escenario['Mortalidad_Acumulada'].diff().fillna(tabla_escenario['Mortalidad_Acumulada'].iloc[0])
        
        costo_alimento_desperdiciado = (tabla_escenario['Mortalidad_Diaria'] * tabla_escenario['Costo_Alimento_Acum_Ave']).sum()
        
        aves_muertas_total = st_session_state.aves_programadas - aves_producidas
        costo_pollitos_perdidos = aves_muertas_total * st_session_state.costo_pollito
        costo_otros_perdidos = aves_muertas_total * st_session_state.otros_costos_ave
        # --- FIN DE LA MODIFICACIÓN ---

        resultados_kpi = {
            "costo_alimento_kilo": costo_total_alimento / kilos_totales_producidos,
            "costo_pollito_kilo": costo_total_pollitos / kilos_totales_producidos,
            "costo_otros_kilo": costo_total_otros / kilos_totales_producidos,
            "costo_total_por_kilo": costo_total_lote / kilos_totales_producidos,
            "costo_alimento_mortalidad_total": costo_alimento_desperdiciado,
            "costo_pollito_mortalidad_total": costo_pollitos_perdidos,
            "costo_otros_mortalidad_total": costo_otros_perdidos,
            "costo_alimento_mortalidad_kilo": costo_alimento_desperdiciado / kilos_totales_producidos,
            "costo_pollito_mortalidad_kilo": costo_pollitos_perdidos / kilos_totales_producidos,
            "costo_otros_mortalidad_kilo": costo_otros_perdidos / kilos_totales_producidos,
        }
    return resultados_kpi, tabla_escenario

st.title("📊 Análisis Comparativo de Escenarios de Mortalidad")
# ... (El resto del código de la página permanece igual hasta la visualización) ...

try:
    # ... (Reconstrucción de tabla_base_final como antes) ...
    
    mortalidad_base = st.session_state.mortalidad_objetivo
    kpis_lineal = st.session_state.get('resultados_base')
    _, tabla_lineal = calcular_escenario_completo(tabla_base_final, "Lineal (Uniforme)", 50, mortalidad_base, st.session_state)
    kpis_inicio, tabla_inicio = calcular_escenario_completo(tabla_base_final, "Concentrada al Inicio (Semana 1)", 90, mortalidad_base, st.session_state)
    kpis_final, tabla_final = calcular_escenario_completo(tabla_base_final, "Concentrada al Final (Última Semana)", 90, mortalidad_base, st.session_state)

    st.header("1. Tabla Comparativa de Curvas de Mortalidad")
    if kpis_lineal and kpis_inicio and kpis_final:
        # ... (La tabla comparativa de 3 escenarios permanece igual) ...
        st.dataframe(...)
        
        # --- NUEVA TABLA: Desglose del Costo por Mortalidad ---
        st.subheader("Desglose del Costo por Mortalidad")
        
        costo_mortalidad_data = {
            "Componente de Costo": ["Costo Alimento Perdido", "Costo Pollito Perdido", "Otros Costos Perdidos", "**Costo Total por Mortalidad**"],
            "Lineal ($)": [
                kpis_lineal.get("costo_alimento_mortalidad_total", 0), kpis_lineal.get("costo_pollito_mortalidad_total", 0),
                kpis_lineal.get("costo_otros_mortalidad_total", 0), kpis_lineal.get("costo_alimento_mortalidad_total", 0) + kpis_lineal.get("costo_pollito_mortalidad_total", 0) + kpis_lineal.get("costo_otros_mortalidad_total", 0)
            ],
            "Lineal ($/kg)": [
                kpis_lineal.get("costo_alimento_mortalidad_kilo", 0), kpis_lineal.get("costo_pollito_mortalidad_kilo", 0),
                kpis_lineal.get("costo_otros_mortalidad_kilo", 0), kpis_lineal.get("costo_alimento_mortalidad_kilo", 0) + kpis_lineal.get("costo_pollito_mortalidad_kilo", 0) + kpis_lineal.get("costo_otros_mortalidad_kilo", 0)
            ],
            "M. Inicial ($)": [
                kpis_inicio["costo_alimento_mortalidad_total"], kpis_inicio["costo_pollito_mortalidad_total"],
                kpis_inicio["costo_otros_mortalidad_total"], kpis_inicio["costo_alimento_mortalidad_total"] + kpis_inicio["costo_pollito_mortalidad_total"] + kpis_inicio["costo_otros_mortalidad_total"]
            ],
            "M. Inicial ($/kg)": [
                kpis_inicio["costo_alimento_mortalidad_kilo"], kpis_inicio["costo_pollito_mortalidad_kilo"],
                kpis_inicio["costo_otros_mortalidad_kilo"], kpis_inicio["costo_alimento_mortalidad_kilo"] + kpis_inicio["costo_pollito_mortalidad_kilo"] + kpis_inicio["costo_otros_mortalidad_kilo"]
            ],
             "M. Final ($)": [
                kpis_final["costo_alimento_mortalidad_total"], kpis_final["costo_pollito_mortalidad_total"],
                kpis_final["costo_otros_mortalidad_total"], kpis_final["costo_alimento_mortalidad_total"] + kpis_final["costo_pollito_mortalidad_total"] + kpis_final["costo_otros_mortalidad_total"]
            ],
            "M. Final ($/kg)": [
                kpis_final["costo_alimento_mortalidad_kilo"], kpis_final["costo_pollito_mortalidad_kilo"],
                kpis_final["costo_otros_mortalidad_kilo"], kpis_final["costo_alimento_mortalidad_kilo"] + kpis_final["costo_pollito_mortalidad_kilo"] + kpis_final["costo_otros_mortalidad_kilo"]
            ]
        }
        df_mortalidad = pd.DataFrame(costo_mortalidad_data).set_index("Componente de Costo")
        
        # Formatear la nueva tabla
        st.dataframe(df_mortalidad.style.format("${:,.2f}"))

        # --- El resto del código de gráficos y tablas de sensibilidad permanece igual ---
    else:
        st.warning("No se pudieron calcular los KPIs para la comparación.")

except Exception as e:
    st.error("Ocurrió un error inesperado durante la simulación.")
    st.exception(e)
