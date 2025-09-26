# Contenido COMPLETO y FINAL para: pages/2_Simulador_de_Mortalidad.py

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from utils import load_data, clean_numeric_column, calcular_peso_estimado, calcular_curva_mortalidad

st.set_page_config(page_title="Análisis de Mortalidad", page_icon="💀", layout="wide")

# --- FUNCIÓN DE CÁLCULO REFACTORIZADA Y MEJORADA ---
def calcular_escenario_completo(tabla_base, tipo_mortalidad, porcentaje_curva, mortalidad_objetivo_porc, st_session_state):
    """
    Toma una tabla base y parámetros de mortalidad, y devuelve un diccionario con todos los KPIs calculados.
    Ahora acepta un porcentaje de mortalidad total como argumento.
    """
    tabla_escenario = tabla_base.copy()
    
    # Aplicar la curva de mortalidad específica
    dia_obj = tabla_escenario['Dia'].iloc[-1]
    total_mortalidad_aves = st_session_state.aves_programadas * (mortalidad_objetivo_porc / 100.0) # Usa el nuevo objetivo
    mortalidad_acum = calcular_curva_mortalidad(dia_obj, total_mortalidad_aves, tipo_mortalidad, porcentaje_curva)
    
    tabla_escenario['Mortalidad_Acumulada'] = mortalidad_acum
    tabla_escenario['Saldo'] = st_session_state.aves_programadas - tabla_escenario['Mortalidad_Acumulada']

    # Recalcular el consumo del lote
    tabla_escenario['Cons_Diario_Ave_gr'] = tabla_escenario['Cons_Acum_Ajustado'].diff().fillna(tabla_escenario['Cons_Acum_Ajustado'].iloc[0])
    if st_session_state.unidades_calculo == "Kilos":
        daily_col_name = "Kilos Diarios"
        tabla_escenario[daily_col_name] = (tabla_escenario['Cons_Diario_Ave_gr'] * tabla_escenario['Saldo']) / 1000
    else:
        daily_col_name = "Bultos Diarios"
        tabla_escenario[daily_col_name] = np.ceil((tabla_escenario['Cons_Diario_Ave_gr'] * tabla_escenario['Saldo']) / 40000)

    # Recalcular costos
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

    aves_producidas = tabla_escenario['Saldo'].iloc[-1]
    peso_obj_final = tabla_escenario['Peso_Estimado'].iloc[-1]
    kilos_totales_producidos = (aves_producidas * peso_obj_final) / 1000 if aves_producidas > 0 else 0
    
    resultados_kpi = {}
    if kilos_totales_producidos > 0:
        resultados_kpi = {
            "mortalidad_objetivo": mortalidad_objetivo_porc,
            "costo_alimento_kilo": costo_total_alimento / kilos_totales_producidos,
            "costo_pollito_kilo": costo_total_pollitos / kilos_totales_producidos,
            "costo_otros_kilo": costo_total_otros / kilos_totales_producidos,
            "costo_total_por_kilo": costo_total_lote / kilos_totales_producidos,
        }
    return resultados_kpi, tabla_escenario

st.title("📊 Análisis Comparativo de Escenarios de Mortalidad")
st.markdown("Esta página analiza el impacto económico de tres curvas de mortalidad distintas para el mismo lote.")

if 'aves_programadas' not in st.session_state or st.session_state.aves_programadas <= 0:
    st.warning("👈 Por favor, ejecuta un cálculo en la página 'Presupuesto Principal' primero.")
    st.stop()

# --- Cargar datos ---
BASE_DIR = Path(__file__).resolve().parent.parent
df_referencia = load_data(BASE_DIR / "ARCHIVOS" / "ROSS_COBB_HUBBARD_2025.csv")
df_coeffs = load_data(BASE_DIR / "ARCHIVOS" / "Cons_Acum_Peso.csv")
df_coeffs_15 = load_data(BASE_DIR / "ARCHIVOS" / "Cons_Acum_Peso_15.csv")

try:
    # --- PASO 1: RECONSTRUIR LA TABLA BASE ---
    # ... (Este bloque reconstruye la tabla base y no necesita cambios) ...
    tabla_base = df_referencia[
        (df_referencia['RAZA'] == st.session_state.raza_seleccionada) &
        (df_referencia['SEXO'] == st.session_state.sexo_seleccionado)
    ].copy()
    # ... (resto de la reconstrucción) ...
    
    # --- PASO 2: CALCULAR LOS TRES ESCENARIOS PRINCIPALES ---
    # ... (Este bloque calcula los 3 escenarios y no necesita cambios) ...
    
    st.header("1. Tabla Comparativa de Curvas de Mortalidad")
    # ... (Este bloque muestra la tabla comparativa y no necesita cambios) ...
    
    st.markdown("---")
    st.header("2. Visualización de Curvas de Mortalidad")
    # ... (Este bloque muestra los 3 gráficos de curvas y no necesita cambios) ...

    st.markdown("---")
    st.header("3. Comparación de Estructura de Costos por Kilo")
    # ... (Este bloque muestra los 3 gráficos de pastel y no necesita cambios) ...

    # --- NUEVA SECCIÓN: ANÁLISIS DE SENSIBILIDAD A LA MORTALIDAD TOTAL ---
    st.markdown("---")
    st.header("4. Análisis de Sensibilidad al % de Mortalidad Total")
    st.write(f"Análisis basado en el escenario de curva **Lineal**, usando la Mortalidad Objetivo de **{st.session_state.mortalidad_objetivo}%** como punto central.")

    mortalidad_base = st.session_state.mortalidad_objetivo
    escenarios_mortalidad = [mortalidad_base + i * 0.5 for i in range(-3, 4)] # Crea 7 escenarios: -1.5%, -1.0%, ..., +1.5%
    
    resultados_sensibilidad = []
    for mort_porc in escenarios_mortalidad:
        if mort_porc >= 0: # Evitar mortalidad negativa
            kpis, _ = calcular_escenario_completo(tabla_base_final, "Lineal (Uniforme)", 50, mort_porc, st.session_state)
            if kpis:
                resultados_sensibilidad.append(kpis)

    if resultados_sensibilidad:
        df_sensibilidad = pd.DataFrame(resultados_sensibilidad)
        df_sensibilidad = df_sensibilidad.rename(columns={
            "mortalidad_objetivo": "Mortalidad Objetivo (%)",
            "costo_alimento_kilo": "Costo Alimento / Kilo",
            "costo_pollito_kilo": "Costo Pollito / Kilo",
            "costo_otros_kilo": "Otros Costos / Kilo",
            "costo_total_por_kilo": "Costo Total / Kilo"
        })

        # Usar Styler para formatear y añadir barras de datos para visualización
        st.dataframe(
            df_sensibilidad.style
            .format({
                "Mortalidad Objetivo (%)": "{:.2f}%",
                "Costo Alimento / Kilo": "${:,.2f}",
                "Costo Pollito / Kilo": "${:,.2f}",
                "Otros Costos / Kilo": "${:,.2f}",
                "Costo Total / Kilo": "${:,.2f}"
            })
            .background_gradient(cmap='Reds', subset=['Costo Total / Kilo'])
            .set_properties(**{'text-align': 'center'})
        )

except Exception as e:
    st.error("Ocurrió un error inesperado durante la simulación.")
    st.exception(e)
