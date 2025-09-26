# Contenido COMPLETO y FINAL para: pages/2_Simulador_de_Mortalidad.py

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from utils import load_data, clean_numeric_column, calcular_peso_estimado, calcular_curva_mortalidad

st.set_page_config(page_title="Análisis de Mortalidad", page_icon="💀", layout="wide")

# --- FUNCIÓN DE CÁLCULO REFACTORIZADA ---
def calcular_escenario_completo(tabla_base, tipo_mortalidad, porcentaje_mortalidad, st_session_state):
    """
    Toma una tabla base y parámetros de mortalidad, y devuelve tanto los KPIs como la tabla calculada.
    """
    tabla_escenario = tabla_base.copy()
    
    # Aplicar la curva de mortalidad
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
    
    resultados_kpi = {}
    if kilos_totales_producidos > 0:
        resultados_kpi = {
            "costo_total_pollitos": costo_total_pollitos,
            "costo_total_alimento": costo_total_alimento,
            "costo_total_otros": costo_total_otros,
            "costo_total_lote": costo_total_lote,
            "kilos_totales_producidos": kilos_totales_producidos,
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
    tabla_base = df_referencia[
        (df_referencia['RAZA'] == st.session_state.raza_seleccionada) &
        (df_referencia['SEXO'] == st.session_state.sexo_seleccionado)
    ].copy()

    if tabla_base.empty:
        st.warning("No se encontraron datos de referencia.")
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

    # --- PASO 2: CALCULAR LOS TRES ESCENARIOS ---
    # Usamos un porcentaje alto (90%) para las curvas concentradas para ver un efecto claro
    kpis_lineal, tabla_lineal = calcular_escenario_completo(tabla_base_final, "Lineal (Uniforme)", 50, st.session_state)
    kpis_inicio, tabla_inicio = calcular_escenario_completo(tabla_base_final, "Concentrada al Inicio (Semana 1)", 90, st.session_state)
    kpis_final, tabla_final = calcular_escenario_completo(tabla_base_final, "Concentrada al Final (Última Semana)", 90, st.session_state)

    st.header("1. Tabla Comparativa de Costos")
    if kpis_lineal and kpis_inicio and kpis_final:
        comparative_data = {
            "Concepto": [
                "Costo Alimento / Kilo ($)", "Costo Pollito / Kilo ($)", "Otros Costos / Kilo ($)",
                "**COSTO TOTAL POR KILO ($)**"
            ],
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
        df_comparative = pd.DataFrame(comparative_data).set_index("Concepto")
        st.dataframe(df_comparative.style.format("${:,.2f}"))

        # --- PASO 3: GRÁFICOS DE CURVAS DE MORTALIDAD ---
        st.markdown("---")
        st.header("2. Visualización de Curvas de Mortalidad")
        col1, col2, col3 = st.columns(3)

        def plot_mortality_curve(ax, data, title):
            data['Mortalidad_Diaria'] = data['Mortalidad_Acumulada'].diff().fillna(data['Mortalidad_Acumulada'].iloc[0])
            ax.plot(data['Dia'], data['Saldo'], color='orange', label='Saldo de Aves')
            ax.set_xlabel("Día")
            ax.set_ylabel("Número de Aves", color='orange')
            ax.tick_params(axis='y', labelcolor='orange')
            ax.grid(True, linestyle='--', alpha=0.4)
            ax_twin = ax.twinx()
            ax_twin.bar(data['Dia'], data['Mortalidad_Diaria'], color='red', alpha=0.5, label='Mortalidad Diaria')
            ax_twin.set_ylabel("Mortalidad Diaria", color='red')
            ax_twin.tick_params(axis='y', labelcolor='red')
            ax.set_title(title)

        with col1:
            fig1, ax1 = plt.subplots()
            plot_mortality_curve(ax1, tabla_lineal, "Escenario Lineal")
            st.pyplot(fig1)
        with col2:
            fig2, ax2 = plt.subplots()
            plot_mortality_curve(ax2, tabla_inicio, "Mortalidad Inicial (90% en Sem 1)")
            st.pyplot(fig2)
        with col3:
            fig3, ax3 = plt.subplots()
            plot_mortality_curve(ax3, tabla_final, "Mortalidad Final (90% en últ. Sem)")
            st.pyplot(fig3)

        # --- PASO 4: GRÁFICOS DE PASTEL COMPARATIVOS ---
        st.markdown("---")
        st.header("3. Comparación de Estructura de Costos por Kilo")
        col_pie1, col_pie2, col_pie3 = st.columns(3)

        def plot_pie_chart(ax, kpis, title):
            sizes = [kpis["costo_alimento_kilo"], kpis["costo_pollito_kilo"], kpis["costo_otros_kilo"]]
            labels = [f"Alimento\n${sizes[0]:,.0f}", f"Pollitos\n${sizes[1]:,.0f}", f"Otros\n${sizes[2]:,.0f}"]
            colors = ['darkred', 'lightblue', 'lightcoral']
            ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors)
            ax.set_title(f"{title}\nCosto Total: ${kpis['costo_total_por_kilo']:,.0f}/Kg")

        with col_pie1:
            fig_pie1, ax_pie1 = plt.subplots()
            plot_pie_chart(ax_pie1, kpis_lineal, "Escenario Lineal")
            st.pyplot(fig_pie1)
        with col_pie2:
            fig_pie2, ax_pie2 = plt.subplots()
            plot_pie_chart(ax_pie2, kpis_inicio, "Mortalidad Inicial")
            st.pyplot(fig_pie2)
        with col_pie3:
            fig_pie3, ax_pie3 = plt.subplots()
            plot_pie_chart(ax_pie3, kpis_final, "Mortalidad Final")
            st.pyplot(fig_pie3)
    else:
        st.warning("No se pudieron calcular los KPIs para la comparación.")

except Exception as e:
    st.error("Ocurrió un error inesperado durante la simulación.")
    st.exception(e)
