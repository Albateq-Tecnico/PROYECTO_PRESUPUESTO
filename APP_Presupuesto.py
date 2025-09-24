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

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Presupuesto Avícola",
    page_icon="🐔",
    layout="wide",
)

# --- DEFINIR RUTA BASE PARA ACCEDER A LOS ARCHIVOS ---
BASE_DIR = Path(__file__).resolve().parent

# --- CARGA DE DATOS CON CACHÉ ---
@st.cache_data
def load_data(file_path, separator=','):
    # Cache buster: 1
    """
    Función para cargar datos desde un archivo CSV y guardarlos en caché.
    Maneja errores si el archivo no se encuentra.
    """
    try:
        df = pd.read_csv(file_path, sep=separator)
        return df
    except FileNotFoundError:
        st.error(f"Error: No se encontró el archivo en la ruta: {file_path}")
        return None
    except Exception as e:
        st.error(f"Error al cargar o procesar el archivo {file_path}: {e}")
        return None

# Cargar los DataFrames usando rutas absolutas
print("--- DEBUG: Loading df_coeffs...", flush=True)
df_coeffs = load_data(BASE_DIR / "ARCHIVOS" / "Cons_Acum_Peso.csv")
print("--- DEBUG: df_coeffs loaded.", flush=True)

print("--- DEBUG: Loading df_coeffs_15...", flush=True)
df_coeffs_15 = load_data(BASE_DIR / "ARCHIVOS" / "Cons_Acum_Peso_15.csv")
print("--- DEBUG: df_coeffs_15 loaded.", flush=True)

print("--- DEBUG: Loading df_referencia...", flush=True)
df_referencia = load_data(BASE_DIR / "ARCHIVOS" / "ROSS_COBB_HUBBARD_2025.csv")
print("--- DEBUG: df_referencia loaded.", flush=True)

print("--- DEBUG: All dataframes loaded. Proceeding to render UI.", flush=True)

# --- PANEL LATERAL DE ENTRADAS (SIDEBAR) ---

st.sidebar.header("1. Valores de Entrada")

try:
    logo = Image.open(BASE_DIR / "ARCHIVOS" / "log_PEQ.png")
    st.sidebar.image(logo, width=150)
except FileNotFoundError:
    st.sidebar.warning("No se encontró el archivo del logo.")

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
    razas = ["ROSS 308 AP", "COBB", "HUBBARD", "ROSS"] # Fallback
    sexos = ["MIXTO", "HEMBRA", "MACHO"] # Fallback

raza_seleccionada = st.sidebar.selectbox("RAZA", razas)
sexo_seleccionado = st.sidebar.selectbox("SEXO", sexos)

# --- OBJETIVOS ---
st.sidebar.subheader("Objetivos del Lote")
peso_objetivo = st.sidebar.number_input("Peso Objetivo al mercado (gramos)", min_value=0, value=2500, step=50, format="%d")
mortalidad_objetivo = st.sidebar.number_input("Mortalidad Objetivo en %", min_value=0.0, max_value=100.0, value=5.0, step=0.5, format="%.2f")

# --- CONDICIONES DE GRANJA ---
st.sidebar.subheader("Condiciones de Granja")
tipo_granja = st.sidebar.radio("Tipo de GRANJA", ["TUNEL", "MEJORADA", "NATURAL"])
asnm = st.sidebar.radio("Altitud (ASNM)", ["ALTA >2000 msnm", "MEDIA <2000 y >1000 msnm", "BAJA < 1000 msnm"])

# --- LÓGICA DE RESTRICCIÓN ---
st.sidebar.subheader("Programa de Alimentación")
if asnm == "ALTA >2000 msnm":
    st.sidebar.info("Recomendación: Máxima restricción del 20%.")
    max_restriccion = 20
elif asnm == "MEDIA <2000 y >1000 msnm":
    st.sidebar.info("Recomendación: Máxima restricción del 10%.")
    max_restriccion = 10
else: # BAJA < 1000 msnm
    st.sidebar.info("Recomendación: No se recomienda restricción.")
    max_restriccion = 0

restriccion_programada = st.sidebar.number_input("% Restricción Programado", min_value=0, max_value=100, value=max_restriccion, step=1, format="%d")

if asnm == "ALTA >2000 msnm" and restriccion_programada > 20:
    st.sidebar.warning(f"Advertencia: La restricción ({restriccion_programada}%) supera el 20% recomendado.")
elif asnm == "MEDIA <2000 y >1000 msnm" and restriccion_programada > 10:
    st.sidebar.warning(f"Advertencia: La restricción ({restriccion_programada}%) supera el 10% recomendado.")
elif asnm == "BAJA < 1000 msnm" and restriccion_programada > 0:
    st.sidebar.warning(f"Advertencia: La restricción ({restriccion_programada}%) no es recomendada para esta altitud.")

# --- CONSUMOS PROGRAMADOS ---
pre_iniciador = st.sidebar.number_input("Pre-iniciador (gramos/ave)", min_value=0, max_value=300, value=150, step=10, format="%d")
iniciador = st.sidebar.number_input("Iniciador (gramos/ave)", min_value=1, max_value=2000, value=1200, step=10, format="%d")
retiro = st.sidebar.number_input("Retiro (gramos/ave)", min_value=0, max_value=2000, value=500, step=10, format="%d")
st.sidebar.markdown("_El **Engorde** se calcula por diferencia._")

# --- UNIDADES ---
st.sidebar.subheader("Configuración de Unidades")
unidades_calculo = st.sidebar.selectbox("Unidades de Cálculo para Alimento", ["Kilos", "Bultos x 40 Kilos"])

# --- COSTOS DE ALIMENTO ---
st.sidebar.subheader("Costos de Alimento ($/Kg)")
val_pre_iniciador = st.sidebar.number_input("Valor Pre-iniciador", min_value=0.0, value=2200.0, step=0.01, format="%.2f")
val_iniciador = st.sidebar.number_input("Valor Iniciador", min_value=0.0, value=2200.0, step=0.01, format="%.2f")
val_engorde = st.sidebar.number_input("Valor Engorde", min_value=0.0, value=2200.0, step=0.01, format="%.2f")
val_retiro = st.sidebar.number_input("Valor Retiro", min_value=0.0, value=2200.0, step=0.01, format="%.2f")


# --- ÁREA PRINCIPAL ---

st.markdown("""
<div style="background-color: #ffcccc; padding: 10px; border-radius: 5px;">
👈 Para empezar, despliegue el Panel de Control en la esquina superior izquierda para introducir los datos de la granja.
</div>
""", unsafe_allow_html=True)
try:
    logo = Image.open(BASE_DIR / "ARCHIVOS" / "log_PEQ.png")
    st.image(logo, width=150)
except FileNotFoundError:
    st.warning("No se encontró el archivo del logo.")

st.title("🐔 Presupuesto Avícola")
st.markdown("---")
st.header("Resultados del Presupuesto")


# --- FILTRAR Y MOSTRAR TABLA DE REFERENCIA ---
st.subheader(f"Tabla de Referencia para la {raza_seleccionada} y {sexo_seleccionado} con Peso Objetivo {peso_objetivo}")

if df_referencia is not None:
    # Filtrar el DataFrame basado en las selecciones de la barra lateral
    tabla_filtrada = df_referencia[
        (df_referencia['RAZA'] == raza_seleccionada) &
        (df_referencia['SEXO'] == sexo_seleccionado)
    ].copy() # Usar .copy() para evitar SettingWithCopyWarning más adelante

    # Calcular la nueva columna si la tabla no está vacía
    if not tabla_filtrada.empty:
        
        # --- ORDEN DE CÁLCULOS REESTRUCTURADO ---
        
        # 1. AJUSTAR CONSUMO POR RESTRICCIÓN
        factor_ajuste = 1 - (restriccion_programada / 100.0)
        if tabla_filtrada['Cons_Acum'].dtype == 'object':
            tabla_filtrada['Cons_Acum'] = pd.to_numeric(tabla_filtrada['Cons_Acum'].str.replace(',', '.'), errors='coerce')
        tabla_filtrada['Cons_Acum_Ajustado'] = tabla_filtrada['Cons_Acum'] * factor_ajuste

        # 2. CALCULAR PESO ESTIMADO (depende de Cons_Acum_Ajustado)
        tabla_filtrada['Peso_Estimado'] = 0.0
        def calcular_peso(data, coeffs_df, df_name):
            if coeffs_df is None: return pd.Series(0, index=data.index)
            coeffs_seleccion = coeffs_df[(coeffs_df['RAZA'] == raza_seleccionada) & (coeffs_df['SEXO'] == sexo_seleccionado)]
            if not coeffs_seleccion.empty:
                params = coeffs_seleccion.iloc[0]
                x = data['Cons_Acum_Ajustado']
                return (params['Intercept'] + params['Coef_1'] * x + params['Coef_2'] * (x**2) + params['Coef_3'] * (x**3) + params['Coef_4'] * (x**4))
            else: return pd.Series(0, index=data.index)
        
        dias_1_14 = tabla_filtrada['Dia'] <= 14
        dias_15_adelante = tabla_filtrada['Dia'] >= 15
        if dias_1_14.any():
             tabla_filtrada.loc[dias_1_14, 'Peso_Estimado'] = calcular_peso(tabla_filtrada[dias_1_14], df_coeffs_15, "Cons_Acum_Peso_15.csv")
        if dias_15_adelante.any():
            tabla_filtrada.loc[dias_15_adelante, 'Peso_Estimado'] = calcular_peso(tabla_filtrada[dias_15_adelante], df_coeffs, "Cons_Acum_Peso.csv")

        # 3. ASIGNAR FASE DE ALIMENTO (depende de Peso_Estimado para el consumo total)
        consumo_total_objetivo_ave = 0
        if peso_objetivo > 0 and 'Peso_Estimado' in tabla_filtrada.columns and tabla_filtrada['Peso_Estimado'].sum() > 0:
            df_interp = tabla_filtrada.drop_duplicates(subset=['Peso_Estimado']).sort_values('Peso_Estimado')
            consumo_total_objetivo_ave = np.interp(peso_objetivo, df_interp['Peso_Estimado'], df_interp['Cons_Acum_Ajustado'])

        limite_preiniciador = pre_iniciador
        limite_iniciador = pre_iniciador + iniciador
        limite_inicio_retiro = consumo_total_objetivo_ave - retiro if retiro > 0 and consumo_total_objetivo_ave > retiro else np.inf

        conditions = [
            tabla_filtrada['Cons_Acum_Ajustado'] <= limite_preiniciador,
            tabla_filtrada['Cons_Acum_Ajustado'].between(limite_preiniciador, limite_iniciador, inclusive='right'),
            tabla_filtrada['Cons_Acum_Ajustado'] > limite_inicio_retiro
        ]
        choices = ['Pre-iniciador', 'Iniciador', 'Retiro']
        tabla_filtrada['Fase_Alimento'] = np.select(conditions, choices, default='Engorde')

        # 4. MOSTRAR TABLA PRINCIPAL
        tabla_filtrada = tabla_filtrada[tabla_filtrada['Peso_Estimado'] <= peso_objetivo * 1.05]
        closest_idx = (tabla_filtrada['Peso_Estimado'] - peso_objetivo).abs().idxmin()

        # --- CÁLCULO DE SALDO DE AVES ---
        dias_ciclo = tabla_filtrada.loc[closest_idx, 'Dia']
        if dias_ciclo > 0 and aves_programadas > 0:
            total_mortalidad_aves = aves_programadas * (mortalidad_objetivo / 100.0)
            mortalidad_diaria = total_mortalidad_aves / dias_ciclo
            tabla_filtrada['Mortalidad_Acumulada'] = (tabla_filtrada['Dia'] * mortalidad_diaria).apply(np.floor).astype(int)
            tabla_filtrada['Saldo'] = (aves_programadas - tabla_filtrada['Mortalidad_Acumulada']).astype(int)
        else:
            tabla_filtrada['Mortalidad_Acumulada'] = 0
            tabla_filtrada['Saldo'] = aves_programadas
        
        # --- CÁLCULO DE FECHA ---
        tabla_filtrada['Fecha'] = tabla_filtrada['Dia'].apply(lambda dia: fecha_llegada + timedelta(days=dia - 1))

        # --- CÁLCULO DE CONSUMO TOTAL (Kilos o Bultos) ---
        if unidades_calculo == "Kilos":
            total_col_name = "Kilos Totales"
            daily_col_name = "Kilos Diarios"
            tabla_filtrada[total_col_name] = ((tabla_filtrada['Cons_Acum_Ajustado'] * tabla_filtrada['Saldo']) / 1000).round(0).astype(int)
            format_total = "{:,.0f}"
        else: # Bultos x 40 Kilos
            total_col_name = "Bultos Totales"
            daily_col_name = "Bultos Diarios"
            tabla_filtrada[total_col_name] = ((tabla_filtrada['Cons_Acum_Ajustado'] * tabla_filtrada['Saldo']) / 40000).apply(np.ceil).astype(int)
            format_total = "{:,.0f}"

        tabla_filtrada[daily_col_name] = tabla_filtrada[total_col_name].diff().fillna(tabla_filtrada[total_col_name]).astype(int)

        def highlight_closest(row):
            is_closest = row.name == closest_idx
            return ['background-color: #ffcccc' if is_closest else '' for _ in row]
        
        format_dict = {
            "Peso_Estimado": "{:,.0f}", 
            "Cons_Acum_Ajustado": "{:,.0f}", 
            "Peso": "{:,.0f}", 
            "Dia": "{:,.0f}", 
            "Cons_Acum": "{:,.0f}", 
            "Saldo": "{:,.0f}", 
            total_col_name: format_total,
            daily_col_name: "{:,.0f}"
        }

        columnas_a_mostrar = [
            'Dia', 'Fecha', 'Cons_Acum', 'Cons_Acum_Ajustado', 
            'Peso', 'Peso_Estimado', 'Saldo', daily_col_name, total_col_name, 'Fase_Alimento'
        ]
        styler = tabla_filtrada[columnas_a_mostrar].style.apply(highlight_closest, axis=1).format(format_dict)
        styler.set_table_styles([
            {'selector': 'tr:nth-child(even)', 'props': [('background-color', '#7D7D7D')]}
        ], overwrite=False)
        styler.hide(axis="index")
        st.dataframe(styler)

        # 5. MOSTRAR GRÁFICO
        st.subheader("Gráfico de Crecimiento: Peso de Referencia vs. Peso Estimado")
        if tabla_filtrada['Peso'].dtype == 'object':
            tabla_filtrada['Peso'] = pd.to_numeric(tabla_filtrada['Peso'].str.replace(',', '.'), errors='coerce')
        if 'Peso_Estimado' in tabla_filtrada.columns:
            # Crear el gráfico con Matplotlib
            fig, ax = plt.subplots()

            # Graficar las líneas con colores personalizados
            ax.plot(tabla_filtrada['Dia'], tabla_filtrada['Peso'], color='darkred', label='Peso de Referencia')
            ax.plot(tabla_filtrada['Dia'], tabla_filtrada['Peso_Estimado'], color='lightcoral', label='Peso Estimado')

            # Añadir leyenda, títulos, etc.
            ax.legend()
            ax.set_xlabel("Día")
            ax.set_ylabel("Peso (gramos)")
            ax.grid(True)

            # Añadir marca de agua
            try:
                from matplotlib.offsetbox import OffsetImage, AnnotationBbox
                logo_img = Image.open(BASE_DIR / "ARCHIVOS" / "log_PEQ.png")
                
                # Coordenadas de datos para la esquina inferior derecha de la imagen
                x_coord = tabla_filtrada['Dia'].max()
                y_coord = 1 

                imagebox = OffsetImage(logo_img, zoom=0.2, alpha=0.15)
                
                ab = AnnotationBbox(imagebox, (x_coord, y_coord),
                                    frameon=False,
                                    box_alignment=(1, 0)) # Alinear esquina inferior derecha
                ax.add_artist(ab)
            except (FileNotFoundError, ImportError):
                pass # No hacer nada si no se encuentra el logo

            # Mostrar el gráfico en Streamlit
            st.pyplot(fig)

        # 6. MOSTRAR RESUMEN DE PRESUPUESTO (AJUSTADO POR MORTALIDAD)
        st.subheader("Resumen del Presupuesto de Alimento")
        if aves_programadas > 0 and peso_objetivo > 0:
            
            if unidades_calculo == "Kilos":
                unidad_str = "Kilos"
                factor_conversion_a_kg = 1
            else:
                unidad_str = "Bultos x 40kg"
                factor_conversion_a_kg = 40

            if daily_col_name in tabla_filtrada.columns:
                consumo_por_fase = tabla_filtrada.groupby('Fase_Alimento')[daily_col_name].sum()
                
                pre_iniciador_unidades = consumo_por_fase.get('Pre-iniciador', 0)
                iniciador_unidades = consumo_por_fase.get('Iniciador', 0)
                engorde_unidades = consumo_por_fase.get('Engorde', 0)
                retiro_unidades = consumo_por_fase.get('Retiro', 0)
                total_unidades = consumo_por_fase.sum()

                # Convertir a Kilos para el cálculo de costos
                pre_iniciador_kg = pre_iniciador_unidades * factor_conversion_a_kg
                iniciador_kg = iniciador_unidades * factor_conversion_a_kg
                engorde_kg = engorde_unidades * factor_conversion_a_kg
                retiro_kg = retiro_unidades * factor_conversion_a_kg

                # Calcular costos
                costo_pre_iniciador = pre_iniciador_kg * val_pre_iniciador
                costo_iniciador = iniciador_kg * val_iniciador
                costo_engorde = engorde_kg * val_engorde
                costo_retiro = retiro_kg * val_retiro
                costo_total = costo_pre_iniciador + costo_iniciador + costo_engorde + costo_retiro

                resumen_data = {
                    "Fase de Alimento": ["Pre-iniciador", "Iniciador", "Engorde", "Retiro", "Total"],
                    f"Consumo Total ({unidad_str})": [pre_iniciador_unidades, iniciador_unidades, engorde_unidades, retiro_unidades, total_unidades],
                    "Valor del Alimento ($)": [costo_pre_iniciador, costo_iniciador, costo_engorde, costo_retiro, costo_total]
                }
                df_resumen_ajustado = pd.DataFrame(resumen_data)

                styler_resumen = df_resumen_ajustado.style.format({
                    f"Consumo Total ({unidad_str})": "{:,.0f}",
                    "Valor del Alimento ($)": "${:,.2f}"
                })
                styler_resumen.set_table_styles([
                    {'selector': 'tr:nth-child(even)', 'props': [('background-color', '#7D7D7D')]}
                ], overwrite=False)
                styler_resumen.hide(axis="index")
                st.dataframe(styler_resumen)
            else:
                st.warning("No se pudo calcular el resumen ajustado.")

        else:
            st.info("Ingrese un número de 'Aves Programadas' y un 'Peso Objetivo' mayores a 0 para calcular el presupuesto.")
    else:
        st.warning("No se encontraron datos de referencia para la combinación de RAZA y SEXO seleccionada.")
else:
    st.error("No se pueden mostrar datos de referencia porque el DataFrame 'df_referencia' no se cargó correctamente.")

st.markdown("---")

# --- VERIFICACIÓN DE DATOS CARGADOS ---
if st.checkbox("Mostrar datos crudos cargados para verificación"):
    st.subheader("1. Coeficientes de Peso (Cons_Acum_Peso.csv)")
    if df_coeffs is not None:
        st.dataframe(df_coeffs.head())

    st.subheader("2. Coeficientes de Peso 15 (Cons_Acum_Peso_15.csv)")
    if df_coeffs_15 is not None:
        st.dataframe(df_coeffs_15.head())

    st.subheader("3. Tabla de Referencia (ROSS_COBB_HUBBARD_2025.csv)")
    if df_referencia is not None:
        st.dataframe(df_referencia.head())

st.markdown("""
<div style="background-color: #ffcccc; padding: 10px; border-radius: 5px;">
Nota de Responsabilidad: Esta es una herramienta de apoyo para uso en granja. La utilización de los resultados es de su exclusiva responsabilidad. No sustituye la asesoría profesional y Albateq S.A. no se hace responsable por las decisiones tomadas con base en la información aquí presentada.
<br><br>
Desarrollado por la Dirección Técnica de Albateq dtecnico@albateq.com
</div>
""", unsafe_allow_html=True)