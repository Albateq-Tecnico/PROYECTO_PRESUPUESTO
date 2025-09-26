# Contenido corregido para: pages/2_Simulador_de_Mortalidad.py

import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt  # <-- CORRECCIÓN: Importación añadida
from datetime import timedelta
from utils import calcular_curva_mortalidad, style_kpi_df

st.set_page_config(
    page_title="Simulador de Mortalidad",
    page_icon="💀",
    layout="wide",
)

st.title("💀 Simulador de Escenarios de Mortalidad")
st.markdown("""
Esta herramienta te permite modelar cómo diferentes curvas de mortalidad afectan los indicadores clave de tu presupuesto. 
Los parámetros base (aves, peso objetivo, etc.) se toman de los definidos en la página principal.
""")

if 'tabla_base_calculada' not in st.session_state or st.session_state.tabla_base_calculada.empty:
    st.warning("👈 Por favor, ejecuta un cálculo en la página 'Presupuesto Principal' primero para poder simular escenarios.")
    st.stop()

# --- Controles del Escenario ---
st.header("1. Define el Escenario de Mortalidad")
tipo_escenario = st.radio(
    "Selecciona un tipo de curva de mortalidad:",
    ["Lineal (Uniforme)", "Concentrada al Inicio (Semana 1)", "Concentrada al Final (Última Semana)"],
    horizontal=True,
    key="sim_tipo_escenario"
)

porcentaje_escenario = 50
if tipo_escenario != "Lineal (Uniforme)":
    porcentaje_escenario = st.slider(
        f"Porcentaje de la mortalidad total a concentrar (%):", 0, 100, 50, 5, key="sim_porcentaje"
    )

try:
    # Copiar la tabla base desde la sesión para no modificarla
    tabla_simulada = st.session_state.tabla_base_calculada.copy()
    
    dia_obj = tabla_simulada['Dia'].iloc[-1]
    
    total_mortalidad_aves = st.session_state.aves_programadas * (st.session_state.mortalidad_objetivo / 100.0)
    mortalidad_acum_simulada = calcular_curva_mortalidad(dia_obj, total_mortalidad_aves, tipo_escenario, porcentaje_escenario)
    
    if len(mortalidad_acum_simulada) != len(tabla_simulada):
        mortalidad_acum_simulada = np.resize(mortalidad_acum_simulada, len(tabla_simulada))
        mortalidad_acum_simulada[-1] = total_mortalidad_aves 

    tabla_simulada['Mortalidad_Acumulada'] = mortalidad_acum_simulada
    tabla_simulada['Saldo'] = st.session_state.aves_programadas - tabla_simulada['Mortalidad_Acumulada']
    
    if st.session_state.unidades_calculo == "Kilos":
        total_col, daily_col = "Kilos Totales", "Kilos Diarios"
        tabla_simulada[total_col] = (tabla_simulada['Cons_Acum_Ajustado'] * tabla_simulada['Saldo']) / 1000
    else:
        total_col, daily_col = "Bultos Totales", "Bultos Diarios"
        tabla_simulada[total_col] = np.ceil((tabla_simulada['Cons_Acum_Ajustado'] * tabla_simulada['Saldo']) / 40000)
    
    tabla_simulada[daily_col] = tabla_simulada[total_col].diff().fillna(tabla_simulada[total_col])

    # Recalcular KPIs para el escenario
    fases = ['Pre-iniciador', 'Iniciador', 'Engorde', 'Retiro']
    consumo_por_fase = tabla_simulada.groupby('Fase_Alimento')[daily_col].sum()
    unidades = [consumo_por_fase.get(f, 0) for f in fases]
    costos_kg = [st.session_state.val_pre_iniciador, st.session_state.val_iniciador, st.session_state.val_engorde, st.session_state.val_retiro]
    factor_kg = 1 if st.session_state.unidades_calculo == "Kilos" else 40
    costos = [(u * factor_kg) * c for u, c in zip(unidades, costos_kg)]
    costo_total_alimento = sum(costos)

    aves_producidas = tabla_simulada['Saldo'].iloc[-1]
    peso_obj_final = tabla_simulada['Peso_Estimado'].iloc[-1]
    consumo_total_objetivo_ave = tabla_simulada['Cons_Acum_Ajustado'].iloc[-1]
    kilos_totales_producidos = (aves_producidas * peso_obj_final) / 1000 if aves_producidas > 0 else 0
    consumo_total_kg = sum(unidades) * factor_kg

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
        
        st.markdown("---")
        st.subheader("Gráficos del Escenario Simulado")
        col1_graf, col2_graf = st.columns(2)

        with col1_graf:
            fig, ax = plt.subplots()
            ax.plot(tabla_simulada['Dia'], tabla_simulada['Saldo'], color='orange', label='Saldo de Aves')
            ax.set_xlabel("Día del Ciclo")
            ax.set_ylabel("Número de Aves")
            ax.legend(loc='upper left')
            ax.grid(True, linestyle='--', alpha=0.6)
            ax_twin = ax.twinx()
            ax_twin.bar(tabla_simulada['Dia'], tabla_simulada['Mortalidad_Diaria'], color='red', alpha=0.5, label='Mortalidad Diaria')
            ax_twin.set_ylabel("Mortalidad Diaria")
            ax_twin.legend(loc='upper right')
            fig.suptitle("Curva de Saldo y Mortalidad Diaria")
            st.pyplot(fig)

        with col2_graf:
            fig_pie, ax_pie = plt.subplots()
            costo_alimento_kilo = costo_total_alimento / kilos_totales_producidos
            otros_costos_kilo = costo_total_kilo - costo_alimento_kilo
            sizes = [costo_alimento_kilo, otros_costos_kilo]
            labels = [f"Alimento\n${sizes[0]:,.2f}", f"Otros Costos\n${sizes[1]:,.2f}"]
            ax_pie.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=['darkred', 'lightcoral'])
            ax_pie.set_title(f"Costo Total por Kilo: ${costo_total_kilo:,.2f}")
            st.pyplot(fig_pie)
    else:
        st.warning("No se pueden calcular los KPIs porque los kilos producidos o la participación del alimento son cero.")

except Exception as e:
    st.error(f"Ocurrió un error inesperado durante la simulación.")
    st.exception(e)
