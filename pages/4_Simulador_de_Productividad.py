# Contenido COMPLETO y FINAL para: pages/4_Simulador_de_Productividad.py

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from utils import load_data, reconstruir_tabla_base

st.set_page_config(page_title="Simulador de Productividad", page_icon="⚙️", layout="wide")

st.title("⚙️ Simulador de Eficiencia Productiva")

st.info(
    """
    La métrica "Productividad (%)", también conocida como "Diferencia VS Genética", es un parámetro zootécnico avanzado diseñado para cuantificar la eficiencia de la conversión alimenticia en un lote de aves. Su metodología aísla la eficiencia metabólica al comparar el peso real promedio del lote contra el estándar genético (benchmark) para una cantidad de alimento consumido específica. A diferencia del Índice de Conversión Alimenticia (ICA), este enfoque no se ve afectado por variaciones en el apetito, centrándose exclusivamente en la calidad de la conversión.

Un resultado positivo indica un rendimiento superior al estándar, producto de una nutrición, sanidad y manejo óptimos. En contraste, un resultado negativo es una señal de alerta crítica que revela una ineficiencia productiva. Esta puede originarse por diversos factores, principalmente:

Calidad del Alimento: Una densidad nutricional inferior a la especificada.

Sanidad del Lote: Desafíos sanitarios, incluso subclínicos, que desvían nutrientes del crecimiento hacia la respuesta inmune.

Infraestructura de la Granja: Instalaciones con obsolescencia, pobre aislamiento o sistemas de ventilación deficientes que limitan la capacidad de mitigar el estrés ambiental, obligando a las aves a desviar energía del crecimiento hacia la termorregulación.

Manejo y Ambiente: Factores de estrés como temperaturas inadecuadas, mala calidad del aire o alta densidad.

Desde la perspectiva de costos, esta métrica es fundamental. Una productividad negativa significa que cada kilogramo de alimento —la principal inversión del ciclo— rinde menos de su potencial, lo que infla directamente el costo final por kilogramo de carne producido y permite a la gerencia diagnosticar el origen del problema con mayor precisión.
    """
)

if 'resultados_base' not in st.session_state:
    st.warning("👈 Por favor, ejecuta un cálculo en la página '1_Presupuesto_Principal' primero.")
    st.stop()

try:
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
    
    # =============================================================================
    # --- 3. Visualización del Impacto de la Productividad en los Costos ---
    # =============================================================================
    st.markdown("---")
    st.header("3. Impacto de la Productividad en el Costo por Kilo")
    st.write("""
    Este gráfico muestra cómo el costo total por kilo y sus componentes aumentan a medida que disminuye la eficiencia productiva del lote.
    """)

    df_chart = df_sensibilidad.set_index("Productividad (%)")
    
    # Seleccionamos las columnas de costos por kilo
    df_cost_lines = df_chart[[
        "Costo Alimento/Kilo", 
        "Costo Pollito/Kilo", 
        "Costo Otros/Kilo",
        "Costo Total/Kilo"
    ]]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Graficar las líneas con un marcador en cada punto
    df_cost_lines.plot(kind='line', ax=ax, marker='o')
    
    # Formatear el eje Y como moneda
    from matplotlib.ticker import StrMethodFormatter
    ax.yaxis.set_major_formatter(StrMethodFormatter('${x:,.0f}'))
    
    # Mejorar la visualización
    ax.set_ylabel("Costo por Kilo ($)")
    ax.set_xlabel("Productividad (%)")
    ax.set_title("Sensibilidad del Costo por Kilo a la Productividad")
    ax.legend(title="Componente de Costo")
    ax.grid(True, linestyle='--', alpha=0.6)
    
    # Invertir el eje X para que la "caída" de productividad se lea de izquierda a derecha
    ax.invert_xaxis()
    
    plt.tight_layout()
    st.pyplot(fig)

except Exception as e:
    st.error(f"Ocurrió un error al procesar la simulación: {e}")
    st.exception(e)
