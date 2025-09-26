# Contenido FINAL y Depurado para: pages/2_Simulador_de_Mortalidad.py

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import timedelta
from utils import calcular_curva_mortalidad, style_kpi_df

st.set_page_config(page_title="Simulador de Mortalidad", page_icon="💀", layout="wide")

st.title("💀 Simulador de Escenarios de Mortalidad")
st.markdown("Esta herramienta te permite modelar cómo diferentes curvas de mortalidad afectan los indicadores clave de tu presupuesto.")

if 'tabla_base_calculada' not in st.session_state or st.session_state.tabla_base_calculada.empty:
    st.warning("👈 Por favor, ejecuta un cálculo en la página 'Presupuesto Principal' primero.")
    st.stop()

st.header("1. Define el Escenario de Mortalidad")
tipo_escenario = st.radio(
    "Selecciona un tipo de curva de mortalidad:",
    ["Lineal (Uniforme)", "Concentrada al Inicio (Semana 1)", "Concentrada al Final (Última Semana)"],
    horizontal=True, key="sim_tipo_escenario"
)
porcentaje_escenario = 50
if tipo_escenario != "Lineal (Uniforme)":
    porcentaje_escenario = st.slider(f"Porcentaje de la mortalidad total a concentrar (%):", 0, 100, 50, 5, key="sim_porcentaje")

# --- Punto de Control 1 ---
st.info(f"DEBUG: Escenario seleccionado -> {tipo_escenario} @ {porcentaje_escenario}%")

try:
    tabla_simulada = st.session_state.tabla_base_calculada.copy()
    dia_obj = tabla_simulada['Dia'].iloc[-1]
    
    total_mortalidad_aves = st.session_state.aves_programadas * (st.session_state.mortalidad_objetivo / 100.0)
    mortalidad_acum_simulada = calcular_curva_mortalidad(dia_obj, total_mortalidad_aves, tipo_escenario, porcentaje_escenario)
    
    tabla_simulada['Mortalidad_Acumulada'] = mortalidad_acum_simulada
    tabla_simulada['Saldo'] = st.session_state.aves_programadas - tabla_simulada['Mortalidad_Acumulada']
    
    # --- Punto de Control 2 ---
    st.write("DEBUG: Verificación de la columna 'Saldo' (primeras 10 filas)")
    st.dataframe(tabla_simulada[['Dia', 'Mortalidad_Acumulada', 'Saldo']].head(10))

    if st.session_state.unidades_calculo == "Kilos":
        total_col, daily_col = "Kilos Totales", "Kilos Diarios"
        tabla_simulada[total_col] = (tabla_simulada['Cons_Acum_Ajustado'] * tabla_simulada['Saldo']) / 1000
    else:
        total_col, daily_col = "Bultos Totales", "Bultos Diarios"
        tabla_simulada[total_col] = np.ceil((tabla_simulada['Cons_Acum_Ajustado'] * tabla_simulada['Saldo']) / 40000)
    
    tabla_simulada[daily_col] = tabla_simulada[total_col].diff().fillna(tabla_simulada[total_col])

    consumo_por_fase = tabla_simulada.groupby('Fase_Alimento')[daily_col].sum()
    unidades = [consumo_por_fase.get(f, 0) for f in ['Pre-iniciador', 'Iniciador', 'Engorde', 'Retiro']]
    factor_kg = 1 if st.session_state.unidades_calculo == "Kilos" else 40
    consumo_total_kg = sum(unidades) * factor_kg
    
    costos_kg = [st.session_state.val_pre_iniciador, st.session_state.val_iniciador, st.session_state.val_engorde, st.session_state.val_retiro]
    costos = [(u * factor_kg) * c for u, c in zip(unidades, costos_kg)]
    costo_total_alimento = sum(costos)

    aves_producidas = tabla_simulada['Saldo'].iloc[-1]
    peso_obj_final = tabla_simulada['Peso_Estimado'].iloc[-1]
    kilos_totales_producidos = (aves_producidas * peso_obj_final) / 1000 if aves_producidas > 0 else 0
    
    # --- Punto de Control 3 ---
    st.subheader("--- PUNTOS DE CONTROL (DEBUG) ---")
    debug_cols = st.columns(3)
    debug_cols[0].metric("Total Kilos de Alimento (debe cambiar)", f"{consumo_total_kg:,.2f}")
    debug_cols[1].metric("Kilos de Carne (debe ser constante)", f"{kilos_totales_producidos:,.2f}")
    debug_cols[2].metric("Costo Total Alimento (debe cambiar)", f"${costo_total_alimento:,.2f}")
    st.markdown("---")

    st.header("2. Resultados de la Simulación")
    if kilos_totales_producidos > 0 and st.session_state.porcentaje_participacion_alimento > 0:
        costo_total_lote = costo_total_alimento / (st.session_state.porcentaje_participacion_alimento / 100)
        costo_total_kilo = costo_total_lote / kilos_totales_producidos
        conversion_alimenticia = consumo_total_kg / kilos_totales_producidos
        
        costo_map = {
            'Pre-iniciador': st.session_state.val_pre_iniciador, 'Iniciador': st.session_state.val_iniciador,
            'Engorde': st.session_state.val_engorde, 'Retiro': st.session_state.val_retiro
        }
        tabla_simulada['Costo_Kg_Dia'] = tabla_simulada['Fase_Alimento'].map(costo_map)
        tabla_simulada['Cons_Diario_Ave_gr'] = tabla_simulada['Cons_Acum_Ajustado'].diff().fillna(tabla_simulada['Cons_Acum_Ajustado'].iloc[0])
        tabla_simulada['Costo_Alimento_Diario_Ave'] = (tabla_simulada['Cons_Diario_Ave_gr'] / 1000) * tabla_simulada['Costo_Kg_Dia']
        tabla_simulada['Costo_Alimento_Acum_Ave'] = tabla_simulada['Costo_Alimento_Diario_Ave'].cumsum()
        tabla_simulada['Mortalidad_Diaria'] = tabla_simulada['Mortalidad_Acumulada'].diff().fillna(tabla_simulada['Mortalidad_Acumulada'].iloc[0])
        costo_desperdicio = (tabla_simulada['Mortalidad_Diaria'] * tabla_simulada['Costo_Alimento_Acum_Ave']).sum()

        st.subheader("Indicadores de Eficiencia Clave (Simulado)")
        kpi_cols = st.columns(3)
        kpi_cols[0].metric("Costo Total por Kilo", f"${costo_total_kilo:,.2f}")
        kpi_cols[1].metric("Conversión Alimenticia", f"{conversion_alimenticia:,.3f}")
        kpi_cols[2].metric("Costo por Mortalidad", f"${costo_desperdicio:,.2f}", help="Costo estimado del alimento consumido por las aves que murieron.")
        
    # ... resto de los gráficos ...

except Exception as e:
    st.error("Ocurrió un error inesperado durante la simulación.")
    st.exception(e)
