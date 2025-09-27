# Contenido COMPLETO y ACTUALIZADO para: utils.py

import streamlit as st
import pandas as pd
import numpy as np

@st.cache_data
def load_data(file_path):
    """Carga datos desde un archivo CSV de forma robusta."""
    try:
        return pd.read_csv(file_path)
    except FileNotFoundError:
        # Este es el error que estás viendo
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

def style_kpi_df(df):
    """Aplica formato condicional a un DataFrame de KPIs de forma eficiente."""
    def formatter(val, metric_name):
        if "Conversión" in metric_name: return f"{val:,.3f}"
        if "($)" in metric_name: return f"${val:,.2f}"
        return f"{val:,.0f}"
    df_styled = df.copy()
    df_styled['Valor'] = [formatter(val, name) for name, val in df['Valor'].items()]
    return df_styled

def calcular_curva_mortalidad(dias_ciclo, total_mortalidad, tipo, porcentaje=50):
    """Genera un array de mortalidad acumulada según un escenario."""
    dias_ciclo = int(dias_ciclo)
    total_mortalidad = float(total_mortalidad)
    mortalidad_acumulada = np.zeros(dias_ciclo)
    if tipo == "Lineal (Uniforme)":
        mortalidad_acumulada = np.linspace(0, total_mortalidad, dias_ciclo)
    elif tipo == "Concentrada al Inicio (Semana 1)":
        dias_concentracion = min(7, dias_ciclo)
        mortalidad_inicial = total_mortalidad * (porcentaje / 100.0)
        mortalidad_restante = total_mortalidad - mortalidad_inicial
        curva_inicial = np.linspace(0, mortalidad_inicial, dias_concentracion)
        mortalidad_acumulada[:dias_concentracion] = curva_inicial
        if dias_ciclo > dias_concentracion:
            curva_restante = np.linspace(0, mortalidad_restante, dias_ciclo - dias_concentracion)
            mortalidad_acumulada[dias_concentracion:] = mortalidad_inicial + curva_restante
    elif tipo == "Concentrada al Final (Última Semana)":
        dias_concentracion = min(7, dias_ciclo)
        punto_inicio_final = dias_ciclo - dias_concentracion
        mortalidad_final_concentrada = total_mortalidad * (porcentaje / 100.0)
        mortalidad_previa = total_mortalidad - mortalidad_final_concentrada
        if punto_inicio_final > 0:
            curva_previa = np.linspace(0, mortalidad_previa, punto_inicio_final)
            mortalidad_acumulada[:punto_inicio_final] = curva_previa
        curva_final = np.linspace(0, mortalidad_final_concentrada, dias_concentracion)
        mortalidad_acumulada[punto_inicio_final:] = mortalidad_previa + curva_final
    return np.floor(mortalidad_acumulada)

# --- NUEVA FUNCIÓN CENTRALIZADA ---
def reconstruir_tabla_base(st_session_state, df_referencia, df_coeffs, df_coeffs_15):
    """
    Reconstruye la tabla base de proyecciones a partir de los parámetros guardados en la sesión.
    Devuelve la tabla truncada al peso objetivo y lista para simulaciones.
    """
    tabla = df_referencia[
        (df_referencia['RAZA'] == st_session_state.raza_seleccionada) &
        (df_referencia['SEXO'] == st_session_state.sexo_seleccionado)
    ].copy()

    if tabla.empty:
        return None

    tabla['Cons_Acum'] = clean_numeric_column(tabla['Cons_Acum'])
    tabla['Peso'] = clean_numeric_column(tabla['Peso'])
    factor_ajuste = 1 - (st_session_state.restriccion_programada / 100.0)
    tabla['Cons_Acum_Ajustado'] = tabla['Cons_Acum'] * factor_ajuste
    
    dias_1_14 = tabla['Dia'] <= 14
    dias_15_adelante = tabla['Dia'] >= 15
    tabla.loc[dias_1_14, 'Peso_Estimado'] = calcular_peso_estimado(tabla[dias_1_14], df_coeffs_15, st_session_state.raza_seleccionada, st_session_state.sexo_seleccionado)
    tabla.loc[dias_15_adelante, 'Peso_Estimado'] = calcular_peso_estimado(tabla[dias_15_adelante], df_coeffs, st_session_state.raza_seleccionada, st_session_state.sexo_seleccionado)
    tabla['Peso_Estimado'] *= (st_session_state.productividad / 100.0)
    
    return tabla