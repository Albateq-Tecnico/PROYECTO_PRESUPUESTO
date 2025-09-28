# Contenido COMPLETO y FINAL para: pages/4_Simulador_de_Productividad.py

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from utils import load_data, reconstruir_tabla_base

st.set_page_config(page_title="Simulador de Productividad", page_icon="⚙️", layout="wide")

st.title("⚙️ Simulador de Eficiencia Productiva")

# --- TEXTO EXPLICATIVO AÑADIDO ---
st.info(
    """
    La productividad es un indicador clave que mide la eficiencia con la que un lote convierte el alimento en masa corporal, 
    comparado con su potencial genético. Una baja productividad es una señal de alerta crítica; significa que cada kilogramo 
    de alimento rinde menos de lo esperado, lo que **infla directamente el costo final por kilo**. Esta ineficiencia puede 
    ser causada por factores como la calidad del alimento, desafíos sanitarios o estrés ambiental en la granja.
    """
)

# --- Validar que el presupuesto principal se ha ejecutado ---
if 'resultados_base' not in st.session_state:
    st.warning("👈 Por favor, ejecuta un cálculo en la página '1_Presupuesto_Principal' primero.")
    st.stop()

try:
    # --- Extraer resultados base de la sesión ---
    resultados_base = st.session_state['resultados_base']
    productividad_base_perc = st.session_state.get('productividad', 100.0)
    
    costo_total_alimento = resultados_base.get('costo_total_alimento', 0)
    costo_total_pollitos = resultados_base.get('costo_total_pollitos', 0)
    costo_total_otros = resultados_base.get('costo_total_otros', 0)
    costo_total_lote = costo_total_alimento + costo_total_pollitos + costo_total_otros

    consumo_total_kg = resultados_base.get('consumo_total_kg', 0)
    
    kilos_base_ajustados = resultados_base.get('kilos_totales_producidos', 0)
    if productividad_base_perc == 0:
        st.error("La productividad base no puede ser cero.")
        st.stop()
    kilos_potenciales_100 = kilos_base_ajustados / (productividad_base_perc / 100.0)

    # =============================================================================
    # --- 1. Simulador Interactivo de Productividad ---
    # =============================================================================
    st.header("1. Simulador Interactivo de Productividad")
    st.write("Ajusta el slider para simular cómo una variación en la productividad general afecta tus costos.")

    productividad_sim_perc = st.slider(
        "Seleccione la Productividad (%) a simular", 
        min_value=70.0, max_value=110.0, value=productividad_base_perc, step=0.5, format="%.1f%%"
    )

    kilos_producidos_sim = kilos_potenciales_100 * (productividad_sim_perc / 100.0)

    if kilos_producidos_sim > 0:
        costo_total_kilo_sim = costo_total_lote / kilos_producidos_sim
        conversion_sim = consumo_total_kg / kilos_producidos_sim
    else:
        costo_total_kilo_sim = 0
        conversion_sim = 0

    st.markdown("##### Resultados de la Simulación")
    kpi_cols = st.columns(2)
    kpi_cols[0].metric(
        label="Costo Total por Kilo Simulado", 
        value=f"${costo_total_kilo_sim:,.2f}",
        delta=f"${costo_total_kilo_sim - resultados_base.get('costo_total_por_kilo', 0):,.2f}",
        delta_color="inverse"
    )
    kpi_cols[1].metric(
        label="Conversión Alimenticia Simulada",
        value=f"{conversion_sim:,.3f}",
        delta=f"{conversion_sim - resultados_base.get('conversion_alimenticia', 0):,.3f}",
        delta_color="inverse"
    )

    # =============================================================================
    # --- 2. Análisis de Sensibilidad por Productividad ---
    # =============================================================================
    st.markdown("---")
    st.header("2. Análisis de Sensibilidad por Productividad")
    st.write(f"""
    Esta tabla y gráfico muestran cómo cambian los indicadores clave. La fila resaltada corresponde a la 
    productividad definida en la página principal ({productividad_base_perc}%).
    """)

    resultados_sensibilidad = []
    niveles_productividad = sorted(list(set([100.0, 97.5, 95.0, 90.0, 85.0, 80.0, 75.0, productividad_base_perc])), reverse=True)

    for prod_perc in niveles_productividad:
        kilos_sim = kilos_potenciales_100 * (prod_perc / 100.0)
        
        if kilos_sim > 0:
            costo_kilo = costo_total_lote / kilos_sim
            conversion = consumo_total_kg / kilos_sim
            costo_alimento_kilo = costo_total_alimento / kilos_sim
            costo_pollito_kilo = costo_total_pollitos / kilos_sim
            costo_otros_kilo = costo_total_otros / kilos_sim
        else:
            costo_kilo = conversion = costo_alimento_kilo = costo_pollito_kilo = costo_otros_kilo = 0

        resultados_sensibilidad.append({
            "Productividad (%)": prod_perc,
            "Kilos Producidos": kilos_sim,
            "Conversión": conversion,
            "Costo Alimento/Kilo": costo_alimento_kilo,
            "Costo Pollito/Kilo": costo_pollito_kilo,
            "Costo Otros/Kilo": costo_otros_kilo,
            "Costo Total/Kilo": costo_kilo
        })

    df_sensibilidad = pd.DataFrame(resultados_sensibilidad)

    def highlight_base(row):
        is_base = row["Productividad (%)"] == productividad_base_perc
        return ['background-color: #D6EAF8' if is_base else '' for _ in row]

    st.dataframe(
        df_sensibilidad.style
        .apply(highlight_base, axis=1)
        .format({
            "Productividad (%)": "{:,.1f}%", "Kilos Producidos": "{:,.0f}",
            "Conversión": "{:,.3f}", "Costo Alimento/Kilo": "${:,.2f}",
            "Costo Pollito/Kilo": "${:,.2f}", "Costo Otros/Kilo": "${:,.2f}",
            "Costo Total/Kilo": "${:,.2f}"
        })
        .background_gradient(cmap='Reds', subset=['Costo Total/Kilo', 'Conversión'])
        .set_properties(**{'text-align': 'center'})
    )

    # --- GRÁFICO DE LÍNEAS ELIMINADO ---

    # =============================================================================
    # --- 3. Visualización de la Estructura de Costos ---
    # =============================================================================
    st.markdown("---")
    st.header("3. Estructura de Costos por Productividad")
    st.write("El gráfico muestra cómo cambia la participación porcentual de cada componente en el costo total.")

    df_estructura = df_sensibilidad.set_index("Productividad (%)")[[
        "Costo Alimento/Kilo", "Costo Pollito/Kilo", "Costo Otros/Kilo"
    ]]
    df_porcentaje = df_estructura.div(df_estructura.sum(axis=1), axis=0) * 100
    
    fig, ax = plt.subplots()
    # --- COLORES ESTANDARIZADOS ---
    colores = ['#2E7D32', '#66BB6A', '#A5D6A7'] # Paleta de verdes
    df_porcentaje.plot(kind='bar', stacked=True, ax=ax, color=colores)

    ax.set_ylabel("Participación en el Costo por Kilo")
    ax.set_xlabel("Productividad (%)")
    ax.legend(title="Componente de Costo")
    ax.yaxis.set_major_formatter(plt.matplotlib.ticker.PercentFormatter(100))
    plt.xticks(rotation=0)
    plt.tight_layout()

    for container in ax.containers:
        labels = [f'{v:.0f}%' if v > 5 else '' for v in container.datavalues]
        ax.bar_label(container, labels=labels, label_type='center', color='white', weight='bold')

    st.pyplot(fig)

except Exception as e:
    st.error(f"Ocurrió un error al procesar la simulación: {e}")
    st.exception(e)
