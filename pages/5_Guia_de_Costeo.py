# Contenido COMPLETO para: pages/5_Guia_de_Costeo.py

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from PIL import Image

st.set_page_config(page_title="Guía de Costeo", page_icon="📖", layout="wide")

# --- LOGO EN SIDEBAR ---
BASE_DIR = Path(__file__).resolve().parent.parent 
try:
    logo = Image.open(BASE_DIR / "ARCHIVOS" / "log_PEQ.png")
    st.sidebar.image(logo, width=150)
except Exception:
    st.sidebar.warning("Logo no encontrado.")
st.sidebar.markdown("---")


# =============================================================================
# --- CONTENIDO DE LA PÁGINA ---
# =============================================================================

st.title("📖 Guía de Costeo del Pollo de Engorde")
st.subheader("Análisis de Costos y Métricas de Rendimiento: De la Granja al Sacrificio")
st.markdown("---")


try:
    # Construir la ruta completa al archivo PDF
    pdf_path = BASE_DIR / "ARCHIVOS" / "Costeo_Pollo_Engorde_ Granja_a_Sacrificio.pdf"
    
    # Leer el archivo en modo binario ('rb')
    with open(pdf_path, "rb") as pdf_file:
        pdf_bytes = pdf_file.read()

    # Crear el botón de descarga en el área principal
    st.download_button(
        label="📥 Descargar Guía Completa en PDF",
        data=pdf_bytes,
        file_name="Guia_Costeo_Pollo_Engorde.pdf", # Nombre que tendrá el archivo al descargar
        mime='application/pdf'
    )
except FileNotFoundError:
    st.warning("El archivo PDF de la guía no se encontró en la carpeta ARCHIVOS/.")

st.markdown("---")
# --- 1. ESTRUCTURA DE COSTOS ---
st.header("1. Estructura de Costos de Producción")
col1, col2 = st.columns([1.5, 1])

with col1:
    st.markdown(
        """
        El costo del **alimento balanceado** representa el componente más significativo en la producción de pollo de engorde, 
        constituyendo entre el **65% y 75% del costo total**. Este dominio subraya la importancia crítica de la 
        eficiencia alimenticia y la gestión de la cadena de suministro. 
        
        El costo del **pollito de un día** es el segundo factor más relevante, seguido por la **mano de obra**, 
        **sanidad** y otros costos operativos como energía, agua y mantenimiento de instalaciones.

        Una gestión financiera efectiva exige un control riguroso sobre cada uno de estos componentes, 
        con un enfoque prioritario en la optimización de la conversión alimenticia y la negociación 
        estratégica en la compra de insumos clave.
        """
    )

with col2:
    labels = 'Alimento', 'Pollito', 'Mano de Obra', 'Sanidad', 'Otros'
    sizes = [70, 18, 5, 3, 4]
    colors = ['#00A6FB', '#F5B700', '#00B295', '#F15946', '#5C3C92'] # Azul, Amarillo, Verde, Rojo, Púrpura

    fig, ax = plt.subplots()
    ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors, wedgeprops=dict(width=0.4))
    ax.axis('equal')
    st.pyplot(fig)

# --- 2. DESGLOSE DETALLADO ---
st.markdown("---")
st.header("2. Desglose Detallado de Costos de Producción")
st.write("""
El análisis detallado de costos revela la complejidad operativa de una granja avícola. Cada categoría principal 
se subdivide en componentes específicos que deben ser medidos y controlados.
""")

# Crear DataFrame para la tabla de desglose
data_desglose = {
    "Categoría de Costo": [
        "1. Alimento (65-75%)", "", "", "", "",
        "2. Pollito de un día (15-20%)",
        "3. Sanidad (3-5%)", "",
        "4. Mano de Obra (3-6%)",
        "5. Otros Costos (5-10%)", "", ""
    ],
    "Componente Específico": [
        "Alimento Pre-iniciador", "Alimento Iniciador", "Alimento Engorde", "Alimento Retiro", "Transporte de Alimento",
        "Costo de adquisición",
        "Vacunas y Medicamentos", "Bioseguridad",
        "Salarios y Prestaciones",
        "Energía y Agua", "Cama (viruta, cascarilla)", "Depreciación y Mantenimiento"
    ],
    "Descripción y Consideraciones": [
        "Fórmula de alta digestibilidad y costo para las primeras etapas de vida.",
        "Fórmula para el desarrollo estructural inicial.",
        "Fórmula para la ganancia de masa muscular.",
        "Fórmula final sin medicamentos con período de retiro.",
        "Costo de flete desde la planta de alimentos hasta la granja.",
        "Precio por unidad, dependiente de la línea genética y la demanda.",
        "Plan de vacunación (Gumboro, Newcastle) y tratamientos.",
        "Desinfectantes, control de plagas y medidas de control de acceso.",
        "Personal de granja (galponeros) y supervisión técnica.",
        "Electricidad para calefacción y ventilación; consumo de agua.",
        "Material absorbente para el piso del galpón.",
        "Costos asociados a la infraestructura y equipos."
    ]
}
df_desglose = pd.DataFrame(data_desglose)
st.dataframe(df_desglose, use_container_width=True)


# --- 3. INDICADORES CLAVE (KPIs) ---
st.markdown("---")
st.header("3. Indicadores Clave de Rendimiento (KPIs)")

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric(label="Conversión Alimenticia", value="1.65", help="Kg de alimento por Kg de peso vivo. Menor es mejor.")
kpi2.metric(label="Peso Promedio", value="2,500 g", help="Peso final al momento del sacrificio. Depende del mercado.")
kpi3.metric(label="Porcentaje de Mortalidad", value="< 4%", help="Índice de bajas durante el ciclo de engorde.")
kpi4.metric(label="Factor de Eficiencia Europeo", value="> 400", help="Métrica integral que combina peso, edad, viabilidad y conversión.")

# --- 4. MÉTRICAS AVANZADAS ---
st.markdown("---")
st.header("4. Análisis de Métricas de Productividad Avanzadas")
adv1, adv2 = st.columns(2)

with adv1:
    st.subheader("Índice de Productividad (IP)")
    st.latex(r'''
    IP = \frac{(\text{Peso Promedio (g)})^3}{(\text{Consumo Alimento (g)})^2} \div 10
    ''')
    st.write("""
    El IP pondera de forma exponencial la ganancia de peso frente al consumo, 
    asignando mayor importancia al peso final alcanzado. Un IP alto es indicativo de un lote 
    altamente productivo que expresó su máximo potencial genético.
    """)

with adv2:
    st.subheader("Diferencia VS Genética")
    st.latex(r'''
    \Delta \text{ Genética} = \text{Peso Real} - \text{Peso Teórico (según consumo)}
    ''')
    st.write("""
    Esta métrica de diagnóstico cuantifica la brecha entre el rendimiento real y el potencial 
    genético para un nivel de consumo específico.
    - **Valor Positivo:** El lote superó las expectativas.
    - **Valor Negativo:** Señal de alerta que indica problemas de manejo, infraestructura, sanidad o calidad de alimento.
    """)
