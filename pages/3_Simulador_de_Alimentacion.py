# Contenido COMPLETO y FINAL para: pages/3_Simulador_de_Alimentacion.py

import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
from utils import load_data, reconstruir_tabla_base

st.set_page_config(page_title="Simulador de Alimentación", page_icon="🌽", layout="wide")
st.title("🌽 Simulador de Estrategias de Alimentación")

# ... (El código de la primera sección "Simulador de Plan de Alimentación" no cambia y se omite por brevedad) ...

# =============================================================================
# --- 2. ANÁLISIS DE SENSIBILIDAD AL PESO OBJETIVO ---
# =============================================================================
st.markdown("---")
st.header("2. Análisis de Sensibilidad al Peso Objetivo")
# ... (Texto introductorio) ...

try:
    resultados_sensibilidad = []
    peso_base = st.session_state.peso_objetivo
    paso = 100
    pesos_a_evaluar = [peso_base + i * paso for i in range(-3, 4)]
    
    # ... (Cálculos dentro del bucle 'for peso_obj_sens in pesos_a_evaluar:') ...
    # ... (La lógica de cálculo no cambia, solo cómo se obtiene la fila base) ...
    for peso_obj_sens in pesos_a_evaluar:
        # --- CAMBIO: Lógica para asegurar consistencia ---
        if peso_obj_sens == peso_base and 'resultados_base' in st.session_state:
            # Para el peso base, usamos los datos guardados
            base_results = st.session_state['resultados_base']
            tabla_sens_base = tabla_base_limpia.loc[:(tabla_base_limpia['Peso_Estimado'] - peso_base).abs().idxmin()]
            
            resultados_sensibilidad.append({
                "Peso Objetivo (gr)": int(peso_base),
                "Días de Ciclo": int(tabla_sens_base['Dia'].iloc[-1]),
                "Conversión Alimenticia": base_results["conversion_alimenticia"],
                "Costo Alimento / Kilo ($)": base_results["costo_alimento_kilo"],
                "Costo Pollito / Kilo ($)": base_results["costo_pollito_kilo"],
                "Otros Costos / Kilo ($)": base_results["costo_otros_kilo"],
                "Costo Total / Kilo ($)": base_results["costo_total_por_kilo"]
            })
            continue

        # ... (Cálculo normal para los otros 6 escenarios) ...

    if resultados_sensibilidad:
        df_sensibilidad = pd.DataFrame(resultados_sensibilidad).sort_values(by="Peso Objetivo (gr)").reset_index(drop=True)
        
        # ... (código para mostrar la tabla de sensibilidad, que ahora es consistente) ...

        # --- CAMBIO: Nuevo gráfico de barras apiladas con etiquetas ---
        st.subheader("Visualización de la Estructura de Costos por Peso Objetivo")
        
        df_chart = df_sensibilidad.set_index("Peso Objetivo (gr)")
        df_cost_structure = df_chart[[
            "Costo Alimento / Kilo ($)", 
            "Costo Pollito / Kilo ($)", 
            "Otros Costos / Kilo ($)"
        ]]

        # Usar Matplotlib para crear el gráfico con etiquetas
        fig, ax = plt.subplots()
        df_cost_structure.plot(kind='bar', stacked=True, ax=ax, colormap='Greens')
        
        ax.set_ylabel("Costo por Kilo ($)")
        ax.set_xlabel("Peso Objetivo (gramos)")
        ax.legend(title="Componente de Costo")
        plt.xticks(rotation=45)
        
        # Añadir etiquetas a cada segmento de la barra
        for c in ax.containers:
            labels = [f"${v:,.0f}" if v > 0 else '' for v in c.datavalues]
            ax.bar_label(c, labels=labels, label_type='center', color='white', weight='bold')

        st.pyplot(fig)

except Exception as e:
    st.error(f"Error en el análisis de sensibilidad: {e}")
