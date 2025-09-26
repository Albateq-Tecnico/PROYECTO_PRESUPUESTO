# -*- coding: utf-8 -*-
"""
Created on Mon Sep 22 10:43:19 2025
@author: juan.leyton
"""

import streamlit as st
import pandas as pd
import numpy as np
from PIL import Image
from datetime import date, timedelta
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.offsetbox import OffsetImage, AnnotationBbox

# --- CONFIGURACIÓN DE LA PÁGINA (Debe ser el primer comando de Streamlit) ---
st.set_page_config(
    page_title="Presupuesto Avícola",
    page_icon="🐔",
    layout="wide",
)

# --- DEFINIR RUTA BASE (Buena práctica) ---
BASE_DIR = Path(__file__).resolve().parent

# =============================================================================
# --- FUNCIONES AUXILIARES ---
# =============================================================================

@st.cache_data
def load_data(file_path):
    """Carga datos desde un archivo CSV de forma robusta."""
    try:
        return pd.read_csv(file_path)
    except FileNotFoundError:
        st.error(f"Error Crítico: No se encontró el archivo de datos en: {file_path}")
        return None
    except Exception as e:
        st.error(f"Error Crítico al cargar el archivo {file_path.name}: {e}")
        return None

def clean_numeric_column(series):
    """Convierte una columna a tipo numérico, manejando comas como decimales."""
    if series.dtype == 'object':
        return pd.to_numeric(series.str.replace(',', '.', regex=False), errors='coerce')
    return series

def calcular_peso_estimado(data, coeffs_df, raza, sexo):
    """Calcula el peso estimado usando coeficientes de regresión polinomial."""
    if coeffs_df is None: return pd.Series(0, index=data.index)
    coeffs_seleccion = coeffs_df[(coeffs_df['RAZA'] == raza) & (coeffs_df['SEXO'] == sexo)]
    if not coeffs_seleccion.empty:
        params = coeffs_seleccion.iloc[0]
        x = data['Cons_Acum_Ajustado']
        return (params['Intercept'] + params['Coef_1'] * x + params['Coef_2'] * (x**2) + 
                params['Coef_3'] * (x**3) + params['Coef_4'] * (x**4))
    st.warning(f"No se encontraron coeficientes de peso para {raza} - {sexo}.")
    return pd.Series(0, index=data.index)

# --- MEJORA: Función de estilo más eficiente ---
def style_kpi_df(df):
    """Aplica formato condicional a un DataFrame de KPIs de forma eficiente."""
    def formatter(val, metric_name):
        if metric_name == "Conversión Alimenticia": return f"{val:,.3f}"
        if "($)" in metric_name: return f"${val:,.2f}"
        return f"{val:,.0f}"

    # Crear una copia estilizada para aplicar formatos basados en el índice
    df_styled = df.copy()
    df_styled['Valor'] = [formatter(val, name) for name, val in df['Valor'].items()]
    return df_styled

# --- CARGA DE DATOS ---
df_coeffs = load_data(BASE_DIR / "ARCHIVOS" / "Cons_Acum_Peso.csv")
df_coeffs_15 = load_data(BASE_DIR / "ARCHIVOS" / "Cons_Acum_Peso_15.csv")
df_referencia = load_data(BASE_DIR / "ARCHIVOS" / "ROSS_COBB_HUBBARD_2025.csv")

# =============================================================================
# --- PANEL LATERAL DE ENTRADAS (SIDEBAR) ---
# =============================================================================

st.sidebar.header("1. Valores de Entrada")
try:
    logo = Image.open(BASE_DIR / "ARCHIVOS" / "log_PEQ.png")
    st.sidebar.image(logo, width=150)
except FileNotFoundError:
    st.sidebar.warning("Logo no encontrado.")

# --- DATOS DEL LOTE ---
st.sidebar.subheader("Datos del Lote")
fecha_llegada = st.sidebar.date_input("Fecha de llegada", date.today(), key="fecha_llegada")
aves_programadas = st.sidebar.number_input("# Aves Programadas", 0, value=10000, step=1000, format="%d", key="aves_programadas")

# --- GENÉTICA ---
st.sidebar.subheader("Línea Genética")
razas = sorted(df_referencia['RAZA'].unique()) if df_referencia is not None else ["ROSS 308 AP", "COBB", "HUBBARD", "ROSS"]
sexos = sorted(df_referencia['SEXO'].unique()) if df_referencia is not None else ["MIXTO", "HEMBRA", "MACHO"]
raza_seleccionada = st.sidebar.selectbox("RAZA", razas, key="raza_seleccionada")
sexo_seleccionado = st.sidebar.selectbox("SEXO", sexos, key="sexo_seleccionado")

# --- OBJETIVOS ---
st.sidebar.subheader("Objetivos del Lote")
peso_objetivo = st.sidebar.number_input("Peso Objetivo (gramos)", 0, value=2500, step=50, format="%d", key="peso_objetivo")
mortalidad_objetivo = st.sidebar.number_input("Mortalidad Objetivo %", 0.0, 100.0, 5.0, 0.5, format="%.2f", key="mortalidad_objetivo")

# --- CONDICIONES DE GRANJA ---
st.sidebar.subheader("Condiciones de Granja")
tipo_granja = st.sidebar.radio("Tipo de GRANJA", ["TUNEL", "MEJORADA", "NATURAL"], index=2, key="tipo_granja")
productividad_options = {"TUNEL": 100.0, "MEJORADA": 97.5, "NATURAL": 95.0}
productividad = st.sidebar.number_input("Productividad (%)", 0.0, 110.0, productividad_options[tipo_granja], 0.1, format="%.2f", help=f"Productividad teórica: {productividad_options}", key="productividad")

asnm = st.sidebar.radio("Altitud (ASNM)", ["ALTA >2000 msnm", "MEDIA <2000 y >1000 msnm", "BAJA < 1000 msnm"], index=2, key="asnm")

# --- PROGRAMA DE ALIMENTACIÓN ---
st.sidebar.subheader("Programa de Alimentación")
restriccion_map = {"ALTA >2000 msnm": 20, "MEDIA <2000 y >1000 msnm": 10, "BAJA < 1000 msnm": 0}
max_restriccion = restriccion_map[asnm]
st.sidebar.info(f"Recomendación: Máxima restricción del {max_restriccion}%.")
restriccion_programada = st.sidebar.number_input("% Restricción Programado", 0, 100, max_restriccion, 1, format="%d", key="restriccion_programada")
if restriccion_programada > max_restriccion:
    st.sidebar.warning(f"Advertencia: La restricción supera el {max_restriccion}% recomendado.")

pre_iniciador = st.sidebar.number_input("Pre-iniciador (gr/ave)", 0, 300, 150, 10, format="%d", key="pre_iniciador")
iniciador = st.sidebar.number_input("Iniciador (gr/ave)", 1, 2000, 1200, 10, format="%d", key="iniciador")
retiro = st.sidebar.number_input("Retiro (gr/ave)", 0, 2000, 500, 10, format="%d", key="retiro")
st.sidebar.markdown("_El **Engorde** se calcula por diferencia._")

# --- UNIDADES Y COSTOS ---
st.sidebar.subheader("Unidades y Costos")
unidades_calculo = st.sidebar.selectbox("Unidades de Cálculo", ["Kilos", "Bultos x 40 Kilos"], key="unidades_calculo")
val_pre_iniciador = st.sidebar.number_input("Costo Pre-iniciador ($/Kg)", 0.0, 2200.0, 0.01, format="%.2f", key="val_pre_iniciador")
val_iniciador = st.sidebar.number_input("Costo Iniciador ($/Kg)", 0.0, 2200.0, 0.01, format="%.2f", key="val_iniciador")
val_engorde = st.sidebar.number_input("Costo Engorde ($/Kg)", 0.0, 2200.0, 0.01, format="%.2f", key="val_engorde")
val_retiro = st.sidebar.number_input("Costo Retiro ($/Kg)", 0.0, 2200.0, 0.01, format="%.2f", key="val_retiro")
porcentaje_participacion_alimento = st.sidebar.number_input("Participación Alimento en Costo Total (%)", 0.0, 100.0, 65.0, 0.01, format="%.2f", key="porcentaje_participacion_alimento")

# =============================================================================
# --- ÁREA PRINCIPAL ---
# =============================================================================

st.title("🐔 Presupuesto Avícola")
st.markdown("---")

if df_referencia is None:
    st.error("No se pueden mostrar resultados porque el archivo de referencia principal no se cargó.")
    st.stop()

if aves_programadas <= 0 or peso_objetivo <= 0:
    st.info("👈 Ingrese un '# Aves Programadas' y un 'Peso Objetivo' mayores a 0 para ver los resultados.")
    st.stop()

try:
    # 1. FILTRAR DATOS
    tabla_filtrada = df_referencia[
        (df_referencia['RAZA'] == raza_seleccionada) &
        (df_referencia['SEXO'] == sexo_seleccionado)
    ].copy()

    if tabla_filtrada.empty:
        st.warning(f"No se encontraron datos de referencia para {raza_seleccionada} - {sexo_seleccionado}.")
        st.stop()
    
    st.header("Resultados del Presupuesto")
    
    tabla_filtrada['Cons_Acum'] = clean_numeric_column(tabla_filtrada['Cons_Acum'])
    tabla_filtrada['Peso'] = clean_numeric_column(tabla_filtrada['Peso'])

    # 2. CÁLCULOS SECUENCIALES
    factor_ajuste = 1 - (restriccion_programada / 100.0)
    tabla_filtrada['Cons_Acum_Ajustado'] = tabla_filtrada['Cons_Acum'] * factor_ajuste

    dias_1_14 = tabla_filtrada['Dia'] <= 14
    dias_15_adelante = tabla_filtrada['Dia'] >= 15
    tabla_filtrada.loc[dias_1_14, 'Peso_Estimado'] = calcular_peso_estimado(tabla_filtrada[dias_1_14], df_coeffs_15, raza_seleccionada, sexo_seleccionado)
    tabla_filtrada.loc[dias_15_adelante, 'Peso_Estimado'] = calcular_peso_estimado(tabla_filtrada[dias_15_adelante], df_coeffs, raza_seleccionada, sexo_seleccionado)
    tabla_filtrada['Peso_Estimado'] *= (productividad / 100.0)

    closest_idx = (tabla_filtrada['Peso_Estimado'] - peso_objetivo).abs().idxmin()
    dia_obj = tabla_filtrada.loc[closest_idx, 'Dia']
    peso_obj_final = tabla_filtrada.loc[closest_idx, 'Peso_Estimado']
    
    tabla_filtrada = tabla_filtrada.loc[:closest_idx].copy()
    
    # --- CAMBIO CLAVE: Guardar la tabla base para el simulador ---
    st.session_state['tabla_base_calculada'] = tabla_filtrada

    df_interp = tabla_filtrada.drop_duplicates(subset=['Peso_Estimado']).sort_values('Peso_Estimado')
    consumo_total_objetivo_ave = np.interp(peso_objetivo, df_interp['Peso_Estimado'], df_interp['Cons_Acum_Ajustado'])
    
    limite_pre = pre_iniciador
    limite_ini = pre_iniciador + iniciador
    limite_ret = consumo_total_objetivo_ave - retiro if retiro > 0 else np.inf
    conditions = [
        tabla_filtrada['Cons_Acum_Ajustado'] <= limite_pre,
        tabla_filtrada['Cons_Acum_Ajustado'].between(limite_pre, limite_ini, inclusive='right'),
        tabla_filtrada['Cons_Acum_Ajustado'] > limite_ret
    ]
    choices = ['Pre-iniciador', 'Iniciador', 'Retiro']
    tabla_filtrada['Fase_Alimento'] = np.select(conditions, choices, default='Engorde')
    
    total_mortalidad_aves = aves_programadas * (mortalidad_objetivo / 100.0)
    mortalidad_diaria = total_mortalidad_aves / dia_obj if dia_obj > 0 else 0
    tabla_filtrada['Mortalidad_Acumulada'] = (tabla_filtrada['Dia'] * mortalidad_diaria).apply(np.floor)
    tabla_filtrada['Saldo'] = aves_programadas - tabla_filtrada['Mortalidad_Acumulada']

    tabla_filtrada['Fecha'] = tabla_filtrada['Dia'].apply(lambda d: fecha_llegada + timedelta(days=d - 1))
    
    if unidades_calculo == "Kilos":
        total_col, daily_col = "Kilos Totales", "Kilos Diarios"
        tabla_filtrada[total_col] = (tabla_filtrada['Cons_Acum_Ajustado'] * tabla_filtrada['Saldo']) / 1000
    else:
        total_col, daily_col = "Bultos Totales", "Bultos Diarios"
        tabla_filtrada[total_col] = np.ceil((tabla_filtrada['Cons_Acum_Ajustado'] * tabla_filtrada['Saldo']) / 40000)
    
    tabla_filtrada[daily_col] = tabla_filtrada[total_col].diff().fillna(tabla_filtrada[total_col])

    # 3. VISUALIZACIONES
    st.subheader(f"Tabla de Proyección para {aves_programadas} aves ({raza_seleccionada} - {sexo_seleccionado})")
    columnas_a_mostrar = ['Dia', 'Fecha', 'Saldo', 'Cons_Acum', 'Cons_Acum_Ajustado', 'Peso', 'Peso_Estimado', daily_col, total_col, 'Fase_Alimento']
    format_dict = {col: "{:,.0f}" for col in columnas_a_mostrar if col not in ['Fecha', 'Fase_Alimento']}
    styler = tabla_filtrada[columnas_a_mostrar].style.format(format_dict)
    styler.apply(lambda row: ['background-color: #ffcccc' if row.name == closest_idx else '' for _ in row], axis=1)
    st.dataframe(styler.hide(axis="index"), use_container_width=True)
    
    # 4. ANÁLISIS ECONÓMICO
    st.subheader("Resumen del Presupuesto de Alimento")
    factor_kg = 1 if unidades_calculo == "Kilos" else 40
    consumo_por_fase = tabla_filtrada.groupby('Fase_Alimento')[daily_col].sum()
    
    fases = ['Pre-iniciador', 'Iniciador', 'Engorde', 'Retiro']
    unidades = [consumo_por_fase.get(f, 0) for f in fases]
    costos_kg = [val_pre_iniciador, val_iniciador, val_engorde, val_retiro]
    costos = [(u * factor_kg) * c for u, c in zip(unidades, costos_kg)]

    df_resumen = pd.DataFrame({
        "Fase de Alimento": fases + ["Total"],
        f"Consumo ({unidades_calculo})": unidades + [sum(unidades)],
        "Valor del Alimento ($)": costos + [sum(costos)]
    })
    styler_resumen = df_resumen.style.format({f"Consumo ({unidades_calculo})": "{:,.0f}", "Valor del Alimento ($)": "${:,.2f}"})
    st.dataframe(styler_resumen.hide(axis="index"), use_container_width=True)

    st.subheader("Indicadores Clave de Desempeño (KPIs)")
    costo_total_alimento = sum(costos)
    aves_producidas = tabla_filtrada.loc[closest_idx, 'Saldo']
    kilos_totales_producidos = (aves_producidas * peso_obj_final) / 1000
    consumo_total_kg = sum(unidades) * factor_kg
    
    if kilos_totales_producidos > 0 and porcentaje_participacion_alimento > 0:
        costo_total_lote = costo_total_alimento / (porcentaje_participacion_alimento / 100)
        costo_total_kilo = costo_total_lote / kilos_totales_producidos
        conversion_alimenticia = consumo_total_kg / kilos_totales_producidos

        # --- MEJORA: Cálculo de Costo por Mortalidad más preciso ---
        costo_map = {'Pre-iniciador': val_pre_iniciador, 'Iniciador': val_iniciador, 'Engorde': val_engorde, 'Retiro': val_retiro}
        tabla_filtrada['Costo_Kg_Dia'] = tabla_filtrada['Fase_Alimento'].map(costo_map)
        tabla_filtrada['Cons_Diario_Ave_gr'] = tabla_filtrada['Cons_Acum_Ajustado'].diff().fillna(tabla_filtrada['Cons_Acum_Ajustado'].iloc[0])
        tabla_filtrada['Costo_Alimento_Diario_Ave'] = (tabla_filtrada['Cons_Diario_Ave_gr'] / 1000) * tabla_filtrada['Costo_Kg_Dia']
        tabla_filtrada['Costo_Alimento_Acum_Ave'] = tabla_filtrada['Costo_Alimento_Diario_Ave'].cumsum()
        tabla_filtrada['Mortalidad_Diaria'] = tabla_filtrada['Mortalidad_Acumulada'].diff().fillna(tabla_filtrada['Mortalidad_Acumulada'].iloc[0])
        costo_desperdicio = (tabla_filtrada['Mortalidad_Diaria'] * tabla_filtrada['Costo_Alimento_Acum_Ave']).sum()

        st.subheader("Indicadores de Eficiencia Clave")
        kpi_cols = st.columns(3)
        kpi_cols[0].metric("Costo Total por Kilo", f"${costo_total_kilo:,.2f}")
        kpi_cols[1].metric("Conversión Alimenticia", f"{conversion_alimenticia:,.3f}")
        kpi_cols[2].metric("Costo por Mortalidad", f"${costo_desperdicio:,.2f}", help="Costo del alimento consumido por las aves que murieron.")

        st.markdown("---")
        st.subheader("Análisis de Costos Detallado")
        kpi_data = {
            "Métrica": [
                "Aves Producidas", "Kilos Totales Producidos", "Consumo / Ave (gr)", "Peso / Ave (gr)",
                "Costo Alimento / Kilo ($)", "Costo Total / Kilo ($)",
                "Costo Total Alimento ($)", "Costo por Mortalidad ($)", "Costo Total de Producción ($)"
            ], "Valor": [
                aves_producidas, kilos_totales_producidos, consumo_total_objetivo_ave, peso_obj_final,
                costo_total_alimento / kilos_totales_producidos, costo_total_kilo,
                costo_total_alimento, costo_desperdicio, costo_total_lote
            ]
        }
        df_kpi = pd.DataFrame(kpi_data).set_index("Métrica")
        
        col1, col2 = st.columns(2)
        with col1:
            st.dataframe(style_kpi_df(df_kpi.iloc[:5]), use_container_width=True)
        with col2:
            st.dataframe(style_kpi_df(df_kpi.iloc[5:]), use_container_width=True)

        st.markdown("---")
        col1_graf, col2_graf = st.columns(2)
        with col1_graf:
            st.subheader("Gráfico de Crecimiento")
            fig, ax = plt.subplots(figsize=(6, 5))
            ax.plot(tabla_filtrada['Dia'], tabla_filtrada['Peso'], color='darkred', label='Peso de Referencia')
            ax.plot(tabla_filtrada['Dia'], tabla_filtrada['Peso_Estimado'], color='lightcoral', label='Peso Estimado')
            ax.plot(dia_obj, peso_obj_final, 'o', color='blue', markersize=8, label=f"Día {dia_obj:.0f}: {peso_obj_final:,.0f} gr")
            ax.legend()
            ax.set_xlabel("Día del Ciclo")
            ax.set_ylabel("Peso (gramos)")
            ax.grid(True, linestyle='--', alpha=0.6)
            st.pyplot(fig)
        with col2_graf:
            st.subheader("Participación de Costos")
            costo_alimento_kilo = costo_total_alimento / kilos_totales_producidos
            fig_pie, ax_pie = plt.subplots(figsize=(6, 5))
            sizes = [costo_alimento_kilo, costo_total_kilo - costo_alimento_kilo]
            labels = [f"Alimento\n${sizes[0]:,.2f}", f"Otros Costos\n${sizes[1]:,.2f}"]
            ax_pie.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=['darkred', 'lightcoral'])
            ax_pie.set_title(f"Costo Total por Kilo: ${costo_total_kilo:,.2f}")
            st.pyplot(fig_pie)
    else:
        st.warning("No se pueden calcular KPIs: kilos producidos o participación de alimento son cero.")

except Exception as e:
    st.error("Ocurrió un error inesperado durante el procesamiento.")
    st.exception(e)

finally:
    st.markdown("---")
    st.markdown("""
    <div style="background-color: #ffcccc; padding: 10px; border-radius: 5px;">
    <b>Nota de Responsabilidad:</b> ...
    </div>
    """, unsafe_allow_html=True)