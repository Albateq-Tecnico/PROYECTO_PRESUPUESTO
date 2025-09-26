# Contenido COMPLETO para: pages/3_Simulador_de_Alimentacion.py

import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
from utils import load_data, reconstruir_tabla_base # Usamos la nueva función

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

# --- Controles interactivos para el plan de alimentación ---
c1, c2, c3 = st.columns(3)
with c1:
    pre_iniciador_sim = st.slider("Gramos Pre-iniciador/ave", 0, 500, st.session_state.pre_iniciador)
with c2:
    iniciador_sim = st.slider("Gramos Iniciador/ave", 500, 2000, st.session_state.iniciador)
with c3:
    retiro_sim = st.slider("Gramos Retiro/ave", 0, 1000, st.session_state.retiro)

try:
    # --- Cálculos para el Plan de Alimentación Simulado ---
    tabla_sim_alimento = tabla_base_completa.copy()
    closest_idx = (tabla_sim_alimento['Peso_Estimado'] - st.session_state.peso_objetivo).abs().idxmin()
    tabla_sim_alimento = tabla_sim_alimento.loc[:closest_idx].copy()

    df_interp = tabla_sim_alimento.drop_duplicates(subset=['Peso_Estimado']).sort_values('Peso_Estimado')
    consumo_total_objetivo_ave = np.interp(st.session_state.peso_objetivo, df_interp['Peso_Estimado'], df_interp['Cons_Acum_Ajustado'])
    
    # Usar los valores de los sliders para definir las fases
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

    # Calcular costos con el nuevo plan
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

    # Mostrar KPIs del plan simulado
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
Esta tabla muestra cómo cambian los indicadores clave si decides llevar tus aves a un peso de venta diferente. 
Se usa el plan de alimentación y la mortalidad lineal definidos en la página principal.
""")

try:
    resultados_sensibilidad = []
    peso_base = st.session_state.peso_objetivo
    paso = 100
    pesos_a_evaluar = [peso_base + i * paso for i in range(-3, 4)]

    for peso_obj_sens in pesos_a_evaluar:
        if peso_obj_sens <= 0: continue
        
        tabla_sens = tabla_base_completa.copy()
        
        # Encontrar el nuevo punto de corte y truncar
        try:
            closest_idx_sens = (tabla_sens['Peso_Estimado'] - peso_obj_sens).abs().idxmin()
            tabla_sens = tabla_sens.loc[:closest_idx_sens].copy()
        except ValueError:
            continue # Si el peso objetivo está fuera del rango de la tabla, saltar

        # Recalcular todo para este nuevo escenario de peso
        dias_ciclo = tabla_sens['Dia'].iloc[-1]
        
        consumo_total_ave = tabla_sens['Cons_Acum_Ajustado'].iloc[-1]
        
        # Mortalidad y Saldo
        mortalidad_total_aves = st.session_state.aves_programadas * (st.session_state.mortalidad_objetivo / 100)
        mortalidad_diaria_prom = mortalidad_total_aves / dias_ciclo if dias_ciclo > 0 else 0
        tabla_sens['Saldo'] = st.session_state.aves_programadas - (tabla_sens['Dia'] * mortalidad_diaria_prom).apply(np.floor)
        
        # Consumo y Costo
        tabla_sens['Cons_Diario_Ave_gr'] = tabla_sens['Cons_Acum_Ajustado'].diff().fillna(tabla_sens['Cons_Acum_Ajustado'].iloc[0])
        tabla_sens['Kilos_Diarios_Lote'] = (tabla_sens['Cons_Diario_Ave_gr'] * tabla_sens['Saldo']) / 1000
        consumo_total_kg = tabla_sens['Kilos_Diarios_Lote'].sum()
        
        aves_producidas = tabla_sens['Saldo'].iloc[-1]
        peso_final_real = tabla_sens['Peso_Estimado'].iloc[-1]
        kilos_producidos = (aves_producidas * peso_final_real) / 1000
        
        if kilos_producidos > 0:
            conversion = consumo_total_kg / kilos_producidos
            
            resultados_sensibilidad.append({
                "Peso Objetivo (gr)": int(peso_obj_sens),
                "Días de Ciclo": int(dias_ciclo),
                "Peso Final Real (gr)": int(peso_final_real),
                "Conversión Alimenticia": conversion,
                "Consumo / Ave (gr)": int(consumo_total_ave)
            })

    if resultados_sensibilidad:
        df_sensibilidad = pd.DataFrame(resultados_sensibilidad)
        st.dataframe(
            df_sensibilidad.style
            .format({
                "Peso Objetivo (gr)": "{:,.0f}",
                "Días de Ciclo": "{:,.0f}",
                "Peso Final Real (gr)": "{:,.0f}",
                "Conversión Alimenticia": "{:,.3f}",
                "Consumo / Ave (gr)": "{:,.0f}"
            })
            .background_gradient(cmap='Greens_r', subset=['Conversión Alimenticia'])
            .set_properties(**{'text-align': 'center'})
        )
except Exception as e:
    st.error(f"Error en el análisis de sensibilidad: {e}")
