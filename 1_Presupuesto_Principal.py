# Contenido COMPLETO y FINAL para: 1_Presupuesto_Principal.py

import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
from PIL import Image
from datetime import datetime
from utils import load_data, clean_numeric_column, calcular_peso_estimado, calcular_curva_mortalidad, reconstruir_tabla_base

st.set_page_config(page_title="Presupuesto Principal", page_icon="🐔", layout="wide")

# --- LOGO EN SIDEBAR ---
BASE_DIR = Path(__file__).resolve().parent.parent 
try:
    logo = Image.open(BASE_DIR / "ARCHIVOS" / "log_PEQ.png")
    st.sidebar.image(logo, width=150)
except Exception:
    st.sidebar.warning("Logo no encontrado.")
st.sidebar.markdown("---")

st.sidebar.header("Parámetros del Presupuesto")

# --- ENTRADAS DE USUARIO EN EL SIDEBAR ---
with st.sidebar.expander("Detalles del Lote", expanded=True):
    st.session_state.aves_programadas = clean_numeric_column(
        st.number_input("Número de Aves a Programar", value=10000, min_value=1)
    )
    st.session_state.raza = st.selectbox("Raza", ["COBB", "ROSS", "HUBBARD"], index=0)
    st.session_state.sexo = st.selectbox("Sexo", ["HEMBRA", "MACHO", "MIXTO"], index=0)
    st.session_state.fecha_llegada = st.date_input("Fecha de Llegada")
    st.session_state.peso_objetivo = clean_numeric_column(
        st.number_input("Peso Objetivo (gr)", value=2800, min_value=100)
    )
    st.session_state.mortalidad_objetivo = st.number_input("Mortalidad Objetivo (%)", value=4.0, min_value=0.0, max_value=100.0)

with st.sidebar.expander("Costos Directos", expanded=True):
    st.session_state.costo_pollito = clean_numeric_column(
        st.number_input("Costo por Pollito ($)", value=3200.0, min_value=0.0)
    )
    st.session_state.otros_costos_ave = clean_numeric_column(
        st.number_input("Otros Costos por Ave ($)", value=2500.0, min_value=0.0)
    )

with st.sidebar.expander("Programa de Alimentación (kg / ave)", expanded=False):
    st.session_state.pre_iniciador = clean_numeric_column(st.number_input("Pre-iniciador (kg)", value=0.5, min_value=0.0))
    st.session_state.iniciador = clean_numeric_column(st.number_input("Iniciador (kg)", value=1.5, min_value=0.0))
    st.session_state.engorde = clean_numeric_column(st.number_input("Engorde (kg)", value=3.0, min_value=0.0)) # Este valor se ajusta dinámicamente
    st.session_state.retiro = clean_numeric_column(st.number_input("Retiro (kg)", value=0.0, min_value=0.0))
    st.session_state.unidades_calculo = st.selectbox("Unidades para cálculo de alimento", ["Kilos", "Bultos (40kg)"], index=0)

with st.sidebar.expander("Costos de Alimento ($/kg)", expanded=False):
    st.session_state.val_pre_iniciador = clean_numeric_column(st.number_input("Costo Pre-iniciador ($/kg)", value=2500.0, min_value=0.0))
    st.session_state.val_iniciador = clean_numeric_column(st.number_input("Costo Iniciador ($/kg)", value=2300.0, min_value=0.0))
    st.session_state.val_engorde = clean_numeric_column(st.number_input("Costo Engorde ($/kg)", value=2100.0, min_value=0.0))
    st.session_state.val_retiro = clean_numeric_column(st.number_input("Costo Retiro ($/kg)", value=2200.0, min_value=0.0))

# --- BOTÓN DE GENERAR PRESUPUESTO ---
if st.sidebar.button("Generar Presupuesto", type="primary"):
    # --- Cargar datos de referencia ---
    df_referencia = load_data(BASE_DIR / "ARCHIVOS" / "ROSS_COBB_HUBBARD_2025.csv")
    df_coeffs = load_data(BASE_DIR / "ARCHIVOS" / "Cons_Acum_Peso.csv")
    df_coeffs_15 = load_data(BASE_DIR / "ARCHIVOS" / "Cons_Acum_Peso_15.csv")

    try:
        # Reconstruir la tabla base de la simulación
        tabla_base_completa = reconstruir_tabla_base(st.session_state, df_referencia, df_coeffs, df_coeffs_15)

        if tabla_base_completa is None or tabla_base_completa.empty:
            st.error("No se pudieron generar los datos base para la simulación. Verifique los parámetros.")
            st.session_state.resultados_base = {} # Limpiar resultados anteriores
        else:
            # Asegurar que los datos base están listos para la simulación
            df_interp = tabla_base_completa.drop_duplicates(subset=['Peso_Estimado']).sort_values('Peso_Estimado')
            consumo_total_objetivo_ave = np.interp(st.session_state.peso_objetivo, df_interp['Peso_Estimado'], df_interp['Cons_Acum_Ajustado'])
            
            # Ajustar Engorde para cumplir el peso objetivo
            consumo_acum_ajustado_final = tabla_base_completa['Cons_Acum_Ajustado'].iloc[-1]
            if consumo_acum_ajustado_final < consumo_total_objetivo_ave:
                st.session_state.engorde = consumo_total_objetivo_ave - (st.session_state.pre_iniciador + st.session_state.iniciador + st.session_state.retiro)
                if st.session_state.engorde < 0: st.session_state.engorde = 0 # Asegurar que no sea negativo
            
            # Recalcular tabla_base_completa con el engorde ajustado para que las fases sean consistentes
            tabla_base_completa = reconstruir_tabla_base(st.session_state, df_referencia, df_coeffs, df_coeffs_15)

            # Asignar Fases de Alimento
            limite_pre = st.session_state.pre_iniciador
            limite_ini = st.session_state.pre_iniciador + st.session_state.iniciador
            limite_ret = consumo_total_objetivo_ave - st.session_state.retiro if st.session_state.retiro > 0 else np.inf

            conditions = [
                tabla_base_completa['Cons_Acum_Ajustado'] <= limite_pre,
                tabla_base_completa['Cons_Acum_Ajustado'].between(limite_pre, limite_ini, inclusive='right'),
                tabla_base_completa['Cons_Acum_Ajustado'] > limite_ret
            ]
            choices = ['Pre-iniciador', 'Iniciador', 'Retiro']
            tabla_base_completa['Fase_Alimento'] = np.select(conditions, choices, default='Engorde')

            # Calcular Mortalidad (Curva Lineal por defecto para la base)
            dia_obj_final = tabla_base_completa['Dia'].iloc[-1]
            total_mortalidad_aves = st.session_state.aves_programadas * (st.session_state.mortalidad_objetivo / 100.0)
            
            # Usar la función de curva de mortalidad para el escenario LINEAL (base)
            mortalidad_acum = calcular_curva_mortalidad(dia_obj_final, total_mortalidad_aves, "Lineal (Uniforme)", 50)
            
            tabla_base_completa['Mortalidad_Acumulada'] = mortalidad_acum
            tabla_base_completa['Saldo'] = st.session_state.aves_programadas - tabla_base_completa['Mortalidad_Acumulada']

            # Calcular Consumo Diario y Total
            tabla_base_completa['Cons_Diario_Ave_gr'] = tabla_base_completa['Cons_Acum_Ajustado'].diff().fillna(tabla_base_completa['Cons_Acum_Ajustado'].iloc[0])
            
            if st.session_state.unidades_calculo == "Kilos":
                tabla_base_completa['Kilos_Diarios_Lote'] = (tabla_base_completa['Cons_Diario_Ave_gr'] * tabla_base_completa['Saldo']) / 1000
                consumo_total_kg = tabla_base_completa['Kilos_Diarios_Lote'].sum()
            else: # Bultos (40kg)
                tabla_base_completa['Bultos_Diarios_Lote'] = np.ceil((tabla_base_completa['Cons_Diario_Ave_gr'] * tabla_base_completa['Saldo']) / 40000)
                consumo_total_kg = tabla_base_completa['Bultos_Diarios_Lote'].sum() * 40 # Convertir bultos a kilos
            
            # Calcular Costos
            costos_kg_map = {
                'Pre-iniciador': st.session_state.val_pre_iniciador, 'Iniciador': st.session_state.val_iniciador,
                'Engorde': st.session_state.val_engorde, 'Retiro': st.session_state.val_retiro
            }
            
            if st.session_state.unidades_calculo == "Kilos":
                consumo_por_fase = tabla_base_completa.groupby('Fase_Alimento')['Kilos_Diarios_Lote'].sum()
            else:
                consumo_por_fase = tabla_base_completa.groupby('Fase_Alimento')['Bultos_Diarios_Lote'].sum() * 40 # Usar kilos para el costo

            costo_total_alimento = sum(consumo_por_fase.get(f, 0) * costos_kg_map.get(f, 0) for f in consumo_por_fase.index)
            costo_total_pollitos = st.session_state.aves_programadas * st.session_state.costo_pollito
            costo_total_otros = st.session_state.aves_programadas * st.session_state.otros_costos_ave
            costo_total_lote = costo_total_alimento + costo_total_pollitos + costo_total_otros

            aves_producidas = tabla_base_completa['Saldo'].iloc[-1]
            peso_final_real = tabla_base_completa['Peso_Estimado'].iloc[-1]
            kilos_producidos = (aves_producidas * peso_final_real) / 1000 if aves_producidas > 0 else 0

            # --- CÁLCULO DE COSTO DE MORTALIDAD para 'resultados_base' ---
            if kilos_producidos > 0:
                tabla_base_completa['Costo_Kg_Dia_Fase'] = tabla_base_completa['Fase_Alimento'].map(costos_kg_map)
                tabla_base_completa['Cons_Diario_Ave_Kg'] = tabla_base_completa['Cons_Diario_Ave_gr'] / 1000
                tabla_base_completa['Costo_Alimento_Diario_Ave'] = tabla_base_completa['Cons_Diario_Ave_Kg'] * tabla_base_completa['Costo_Kg_Dia_Fase']
                tabla_base_completa['Costo_Alimento_Acum_Ave'] = tabla_base_completa['Costo_Alimento_Diario_Ave'].cumsum()
                tabla_base_completa['Mortalidad_Diaria'] = tabla_base_completa['Mortalidad_Acumulada'].diff().fillna(tabla_base_completa['Mortalidad_Acumulada'].iloc[0])
                
                costo_alimento_desperdiciado = (tabla_base_completa['Mortalidad_Diaria'] * tabla_base_completa['Costo_Alimento_Acum_Ave']).sum()
                
                aves_muertas_total = st.session_state.aves_programadas - aves_producidas
                costo_pollitos_perdidos = aves_muertas_total * st.session_state.costo_pollito
                costo_otros_perdidos = aves_muertas_total * st.session_state.otros_costos_ave
                
                total_costo_mortalidad = costo_alimento_desperdiciado + costo_pollitos_perdidos + costo_otros_perdidos
                
                # Guardar todos los resultados, incluyendo los de mortalidad, en session_state
                st.session_state.resultados_base = {
                    "tabla_proyeccion": tabla_base_completa,
                    "kilos_producidos": kilos_producidos,
                    "conversion_alimenticia": consumo_total_kg / kilos_producidos if kilos_producidos > 0 else 0,
                    "costo_total_por_kilo": costo_total_lote / kilos_producidos if kilos_producidos > 0 else 0,
                    "costo_alimento_kilo": costo_total_alimento / kilos_producidos if kilos_producidos > 0 else 0,
                    "costo_pollito_kilo": costo_total_pollitos / kilos_producidos if kilos_producidos > 0 else 0,
                    "costo_otros_kilo": costo_otros_perdidos / kilos_producidos if kilos_producidos > 0 else 0,
                    "costo_total_mortalidad": total_costo_mortalidad,
                    "costo_alimento_mortalidad_total": costo_alimento_desperdiciado,
                    "costo_pollito_mortalidad_total": costo_pollitos_perdidos,
                    "costo_otros_mortalidad_total": costo_otros_perdidos,
                    "costo_alimento_mortalidad_kilo": costo_alimento_desperdiciado / kilos_producidos if kilos_producidos > 0 else 0,
                    "costo_pollito_mortalidad_kilo": costo_pollitos_perdidos / kilos_producidos if kilos_producidos > 0 else 0,
                    "costo_otros_mortalidad_kilo": costo_otros_perdidos / kilos_producidos if kilos_producidos > 0 else 0,
                }
            else:
                st.session_state.resultados_base = {}
                st.warning("No se pudieron producir kilos. Verifique los parámetros (mortalidad muy alta, etc.).")


    except Exception as e:
        st.error(f"Ocurrió un error al generar el presupuesto: {e}")
        st.exception(e)
        st.session_state.resultados_base = {} # Limpiar resultados en caso de error

# --- PANTALLA PRINCIPAL ---
st.title("🐔 Presupuesto Avícola")

if 'resultados_base' in st.session_state and st.session_state.resultados_base:
    resultados = st.session_state.resultados_base
    tabla_proyeccion = resultados['tabla_proyeccion']

    st.header("Resultados del Presupuesto")
    st.markdown(f"### Tabla de Proyección para {st.session_state.aves_programadas:,.0f} aves ({st.session_state.raza} - {st.session_state.sexo})")
    
    # Mostrar indicadores clave
    st.subheader("Indicadores de Eficiencia Clave")
    col1, col2, col3 = st.columns(3)
    col1.metric("Costo Total por Kilo", f"${resultados['costo_total_por_kilo']:,.2f}")
    col2.metric("Conversión Alimenticia", f"{resultados['conversion_alimenticia']:.3f}")
    col3.metric("Costo por Mortalidad", f"${resultados['costo_total_mortalidad']:,.2f}", help="Costo total de alimento, pollito y otros insumos perdidos debido a la mortalidad.")

    # Mostrar la tabla de proyección
    st.dataframe(
        tabla_proyeccion.style.format({
            'Fecha': '{:%Y-%m-%d}',
            'Saldo': '{:,.0f}',
            'Cons_Acum_Ajustado': '{:,.0f}',
            'Peso_Estimado': '{:,.0f}',
            'Kilos_Diarios_Lote': '{:,.0f}',
            'Kilos_Totales_Lote': '{:,.0f}'
        }),
        use_container_width=True
    )
    
    # Opcional: Mostrar resumen de fases
    st.subheader("Resumen de Consumo por Fase")
    if st.session_state.unidades_calculo == "Kilos":
        consumo_fases_df = tabla_proyeccion.groupby('Fase_Alimento')['Kilos_Diarios_Lote'].sum().reset_index()
        consumo_fases_df.rename(columns={'Kilos_Diarios_Lote': 'Kilos Totales'}, inplace=True)
        consumo_fases_df['Costo Total ($)'] = consumo_fases_df.apply(lambda row: row['Kilos Totales'] * st.session_state.get(f"val_{row['Fase_Alimento'].lower().replace('-', '_')}", 0), axis=1)
    else: # Bultos
        consumo_fases_df = tabla_proyeccion.groupby('Fase_Alimento')['Bultos_Diarios_Lote'].sum().reset_index()
        consumo_fases_df.rename(columns={'Bultos_Diarios_Lote': 'Bultos Totales'}, inplace=True)
        consumo_fases_df['Costo Total ($)'] = consumo_fases_df.apply(lambda row: (row['Bultos Totales'] * 40) * st.session_state.get(f"val_{row['Fase_Alimento'].lower().replace('-', '_')}", 0), axis=1)

    st.dataframe(consumo_fases_df.style.format({'Kilos Totales': '{:,.0f}', 'Bultos Totales': '{:,.0f}', 'Costo Total ($)': '${:,.2f}'}))

else:
    st.info("Utiliza los parámetros del panel lateral y haz clic en 'Generar Presupuesto' para comenzar.")
