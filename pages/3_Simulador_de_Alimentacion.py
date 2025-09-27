# Contenido COMPLETO y FINAL para: pages/3_Simulador_de_Alimentacion.py

import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
from utils import load_data, reconstruir_tabla_base

st.set_page_config(page_title="Simulador de Alimentación", page_icon="🌽", layout="wide")

st.title("🌽 Simulador de Estrategias de Alimentación")

if 'aves_programadas' not in st.session_state or st.session_state.aves_programadas <= 0:
    st.warning("👈 Por favor, ejecuta un cálculo en la página 'Presupuesto Principal' primero.")
    st.stop()

# --- Cargar datos ---
BASE_DIR = Path(__file__).resolve().parent.parent
df_referencia = load_data(BASE_DIR / "ARCHIVOS" / "ROSS_COBB_HUBBARD_2025.csv")
df_coeffs = load_data(BASE_DIR / "ARCHIVOS" / "Cons_Acum_Peso.csv")
df_coeffs_15 = load_data(BASE_DIR / "ARCHIVOS" / "Cons_Acum_Peso_15.csv")

# --- RECONSTRUIR TABLA BASE (USANDO LA FUNCIÓN DE UTILS) ---
tabla_base_completa = reconstruir_tabla_base(st.session_state, df_referencia, df_coeffs, df_coeffs_15)

if tabla_base_completa is None:
    st.error("No se pudieron generar los datos base para la simulación.")
    st.stop()

# =============================================================================
# --- 1. SIMULADOR DE PLAN DE ALIMENTACIÓN ---
# =============================================================================
st.header("1. Simulador de Plan de Alimentación")
st.write("""
Aquí puedes ajustar las cantidades de las fases de alimento para encontrar la combinación más económica 
que te permita alcanzar tu peso objetivo. El modelo asume que el rendimiento biológico (peso y conversión) no cambia.
""")

c1, c2, c3 = st.columns(3)
with c1:
    pre_iniciador_sim = st.slider("Gramos Pre-iniciador/ave", 0, 500, st.session_state.pre_iniciador, key="slider_pre")
with c2:
    iniciador_sim = st.slider("Gramos Iniciador/ave", 500, 2000, st.session_state.iniciador, key="slider_ini")
with c3:
    retiro_sim = st.slider("Gramos Retiro/ave", 0, 1000, st.session_state.retiro, key="slider_ret")

try:
    # --- Cálculos para el Plan de Alimentación Simulado ---
    tabla_sim_alimento = tabla_base_completa.copy()
    closest_idx = (tabla_sim_alimento['Peso_Estimado'] - st.session_state.peso_objetivo).abs().idxmin()
    tabla_sim_alimento = tabla_sim_alimento.loc[:closest_idx].copy()

    df_interp = tabla_sim_alimento.drop_duplicates(subset=['Peso_Estimado']).sort_values('Peso_Estimado')
    consumo_total_objetivo_ave = np.interp(st.session_state.peso_objetivo, df_interp['Peso_Estimado'], df_interp['Cons_Acum_Ajustado'])
    
    limite_pre = pre_iniciador_sim
    limite_ini = pre_iniciador_sim + iniciador_sim
    limite_ret = consumo_total_objetivo_ave - retiro_sim if retiro_sim > 0 else np.inf
    conditions = [
        tabla_sim_alimento['Cons_Acum_Ajustado'] <= limite_pre,
        tabla_sim_alimento['Cons_Acum_Ajustado'].between(limite_pre, limite_ini, inclusive='right'),
        tabla_sim_alimento['Cons_Acum_Ajustado'] > limite_ret
    ]
    choices = ['Pre-iniciador', 'Iniciador', 'Retiro']
    tabla_sim_alimento['Fase_Alimento'] = np.select(conditions, choices, default='Engorde')

    mortalidad_diaria_prom = (st.session_state.aves_programadas * (st.session_state.mortalidad_objetivo / 100)) / len(tabla_sim_alimento)
    tabla_sim_alimento['Saldo'] = st.session_state.aves_programadas - (tabla_sim_alimento['Dia'] * mortalidad_diaria_prom).apply(np.floor)
    tabla_sim_alimento['Cons_Diario_Ave_gr'] = tabla_sim_alimento['Cons_Acum_Ajustado'].diff().fillna(tabla_sim_alimento['Cons_Acum_Ajustado'].iloc[0])
    tabla_sim_alimento['Kilos_Diarios_Lote'] = (tabla_sim_alimento['Cons_Diario_Ave_gr'] * tabla_sim_alimento['Saldo']) / 1000
    
    costos_kg_map = {
        'Pre-iniciador': st.session_state.val_pre_iniciador, 'Iniciador': st.session_state.val_iniciador,
        'Engorde': st.session_state.val_engorde, 'Retiro': st.session_state.val_retiro
    }
    consumo_por_fase = tabla_sim_alimento.groupby('Fase_Alimento')['Kilos_Diarios_Lote'].sum()
    costo_total_alimento_sim = sum(consumo_por_fase.get(f, 0) * costos_kg_map.get(f, 0) for f in consumo_por_fase.index)

    kilos_producidos = (tabla_sim_alimento['Saldo'].iloc[-1] * tabla_sim_alimento['Peso_Estimado'].iloc[-1]) / 1000
    costo_alimento_kilo_sim = costo_total_alimento_sim / kilos_producidos if kilos_producidos > 0 else 0
    
    st.markdown("##### Resultados del Plan Simulado")
    res1, res2 = st.columns(2)
    res1.metric("Costo Total del Alimento", f"${costo_total_alimento_sim:,.0f}")
    res2.metric("Costo del Alimento por Kilo Producido", f"${costo_alimento_kilo_sim:,.2f}")

except Exception as e:
    st.error(f"Error en el simulador de alimentación: {e}")

# =============================================================================
# --- 2. ANÁLISIS DE SENSIBILIDAD AL PESO OBJETIVO ---
# =============================================================================
st.markdown("---")
st.header("2. Análisis de Sensibilidad al Peso Objetivo")
st.write("""
Esta tabla y gráfico muestran cómo cambian los indicadores y la estructura de costos si decides llevar tus aves a un peso de venta diferente.
""")

try:
    resultados_sensibilidad = []
    peso_base = st.session_state.peso_objetivo
    paso = 100
    pesos_a_evaluar = [peso_base + i * paso for i in range(-3, 4)]

    costos_kg_map = {
        'Pre-iniciador': st.session_state.val_pre_iniciador, 'Iniciador': st.session_state.val_iniciador,
        'Engorde': st.session_state.val_engorde, 'Retiro': st.session_state.val_retiro
    }

    tabla_base_limpia = tabla_base_completa.dropna(subset=['Peso_Estimado']).copy()
    max_peso_posible = tabla_base_limpia['Peso_Estimado'].max()

    for peso_obj_sens in pesos_a_evaluar:
        if peso_obj_sens <= 0: continue
        
        tabla_sens = tabla_base_limpia.copy()
        
        if peso_obj_sens > max_peso_posible:
            tabla_truncada = tabla_sens.copy()
        else:
            idx = (tabla_sens['Peso_Estimado'] - peso_obj_sens).abs().idxmin()
            tabla_truncada = tabla_sens.loc[:idx].copy()
        
        df_interp_sens = tabla_truncada.drop_duplicates(subset=['Peso_Estimado']).sort_values('Peso_Estimado')
        consumo_total_sens = np.interp(peso_obj_sens, df_interp_sens['Peso_Estimado'], df_interp_sens['Cons_Acum_Ajustado'])
        
        limite_pre_sens = st.session_state.pre_iniciador
        limite_ini_sens = st.session_state.pre_iniciador + st.session_state.iniciador
        limite_ret_sens = consumo_total_sens - st.session_state.retiro if st.session_state.retiro > 0 else np.inf
        
        conditions_sens = [
            tabla_truncada['Cons_Acum_Ajustado'] <= limite_pre_sens,
            tabla_truncada['Cons_Acum_Ajustado'].between(limite_pre_sens, limite_ini_sens, inclusive='right'),
            tabla_truncada['Cons_Acum_Ajustado'] > limite_ret_sens
        ]
        choices_sens = ['Pre-iniciador', 'Iniciador', 'Retiro']
        tabla_truncada['Fase_Alimento'] = np.select(conditions_sens, choices_sens, default='Engorde')

        dias_ciclo = tabla_truncada['Dia'].iloc[-1]
        
        mortalidad_total_aves = st.session_state.aves_programadas * (st.session_state.mortalidad_objetivo / 100)
        mortalidad_diaria_prom = mortalidad_total_aves / dias_ciclo if dias_ciclo > 0 else 0
        tabla_truncada['Saldo'] = st.session_state.aves_programadas - (tabla_truncada['Dia'] * mortalidad_diaria_prom).apply(np.floor)
        
        tabla_truncada['Cons_Diario_Ave_gr'] = tabla_truncada['Cons_Acum_Ajustado'].diff().fillna(tabla_truncada['Cons_Acum_Ajustado'].iloc[0])
        tabla_truncada['Kilos_Diarios_Lote'] = (tabla_truncada['Cons_Diario_Ave_gr'] * tabla_truncada['Saldo']) / 1000
        consumo_total_kg = tabla_truncada['Kilos_Diarios_Lote'].sum()
        
        aves_producidas = tabla_truncada['Saldo'].iloc[-1]
        peso_final_real = tabla_truncada['Peso_Estimado'].iloc[-1]
        kilos_producidos_sens = (aves_producidas * peso_final_real) / 1000
        
        if kilos_producidos_sens > 0:
            consumo_por_fase_sens = tabla_truncada.groupby('Fase_Alimento')['Kilos_Diarios_Lote'].sum()
            costo_total_alimento_sens = sum(consumo_por_fase_sens.get(f, 0) * costos_kg_map.get(f, 0) for f in consumo_por_fase_sens.index)
            
            costo_total_pollitos_sens = st.session_state.aves_programadas * st.session_state.costo_pollito
            costo_total_otros_sens = st.session_state.aves_programadas * st.session_state.otros_costos_ave
            costo_total_lote_sens = costo_total_alimento_sens + costo_total_pollitos_sens + costo_total_otros_sens

            costo_alimento_kilo = costo_total_alimento_sens / kilos_producidos_sens
            costo_pollito_kilo = costo_total_pollitos_sens / kilos_producidos_sens
            costo_otros_kilo = costo_total_otros_sens / kilos_producidos_sens
            costo_total_kilo = costo_total_lote_sens / kilos_producidos_sens
            conversion = consumo_total_kg / kilos_producidos_sens
            
            resultados_sensibilidad.append({
                "Peso Objetivo (gr)": int(peso_obj_sens),
                "Días de Ciclo": int(dias_ciclo),
                "Conversión Alimenticia": conversion,
                "Costo Alimento / Kilo ($)": costo_alimento_kilo,
                "Costo Pollito / Kilo ($)": costo_pollito_kilo,
                "Otros Costos / Kilo ($)": costo_otros_kilo,
                "Costo Total / Kilo ($)": costo_total_kilo
            })

    if resultados_sensibilidad:
        df_sensibilidad = pd.DataFrame(resultados_sensibilidad)
        columnas_finales = ["Peso Objetivo (gr)", "Días de Ciclo", "Conversión Alimenticia", "Costo Alimento / Kilo ($)", "Costo Pollito / Kilo ($)", "Otros Costos / Kilo ($)", "Costo Total / Kilo ($)"]
        
        def highlight_base(row):
            is_base = row["Peso Objetivo (gr)"] == peso_base
            return ['background-color: #D6EAF8' if is_base else '' for _ in row]

        st.dataframe(
            df_sensibilidad[columnas_finales].style
            .apply(highlight_base, axis=1)
            .format({
                "Peso Objetivo (gr)": "{:,.0f}",
                "Días de Ciclo": "{:,.0f}",
                "Conversión Alimenticia": "{:,.3f}",
                "Costo Alimento / Kilo ($)": "${:,.2f}",
                "Costo Pollito / Kilo ($)": "${:,.2f}",
                "Otros Costos / Kilo ($)": "${:,.2f}",
                "Costo Total / Kilo ($)": "${:,.2f}"
            })
            .background_gradient(cmap='Greens_r', subset=['Costo Total / Kilo ($)'])
            .background_gradient(cmap='Greens_r', subset=['Conversión Alimenticia'])
            .set_properties(**{'text-align': 'center'})
        )
        
        st.subheader("Visualización de la Estructura de Costos por Peso Objetivo")
        
        df_chart = df_sensibilidad.set_index("Peso Objetivo (gr)")
        df_cost_structure = df_chart[[
            "Costo Alimento / Kilo ($)", 
            "Costo Pollito / Kilo ($)", 
            "Otros Costos / Kilo ($)"
        ]]
        
        fig, ax = plt.subplots()
        df_cost_structure.plot(kind='bar', stacked=True, ax=ax, colormap='YlGn')
        
        ax.set_ylabel("Costo por Kilo ($)")
        ax.set_xlabel("Peso Objetivo (gramos)")
        ax.legend(title="Componente de Costo")
        plt.xticks(rotation=45)
        plt.tight_layout()

        bar_totals = df_cost_structure.sum(axis=1)

        for container in ax.containers:
            labels = [f"{ (v / bar_totals[i]) * 100 :.1f}%" if (v / bar_totals[i]) * 100 > 4 else '' 
                      for i, v in enumerate(container.datavalues)]
            
            ax.bar_label(container, labels=labels, label_type='center', color='black', weight='bold', fontsize=8)

        st.pyplot(fig)

except Exception as e:
    st.error(f"Error en el análisis de sensibilidad: {e}")
