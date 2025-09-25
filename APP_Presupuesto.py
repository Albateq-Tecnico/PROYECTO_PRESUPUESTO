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
# --- FUNCIONES AUXILIARES (MEJORA: Centralizar la lógica) ---
# =============================================================================

@st.cache_data
def load_data(file_path):
    """
    Función optimizada para cargar datos desde un archivo CSV y guardarlos en caché.
    Maneja errores de forma robusta.
    """
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
    """
    Calcula el peso estimado usando coeficientes de regresión polinomial.
    Devuelve una serie de ceros si no encuentra coeficientes.
    """
    if coeffs_df is None:
        return pd.Series(0, index=data.index)
    
    coeffs_seleccion = coeffs_df[(coeffs_df['RAZA'] == raza) & (coeffs_df['SEXO'] == sexo)]
    
    if not coeffs_seleccion.empty:
        params = coeffs_seleccion.iloc[0]
        x = data['Cons_Acum_Ajustado']
        # y = b + c1*x + c2*x^2 + c3*x^3 + c4*x^4
        return (params['Intercept'] + params['Coef_1'] * x + params['Coef_2'] * (x**2) + 
                params['Coef_3'] * (x**3) + params['Coef_4'] * (x**4))
    
    st.warning(f"No se encontraron coeficientes de peso para {raza} - {sexo}. El peso estimado será 0.")
    return pd.Series(0, index=data.index)

def style_kpi_df(df):
    """Aplica formato condicional a un DataFrame de KPIs."""
    styler = df.style
    for metric in df.index:
        if metric == "Conversión Alimenticia":
            fmt = "{:,.3f}"
        elif "($)" in metric:
            fmt = "${:,.2f}"
        else:
            fmt = "{:,.0f}"
        styler = styler.format({"Valor": fmt}, subset=pd.IndexSlice[metric, :])
    return styler

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
fecha_llegada = st.sidebar.date_input("Fecha de llegada", date.today())
aves_programadas = st.sidebar.number_input("# Aves Programadas", min_value=0, value=10000, step=1000, format="%d")

# --- GENÉTICA (DINÁMICO) ---
st.sidebar.subheader("Línea Genética")
if df_referencia is not None:
    razas = sorted(df_referencia['RAZA'].unique())
    sexos = sorted(df_referencia['SEXO'].unique())
else:
    razas = ["ROSS 308 AP", "COBB", "HUBBARD", "ROSS"]
    sexos = ["MIXTO", "HEMBRA", "MACHO"]

raza_seleccionada = st.sidebar.selectbox("RAZA", razas)
sexo_seleccionado = st.sidebar.selectbox("SEXO", sexos)

# --- OBJETIVOS ---
st.sidebar.subheader("Objetivos del Lote")
peso_objetivo = st.sidebar.number_input("Peso Objetivo al mercado (gramos)", min_value=0, value=2500, step=50, format="%d")
mortalidad_objetivo = st.sidebar.number_input("Mortalidad Objetivo en %", min_value=0.0, max_value=100.0, value=5.0, step=0.5, format="%.2f")

# --- CONDICIONES DE GRANJA ---
st.sidebar.subheader("Condiciones de Granja")
tipo_granja = st.sidebar.radio("Tipo de GRANJA", ["TUNEL", "MEJORADA", "NATURAL"])
productividad_options = {"TUNEL": 100.0, "MEJORADA": 97.5, "NATURAL": 95.0}
productividad = st.sidebar.number_input("Productividad (%)", value=productividad_options[tipo_granja], min_value=0.0, max_value=110.0, step=0.1, format="%.2f", help=f"Productividad teórica: {productividad_options}")

asnm = st.sidebar.radio("Altitud (ASNM)", ["ALTA >2000 msnm", "MEDIA <2000 y >1000 msnm", "BAJA < 1000 msnm"])

# --- LÓGICA DE RESTRICCIÓN ---
st.sidebar.subheader("Programa de Alimentación")
restriccion_map = {"ALTA >2000 msnm": 20, "MEDIA <2000 y >1000 msnm": 10, "BAJA < 1000 msnm": 0}
max_restriccion = restriccion_map[asnm]
st.sidebar.info(f"Recomendación: Máxima restricción del {max_restriccion}%.")
restriccion_programada = st.sidebar.number_input("% Restricción Programado", min_value=0, max_value=100, value=max_restriccion, step=1, format="%d")

if restriccion_programada > max_restriccion:
    st.sidebar.warning(f"Advertencia: La restricción ({restriccion_programada}%) supera el {max_restriccion}% recomendado para esta altitud.")

# --- CONSUMOS PROGRAMADOS ---
pre_iniciador = st.sidebar.number_input("Pre-iniciador (gramos/ave)", 0, 300, 150, 10, format="%d")
iniciador = st.sidebar.number_input("Iniciador (gramos/ave)", 1, 2000, 1200, 10, format="%d")
retiro = st.sidebar.number_input("Retiro (gramos/ave)", 0, 2000, 500, 10, format="%d")
st.sidebar.markdown("_El **Engorde** se calcula por diferencia._")

# --- UNIDADES Y COSTOS ---
st.sidebar.subheader("Unidades y Costos")
unidades_calculo = st.sidebar.selectbox("Unidades de Cálculo para Alimento", ["Kilos", "Bultos x 40 Kilos"])
val_pre_iniciador = st.sidebar.number_input("Costo Pre-iniciador ($/Kg)", 0.0, value=2200.0, step=0.01, format="%.2f")
val_iniciador = st.sidebar.number_input("Costo Iniciador ($/Kg)", 0.0, value=2200.0, step=0.01, format="%.2f")
val_engorde = st.sidebar.number_input("Costo Engorde ($/Kg)", 0.0, value=2200.0, step=0.01, format="%.2f")
val_retiro = st.sidebar.number_input("Costo Retiro ($/Kg)", 0.0, value=2200.0, step=0.01, format="%.2f")
porcentaje_participacion_alimento = st.sidebar.number_input("Participación del Alimento en Costo Total (%)", 0.0, 100.0, 65.0, 0.01, format="%.2f")

# =============================================================================
# --- ÁREA PRINCIPAL ---
# =============================================================================

st.title("🐔 Presupuesto Avícola")
st.markdown("---")

# --- MEJORA: CLÁUSULAS DE GUARDA PARA DETENER LA EJECUCIÓN SI LOS DATOS SON INVÁLIDOS ---
if df_referencia is None:
    st.error("No se pueden mostrar resultados porque el archivo de referencia principal no se cargó.")
    st.stop()

if aves_programadas <= 0 or peso_objetivo <= 0:
    st.info("👈 Ingrese un número de 'Aves Programadas' y un 'Peso Objetivo' mayores a 0 en el panel lateral para ver los resultados.")
    st.stop()

# --- MEJORA: MANEJO DE ERRORES CENTRALIZADO PARA TODA LA LÓGICA DE CÁLCULO ---
try:
    # 1. FILTRAR DATOS Y PREPARAR TABLA
    tabla_filtrada = df_referencia[
        (df_referencia['RAZA'] == raza_seleccionada) &
        (df_referencia['SEXO'] == sexo_seleccionado)
    ].copy()

    if tabla_filtrada.empty:
        st.warning(f"No se encontraron datos de referencia para la combinación de {raza_seleccionada} y {sexo_seleccionado}.")
        st.stop()
    
    st.header("Resultados del Presupuesto")
    
    # MEJORA: Usar función auxiliar para limpiar columnas
    tabla_filtrada['Cons_Acum'] = clean_numeric_column(tabla_filtrada['Cons_Acum'])
    tabla_filtrada['Peso'] = clean_numeric_column(tabla_filtrada['Peso'])

    # 2. CÁLCULOS SECUENCIALES
    # Ajustar consumo por restricción
    factor_ajuste = 1 - (restriccion_programada / 100.0)
    tabla_filtrada['Cons_Acum_Ajustado'] = tabla_filtrada['Cons_Acum'] * factor_ajuste

    # Calcular peso estimado
    dias_1_14 = tabla_filtrada['Dia'] <= 14
    dias_15_adelante = tabla_filtrada['Dia'] >= 15
    tabla_filtrada.loc[dias_1_14, 'Peso_Estimado'] = calcular_peso_estimado(tabla_filtrada[dias_1_14], df_coeffs_15, raza_seleccionada, sexo_seleccionado)
    tabla_filtrada.loc[dias_15_adelante, 'Peso_Estimado'] = calcular_peso_estimado(tabla_filtrada[dias_15_adelante], df_coeffs, raza_seleccionada, sexo_seleccionado)
    tabla_filtrada['Peso_Estimado'] *= (productividad / 100.0)

    # Encontrar punto objetivo y truncar la tabla
    closest_idx = (tabla_filtrada['Peso_Estimado'] - peso_objetivo).abs().idxmin()
    tabla_filtrada = tabla_filtrada.loc[:closest_idx].copy()

    # Asignar fase de alimento
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
    
    # Calcular saldo de aves (mortalidad)
    dias_ciclo = tabla_filtrada.loc[closest_idx, 'Dia']
    total_mortalidad_aves = aves_programadas * (mortalidad_objetivo / 100.0)
    mortalidad_diaria = total_mortalidad_aves / dias_ciclo if dias_ciclo > 0 else 0
    tabla_filtrada['Mortalidad_Acumulada'] = (tabla_filtrada['Dia'] * mortalidad_diaria).apply(np.floor)
    tabla_filtrada['Saldo'] = aves_programadas - tabla_filtrada['Mortalidad_Acumulada']

    # Calcular fecha y consumo total (Kilos o Bultos)
    tabla_filtrada['Fecha'] = tabla_filtrada['Dia'].apply(lambda d: fecha_llegada + timedelta(days=d - 1))
    
    if unidades_calculo == "Kilos":
        total_col, daily_col = "Kilos Totales", "Kilos Diarios"
        tabla_filtrada[total_col] = (tabla_filtrada['Cons_Acum_Ajustado'] * tabla_filtrada['Saldo']) / 1000
    else:
        total_col, daily_col = "Bultos Totales", "Bultos Diarios"
        tabla_filtrada[total_col] = np.ceil((tabla_filtrada['Cons_Acum_Ajustado'] * tabla_filtrada['Saldo']) / 40000)
    
    tabla_filtrada[daily_col] = tabla_filtrada[total_col].diff().fillna(tabla_filtrada[total_col])

    # 3. VISUALIZACIONES
    # Tabla principal
    st.subheader(f"Tabla de Proyección para {aves_programadas} aves ({raza_seleccionada} - {sexo_seleccionado})")
    columnas_a_mostrar = ['Dia', 'Fecha', 'Saldo', 'Cons_Acum', 'Cons_Acum_Ajustado', 'Peso', 'Peso_Estimado', daily_col, total_col, 'Fase_Alimento']
    format_dict = {col: "{:,.0f}" for col in columnas_a_mostrar if col not in ['Fecha', 'Fase_Alimento']}
    
    styler = tabla_filtrada[columnas_a_mostrar].style.format(format_dict)
    styler.apply(lambda row: ['background-color: #ffcccc' if row.name == closest_idx else '' for _ in row], axis=1)
    st.dataframe(styler.hide(axis="index"), use_container_width=True)
    
    # Gráfico de crecimiento
    st.subheader("Gráfico de Crecimiento: Peso de Referencia vs. Peso Estimado")
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(tabla_filtrada['Dia'], tabla_filtrada['Peso'], color='darkred', label='Peso de Referencia')
    ax.plot(tabla_filtrada['Dia'], tabla_filtrada['Peso_Estimado'], color='lightcoral', label='Peso Estimado')
    
    dia_obj = tabla_filtrada.loc[closest_idx, 'Dia']
    peso_obj = tabla_filtrada.loc[closest_idx, 'Peso_Estimado']
    cons_obj = tabla_filtrada.loc[closest_idx, 'Cons_Acum_Ajustado']
    
    ax.plot(dia_obj, peso_obj, 'o', color='blue', markersize=8, label=f"Día {dia_obj:.0f}: {peso_obj:,.0f} gr")
    leyenda_texto = f"Edad: {dia_obj:.0f} días\nPeso: {peso_obj:,.0f} gr\nConsumo: {cons_obj:,.0f} gr"
    ax.text(0.05, 0.95, leyenda_texto, transform=ax.transAxes, verticalalignment='top', bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.5))
    
    ax.legend()
    ax.set_xlabel("Día del Ciclo")
    ax.set_ylabel("Peso (gramos)")
    ax.grid(True, linestyle='--', alpha=0.6)
    st.pyplot(fig)

    # --- 4. ANÁLISIS ECONÓMICO Y RESUMEN (MEJORA: Flujo unificado) ---
    st.subheader("Resumen del Presupuesto de Alimento")
    factor_kg = 1 if unidades_calculo == "Kilos" else 40
    consumo_por_fase = tabla_filtrada.groupby('Fase_Alimento')[daily_col].sum()
    
    # Consumo y costo por fase
    fases = ['Pre-iniciador', 'Iniciador', 'Engorde', 'Retiro']
    unidades = [consumo_por_fase.get(f, 0) for f in fases]
    costos_kg = [val_pre_iniciador, val_iniciador, val_engorde, val_retiro]
    costos = [(u * factor_kg) * c for u, c in zip(unidades, costos_kg)]

    # DataFrame de Resumen
    df_resumen = pd.DataFrame({
        "Fase de Alimento": fases + ["Total"],
        f"Consumo ({unidades_calculo})": unidades + [sum(unidades)],
        "Valor del Alimento ($)": costos + [sum(costos)]
    })
    styler_resumen = df_resumen.style.format({f"Consumo ({unidades_calculo})": "{:,.0f}", "Valor del Alimento ($)": "${:,.2f}"})
    st.dataframe(styler_resumen.hide(axis="index"), use_container_width=True)

    # KPIs económicos
    st.subheader("Indicadores Clave de Desempeño (KPIs)")
    costo_total_alimento = sum(costos)
    aves_producidas = tabla_filtrada.loc[closest_idx, 'Saldo']
    kilos_totales_producidos = (aves_producidas * peso_obj) / 1000
    consumo_total_kg = sum(unidades) * factor_kg
    
    if kilos_totales_producidos > 0 and porcentaje_participacion_alimento > 0:
        costo_total_lote = costo_total_alimento / (porcentaje_participacion_alimento / 100)
        
        # Crear el DataFrame completo de KPIs
        kpi_data = {
            "Métrica": [
                "Aves Producidas", "Kilos Totales Producidos", "Consumo / Ave (gr)", "Peso / Ave (gr)",
                "Conversión Alimenticia", "Costo Alimento / Ave ($)", "Costo Alimento / Kilo ($)",
                "Costo Total / Ave ($)", "Costo Total / Kilo ($)", "Costo Total del Lote ($)"
            ],
            "Valor": [
                aves_producidas, kilos_totales_producidos, consumo_total_objetivo_ave, peso_obj,
                (consumo_total_kg / kilos_totales_producidos) if kilos_totales_producidos > 0 else 0,
                (costo_total_alimento / aves_producidas) if aves_producidas > 0 else 0,
                (costo_total_alimento / kilos_totales_producidos) if kilos_totales_producidos > 0 else 0,
                (costo_total_lote / aves_producidas) if aves_producidas > 0 else 0,
                (costo_total_lote / kilos_totales_producidos) if kilos_totales_producidos > 0 else 0,
                costo_total_lote
            ]
        }
        df_kpi = pd.DataFrame(kpi_data).set_index("Métrica")

        # Dividir KPIs en dos columnas para mejor visualización
        num_kpis = len(df_kpi)
        mid_point = (num_kpis + 1) // 2
        df_kpi1 = df_kpi.iloc[:mid_point]
        df_kpi2 = df_kpi.iloc[mid_point:]

        col1, col2 = st.columns(2)

        with col1:
            st.dataframe(style_kpi_df(df_kpi1), use_container_width=True)

        with col2:
            if not df_kpi2.empty:
                st.dataframe(style_kpi_df(df_kpi2), use_container_width=True)

        # Gráfico de participación de costos
        st.subheader("Participación de Costos por Kilo Producido")
        costo_alimento_kilo = costo_total_alimento / kilos_totales_producidos
        costo_total_kilo = costo_total_lote / kilos_totales_producidos
        
        fig_pie, ax_pie = plt.subplots(figsize=(4, 3))
        sizes = [costo_alimento_kilo, costo_total_kilo - costo_alimento_kilo]
        labels = [f"Alimento\n${s:,.2f}" for s in sizes]
        ax_pie.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=['darkred', 'lightcoral'])
        ax_pie.set_title(f"Costo Total por Kilo: ${costo_total_kilo:,.2f}")
        st.pyplot(fig_pie)
    else:
        st.warning("No se pueden calcular los KPIs porque los kilos producidos o la participación del alimento son cero.")

# MEJORA: Este bloque capturará cualquier error no previsto y mostrará un mensaje útil.
except Exception as e:
    st.error("Ocurrió un error inesperado durante el procesamiento de los datos.")
    st.exception(e)  # Esto es muy útil para depurar en la terminal

finally:
    # Este bloque se ejecuta siempre, asegurando que la nota de responsabilidad aparezca.
    st.markdown("---")
    st.markdown("""
    <div style="background-color: #ffcccc; padding: 10px; border-radius: 5px;">
    <b>Nota de Responsabilidad:</b> Esta es una herramienta de apoyo para uso en granja...
    </div>
    """, unsafe_allow_html=True)