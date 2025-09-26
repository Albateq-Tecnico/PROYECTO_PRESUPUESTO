# Contenido COMPLETO y FINAL para: pages/2_Simulador_de_Mortalidad.py

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import timedelta
from pathlib import Path
from utils import load_data, clean_numeric_column, calcular_peso_estimado, calcular_curva_mortalidad

st.set_page_config(page_title="Simulador de Mortalidad", page_icon="💀", layout="wide")

# --- NUEVA FUNCIÓN DE CÁLCULO PARA REUTILIZAR CÓDIGO ---
def calcular_kpis_escenario(tabla_base, tipo_mortalidad, porcentaje_mortalidad, st_session_state):
    """
    Toma una tabla base y parámetros de mortalidad, y devuelve un diccionario con todos los KPIs calculados.
    """
    tabla_escenario = tabla_base.copy()
    
    # Aplicar la curva de mortalidad específica
    dia_obj = tabla_escenario['Dia'].iloc[-1]
    total_mortalidad_aves = st_session_state.aves_programadas * (st_session_state.mortalidad_objetivo / 100.0)
    mortalidad_acum = calcular_curva_mortalidad(dia_obj, total_mortalidad_aves, tipo_mortalidad, porcentaje_mortalidad)
    
    tabla_escenario['Mortalidad_Acumulada'] = mortalidad_acum
    tabla_escenario['Saldo'] = st_session_state.aves_programadas - tabla_escenario['Mortalidad_Acumulada']

    # Recalcular el consumo del lote con el nuevo saldo
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
    
    # Devolver un diccionario con los resultados
    if kilos_totales_producidos > 0:
        return {
            "costo_total_pollitos": costo_total_pollitos,
            "costo_total_alimento": costo_total_alimento,
            "costo_total_otros": costo_total_otros,
            "costo_total_lote": costo_total_lote,
            "kilos_totales_producidos": kilos_totales_producidos,
            "costo_total_por_kilo": costo_total_lote / kilos_totales_producidos,
        }
    return None

st.title("💀 Simulador de Escenarios de Mortalidad")
st.markdown("""
Esta herramienta te permite modelar cómo diferentes curvas de mortalidad afectan los indicadores clave de tu presupuesto. 
Los parámetros base se toman de los definidos en la página 'Presupuesto Principal'.
""")

if 'aves_programadas' not in st.session_state or st.session_state.aves_programadas <= 0:
    st.warning("👈 Por favor, ejecuta un cálculo en la página 'Presupuesto Principal' primero.")
    st.stop()

# --- Cargar datos ---
BASE_DIR = Path(__file__).resolve().parent.parent
df_referencia = load_data(BASE_DIR / "ARCHIVOS" / "ROSS_COBB_HUBBARD_2025.csv")
df_coeffs = load_data(BASE_DIR / "ARCHIVOS" / "Cons_Acum_Peso.csv")
df_coeffs_15 = load_data(BASE_DIR / "ARCHIVOS" / "Cons_Acum_Peso_15.csv")

st.header("1. Define el Escenario de Mortalidad")
tipo_escenario = st.radio(
    "Selecciona un tipo de curva de mortalidad:",
    ["Lineal (Uniforme)", "Concentrada al Inicio (Semana 1)", "Concentrada al Final (Última Semana)"],
    horizontal=True, key="sim_tipo_escenario"
)
porcentaje_escenario = 50
if tipo_escenario != "Lineal (Uniforme)":
    porcentaje_escenario = st.slider(f"Porcentaje de la mortalidad total a concentrar (%):", 0, 100, 50, 5, key="sim_porcentaje")

try:
    # --- PASO 1: RECONSTRUCCIÓN DE LA TABLA BASE (Una sola vez) ---
    tabla_base = df_referencia[
        (df_referencia['RAZA'] == st.session_state.raza_seleccionada) &
        (df_referencia['SEXO'] == st.session_state.sexo_seleccionado)
    ].copy()

    if tabla_base.empty:
        st.warning("No se encontraron datos de referencia para la simulación.")
        st.stop()

    tabla_base['Cons_Acum'] = clean_numeric_column(tabla_base['Cons_Acum'])
    tabla_base['Peso'] = clean_numeric_column(tabla_base['Peso'])
    factor_ajuste = 1 - (st.session_state.restriccion_programada / 100.0)
    tabla_base['Cons_Acum_Ajustado'] = tabla_base['Cons_Acum'] * factor_ajuste
    
    dias_1_14 = tabla_base['Dia'] <= 14
    dias_15_adelante = tabla_base['Dia'] >= 15
    tabla_base.loc[dias_1_14, 'Peso_Estimado'] = calcular_peso_estimado(tabla_base[dias_1_14], df_coeffs_15, st.session_state.raza_seleccionada, st.session_state.sexo_seleccionado)
    tabla_base.loc[dias_15_adelante, 'Peso_Estimado'] = calcular_peso_estimado(tabla_base[dias_15_adelante], df_coeffs, st.session_state.raza_seleccionada, st.session_state.sexo_seleccionado)
    tabla_base['Peso_Estimado'] *= (st.session_state.productividad / 100.0)

    closest_idx = (tabla_base['Peso_Estimado'] - st.session_state.peso_objetivo).abs().idxmin()
    tabla_base_final = tabla_base.loc[:closest_idx].copy()
    
    df_interp = tabla_base_final.drop_duplicates(subset=['Peso_Estimado']).sort_values('Peso_Estimado')
    consumo_total_objetivo_ave = np.interp(st.session_state.peso_objetivo, df_interp['Peso_Estimado'], df_interp['Cons_Acum_Ajustado'])
    
    limite_pre = st.session_state.pre_iniciador
    limite_ini = st.session_state.pre_iniciador + st.session_state.iniciador
    limite_ret = consumo_total_objetivo_ave - st.session_state.retiro if st.session_state.retiro > 0 else np.inf
    conditions = [
        tabla_base_final['Cons_Acum_Ajustado'] <= limite_pre,
        tabla_base_final['Cons_Acum_Ajustado'].between(limite_pre, limite_ini, inclusive='right'),
        tabla_base_final['Cons_Acum_Ajustado'] > limite_ret
    ]
    choices = ['Pre-iniciador', 'Iniciador', 'Retiro']
    tabla_base_final['Fase_Alimento'] = np.select(conditions, choices, default='Engorde')

    # --- PASO 2: CALCULAR AMBOS ESCENARIOS ---
    resultados_lineal = calcular_kpis_escenario(tabla_base_final, "Lineal (Uniforme)", 50, st.session_state)
    resultados_simulados = calcular_kpis_escenario(tabla_base_final, tipo_escenario, porcentaje_escenario, st.session_state)

    st.header("2. Resultados de la Simulación")
    if resultados_lineal and resultados_simulados:
        
        # --- PASO 3: CREAR Y MOSTRAR LA TABLA COMPARATIVA ---
        st.subheader("Análisis Comparativo de Escenarios")
        
        kilos_producidos = resultados_lineal["kilos_totales_producidos"] # Es el mismo en ambos

        comparative_data = {
            "Concepto": [
                "Costo Total Pollitos ($)", "Costo Total Alimento ($)", "Otros Costos ($)",
                "**COSTO TOTAL DEL LOTE ($)**", "Kilos Totales Producidos (kg)",
                "**COSTO TOTAL POR KILO ($/kg)**"
            ],
            "Escenario Lineal (Base)": [
                resultados_lineal["costo_total_pollitos"],
                resultados_lineal["costo_total_alimento"],
                resultados_lineal["costo_total_otros"],
                resultados_lineal["costo_total_lote"],
                kilos_producidos,
                resultados_lineal["costo_total_por_kilo"]
            ],
            "Escenario Simulado": [
                resultados_simulados["costo_total_pollitos"],
                resultados_simulados["costo_total_alimento"],
                resultados_simulados["costo_total_otros"],
                resultados_simulados["costo_total_lote"],
                kilos_producidos,
                resultados_simulados["costo_total_por_kilo"]
            ]
        }
        df_comparative = pd.DataFrame(comparative_data).set_index("Concepto")
        
        # Calcular la diferencia para mostrarla visualmente
        diferencia = resultados_simulados["costo_total_por_kilo"] - resultados_lineal["costo_total_por_kilo"]

        st.dataframe(
            df_comparative.style.format("${:,.2f}", subset=pd.IndexSlice[["Costo Total Pollitos ($)", "Costo Total Alimento ($)", "Otros Costos ($)", "**COSTO TOTAL DEL LOTE ($)**", "**COSTO TOTAL POR KILO ($/kg)**"], :])
                                .format("{:,.2f} kg", subset=pd.IndexSlice[["Kilos Totales Producidos (kg)"], :])
        )

        st.metric(
            label=f"Diferencia vs. Escenario Lineal",
            value=f"${resultados_simulados['costo_total_por_kilo']:,.2f}",
            delta=f"${diferencia:,.2f} por kilo",
            delta_color="inverse"
        )
        
    else:
        st.warning("No se pueden calcular los KPIs.")

except Exception as e:
    st.error("Ocurrió un error inesperado durante la simulación.")
    st.exception(e)
