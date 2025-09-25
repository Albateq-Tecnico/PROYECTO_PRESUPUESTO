import streamlit as st
import pandas as pd
import numpy as np

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
