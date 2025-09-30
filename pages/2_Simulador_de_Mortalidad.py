# Contenido COMPLETO y FINAL para: pages/2_Simulador_de_Mortalidad.py

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

# --- FUNCIÓN DE CÁLCULO ---
def calcular_escenario_completo(tabla_base, tipo_mortalidad, porcentaje_curva, mortalidad_objetivo_porc, st_session_state):
    tabla_escenario = tabla_base.copy()
    
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
        daily_col_name = "Bultos Diarios"
        tabla_escenario[daily_col_name] = np.ceil((tabla_escenario['Cons_Diario_Ave_gr'] * tabla_escenario['Saldo']) / 40000)

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
    
    consumo_total_kg_escenario = tabla_escenario[daily_col_name].sum() * factor_kg

    resultados_kpi = {}
    if kilos_totales_producidos > 0:
        tabla_escenario['Costo_Kg_Dia'] = tabla_escenario['Fase_Alimento'].map(costos_kg_map)
        tabla_escenario['Costo_Alimento_Diario_Ave'] = (tabla_escenario['Cons_Diario_Ave_gr'] / 1000) * tabla_escenario['Costo_Kg_Dia']
        tabla_escenario['Costo_Alimento_Acum_Ave'] = tabla_escenario['Costo_Alimento_Diario_Ave'].cumsum()
        tabla_escenario['Mortalidad_Diaria'] = tabla_escenario['Mortalidad_Acumulada'].diff().fillna(tabla_escenario['Mortalidad_Acumulada'].iloc[0])
        
        costo_alimento_desperdiciado = (tabla_escenario['Mortalidad_Diaria'] * tabla_escenario['Costo_Alimento_Acum_Ave']).sum()
        
        aves_muertas_total = st_session_state.aves_programadas - aves_producidas
        costo_pollitos_perdidos = aves_muertas_total * st_session_state.costo_pollito
        costo_otros_perdidos = aves_muertas_total * st_session_state.otros_costos_ave

        resultados_kpi = {
            "mortalidad_objetivo": mortalidad_objetivo_porc,
            "kilos_totales_producidos": kilos_totales_producidos,
            "consumo_total_kg": consumo_total_kg_escenario,
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
st.markdown("Esta página analiza el impacto económico de tres curvas de mortalidad distintas y la sensibilidad al porcentaje de mortalidad total.")

if 'resultados_base' not in st.session_state:
    st.warning("👈 Por favor, ejecuta un cálculo en la página '1_Presupuesto_Principal' primero para poder generar este análisis.")
    st.stop()

# --- Cargar datos ---
df_referencia = load_data(BASE_DIR / "ARCHIVOS" / "ROSS_COBB_HUBBARD_2025.csv")
df_coeffs = load_data(BASE_DIR / "ARCHIVOS" / "Cons_Acum_Peso.csv")
df_coeffs_15 = load_data(BASE_DIR / "ARCHIVOS" / "Cons_Acum_Peso_15.csv")

try:
    # --- PASO 1: RECONSTRUIR LA TABLA BASE ---
    tabla_base_final = reconstruir_tabla_base(st.session_state, df_referencia, df_coeffs, df_coeffs_15)

    if tabla_base_final is None:
        st.warning("No se encontraron datos de referencia para la simulación.")
        st.stop()
    
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

    # --- PASO 2: CALCULAR LOS TRES ESCENARIOS PRINCIPALES ---
    mortalidad_base = st.session_state.mortalidad_objetivo
    
    kpis_lineal = st.session_state.get('resultados_base')
    _, tabla_lineal = calcular_escenario_completo(tabla_base_final, "Lineal (Uniforme)", 50, mortalidad_base, st.session_state)
    
    kpis_inicio, tabla_inicio = calcular_escenario_completo(tabla_base_final, "Concentrada al Inicio (Semana 1)", 90, mortalidad_base, st.session_state)
    kpis_final, tabla_final = calcular_escenario_completo(tabla_base_final, "Concentrada al Final (Última Semana)", 90, mortalidad_base, st.session_state)

    st.header("1. Tabla Comparativa de Curvas de Mortalidad")
    if kpis_lineal and kpis_inicio and kpis_final:
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
        df_comparative = pd.DataFrame(comparative_data).set_index("Concepto")
        st.dataframe(df_comparative.style.format("${:,.2f}"))
        
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
        with st.container(border=True):
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
        
        # --- PASO 5: ANÁLISIS DE SENSIBILIDAD A LA MORTALIDAD TOTAL ---
        st.markdown("---")
        st.header("4. Análisis de Sensibilidad al % de Mortalidad Total")
        st.write(f"Análisis basado en el escenario de curva **Lineal**, usando la Mortalidad Objetivo de **{st.session_state.mortalidad_objetivo}%** como punto central.")

        escenarios_mortalidad = [mortalidad_base + i * 0.5 for i in range(-3, 4)]
        
        resultados_sensibilidad = []
        for mort_porc in escenarios_mortalidad:
            if mort_porc >= 0:
                kpis, _ = calcular_escenario_completo(tabla_base_final, "Lineal (Uniforme)", 50, mort_porc, st.session_state)
                if kpis:
                    resultados_sensibilidad.append(kpis)

        if resultados_sensibilidad:
            df_sensibilidad = pd.DataFrame(resultados_sensibilidad)
            df_sensibilidad_display = df_sensibilidad.rename(columns={
                "mortalidad_objetivo": "Mortalidad Objetivo (%)",
                "costo_alimento_kilo": "Costo Alimento / Kilo",
                "costo_pollito_kilo": "Costo Pollito / Kilo",
                "costo_otros_kilo": "Otros Costos / Kilo",
                "costo_total_por_kilo": "Costo Total / Kilo"
            })
            
            columnas_a_mostrar = ["Mortalidad Objetivo (%)", "Costo Alimento / Kilo", "Costo Pollito / Kilo", "Otros Costos / Kilo", "Costo Total / Kilo"]

            st.dataframe(
                df_sensibilidad_display[columnas_a_mostrar].style
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
    else:
        st.warning("No se pudieron calcular los KPIs para la comparación.")

except Exception as e:
    st.error("Ocurrió un error inesperado durante la simulación.")
    st.exception(e)
