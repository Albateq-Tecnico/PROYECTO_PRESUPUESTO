# Contenido COMPLETO y CORREGIDO para la página de Optimización

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from PIL import Image
from datetime import timedelta # <-- CORRECCIÓN: Se añadió la importación que faltaba
from utils import load_data, reconstruir_tabla_base

st.set_page_config(page_title="Optimizador de Costos", page_icon="💡", layout="wide")

# --- LOGO EN SIDEBAR ---
BASE_DIR = Path(__file__).resolve().parent.parent 
try:
    logo = Image.open(BASE_DIR / "ARCHIVOS" / "log_PEQ.png")
    st.sidebar.image(logo, width=150)
except Exception:
    st.sidebar.warning("Logo no encontrado.")
st.sidebar.markdown("---")

st.title("💡 Optimizador de Costo por Kilo")
st.markdown("""
Esta herramienta analiza el ciclo productivo día por día para identificar el momento exacto en que se alcanza el **costo por kilogramo más bajo**. 
Permite tomar decisiones informadas sobre la edad óptima de sacrificio para maximizar la rentabilidad.
""")

if 'aves_programadas' not in st.session_state or st.session_state.aves_programadas <= 0:
    st.warning("👈 Por favor, ejecuta un cálculo en la página '1_Presupuesto_Principal' primero.")
    st.stop()

# --- Cargar y reconstruir datos base ---
try:
    df_referencia = load_data(BASE_DIR / "ARCHIVOS" / "ROSS_COBB_HUBBARD_2025.csv")
    df_coeffs = load_data(BASE_DIR / "ARCHIVOS" / "Cons_Acum_Peso.csv")
    df_coeffs_15 = load_data(BASE_DIR / "ARCHIVOS" / "Cons_Acum_Peso_15.csv")
    
    tabla_base_completa = reconstruir_tabla_base(st.session_state, df_referencia, df_coeffs, df_coeffs_15)

    if tabla_base_completa is None:
        st.error("No se pudieron generar los datos base para la simulación.")
        st.stop()
    
    tabla_base_completa = tabla_base_completa[tabla_base_completa['Dia'] <= 50].copy()

    df_interp = tabla_base_completa.drop_duplicates(subset=['Peso_Estimado']).sort_values('Peso_Estimado')
    consumo_total_objetivo_ave = np.interp(st.session_state.peso_objetivo, df_interp['Peso_Estimado'], df_interp['Cons_Acum_Ajustado'])
    
    # --- BUCLE DE OPTIMIZACIÓN ---
    resultados_optimizacion = []
    
    costo_total_pollitos = st.session_state.aves_programadas * st.session_state.costo_pollito
    costo_total_otros = st.session_state.aves_programadas * st.session_state.otros_costos_ave
    costos_kg_map = {
        'Pre-iniciador': st.session_state.val_pre_iniciador, 'Iniciador': st.session_state.val_iniciador,
        'Engorde': st.session_state.val_engorde, 'Retiro': st.session_state.val_retiro
    }

    dia_ciclo_final_objetivo = (tabla_base_completa['Peso_Estimado'] - st.session_state.peso_objetivo).abs().idxmin()
    dia_obj_final = tabla_base_completa.loc[dia_ciclo_final_objetivo, 'Dia'] if dia_ciclo_final_objetivo else len(tabla_base_completa)
    
    for dia in range(1, len(tabla_base_completa) + 1):
        tabla_dia = tabla_base_completa.iloc[:dia].copy()
        
        consumo_actual_ave = tabla_dia['Cons_Acum_Ajustado'].iloc[-1]
        limite_pre = st.session_state.pre_iniciador
        limite_ini = st.session_state.pre_iniciador + st.session_state.iniciador
        limite_ret = consumo_total_objetivo_ave - st.session_state.retiro if st.session_state.retiro > 0 else np.inf
        conditions = [
            tabla_dia['Cons_Acum_Ajustado'] <= limite_pre,
            tabla_dia['Cons_Acum_Ajustado'].between(limite_pre, limite_ini, inclusive='right'),
            tabla_dia['Cons_Acum_Ajustado'] > limite_ret
        ]
        choices = ['Pre-iniciador', 'Iniciador', 'Retiro']
        tabla_dia['Fase_Alimento'] = np.select(conditions, choices, default='Engorde')
        
        total_mortalidad_aves = st.session_state.aves_programadas * (st.session_state.mortalidad_objetivo / 100.0)
        mortalidad_diaria_prom = total_mortalidad_aves / dia_obj_final if dia_obj_final > 0 else 0
        
        tabla_dia['Mortalidad_Acumulada'] = (tabla_dia['Dia'] * mortalidad_diaria_prom).apply(np.floor)
        tabla_dia['Saldo'] = st.session_state.aves_programadas - tabla_dia['Mortalidad_Acumulada']

        tabla_dia['Cons_Diario_Ave_gr'] = tabla_dia['Cons_Acum_Ajustado'].diff().fillna(tabla_dia['Cons_Acum_Ajustado'].iloc[0])
        tabla_dia['Kilos_Diarios_Lote'] = (tabla_dia['Cons_Diario_Ave_gr'] * tabla_dia['Saldo']) / 1000
        
        consumo_total_kg = tabla_dia['Kilos_Diarios_Lote'].sum()
        
        aves_producidas = tabla_dia['Saldo'].iloc[-1]
        peso_final_real = tabla_dia['Peso_Estimado'].iloc[-1]
        kilos_producidos = (aves_producidas * peso_final_real) / 1000
        
        if kilos_producidos > 0:
            consumo_por_fase = tabla_dia.groupby('Fase_Alimento')['Kilos_Diarios_Lote'].sum()
            costo_total_alimento = sum(consumo_por_fase.get(f, 0) * costos_kg_map.get(f, 0) for f in consumo_por_fase.index)

            costo_total_lote = costo_total_alimento + costo_total_pollitos + costo_total_otros
            
            resultados_optimizacion.append({
                'Dia': dia,
                'Fecha': st.session_state.fecha_llegada + timedelta(days=dia - 1),
                'Saldo': int(aves_producidas),
                '% Mortalidad Acumulada': (st.session_state.aves_programadas - aves_producidas) / st.session_state.aves_programadas,
                'Consumo_Acumulado_Ajustado': int(consumo_actual_ave),
                '% Consumo vs Consumo Guia': consumo_actual_ave / tabla_dia['Cons_Acum'].iloc[-1],
                'Peso Guia': int(tabla_dia['Peso'].iloc[-1]),
                'Peso Esperado': int(peso_final_real),
                'Conversion': consumo_total_kg / kilos_producidos,
                'Diferencia Genetica': peso_final_real - tabla_dia['Peso'].iloc[-1],
                'Costo Alimento x Kilo': costo_total_alimento / kilos_producidos,
                'Costo Pollito x Kilo': costo_total_pollitos / kilos_producidos,
                'Otros Costos x Kilo': costo_total_otros / kilos_producidos,
                'Total Costo x Kilo': costo_total_lote / kilos_producidos
            })

    if resultados_optimizacion:
        df_opt = pd.DataFrame(resultados_optimizacion)
        
        idx_min_costo = df_opt['Total Costo x Kilo'].idxmin()
        dia_optimo = df_opt.loc[idx_min_costo, 'Dia']
        costo_optimo = df_opt.loc[idx_min_costo, 'Total Costo x Kilo']
        peso_optimo = df_opt.loc[idx_min_costo, 'Peso Esperado']

        st.header("Punto Óptimo de Sacrificio")
        c1, c2, c3 = st.columns(3)
        c1.metric("Día Óptimo", f"{dia_optimo:.0f}")
        c2.metric("Peso en Día Óptimo", f"{peso_optimo:,.0f} gr")
        c3.metric("Costo Mínimo por Kilo", f"${costo_optimo:,.2f}")
        
        st.header("Análisis de Optimización Día por Día")

        def highlight_min(s):
            is_min = s == s.min()
            return ['background-color: #A9DFBF' if v else '' for v in is_min]

        st.dataframe(
            df_opt.style
            .format({
                'Fecha': '{:%Y-%m-%d}', '% Mortalidad Acumulada': '{:.2%}',
                '% Consumo vs Consumo Guia': '{:.2%}', 'Conversion': '{:.3f}',
                'Diferencia Genetica': '{:+.0f} gr', 'Costo Alimento x Kilo': '${:,.2f}',
                'Costo Pollito x Kilo': '${:,.2f}', 'Otros Costos x Kilo': '${:,.2f}',
                'Total Costo x Kilo': '${:,.2f}'
            })
            .apply(highlight_min, subset=['Total Costo x Kilo'])
        )
        
        st.header("Gráfico de Evolución de Costos")
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        ax.plot(df_opt['Dia'], df_opt['Costo Alimento x Kilo'], label='Costo Alimento/Kilo', color='green')
        ax.plot(df_opt['Dia'], df_opt['Costo Pollito x Kilo'], label='Costo Pollito/Kilo', color='orange')
        ax.plot(df_opt['Dia'], df_opt['Otros Costos x Kilo'], label='Otros Costos/Kilo', color='gray')
        ax.plot(df_opt['Dia'], df_opt['Total Costo x Kilo'], label='Costo TOTAL/Kilo', color='red', linewidth=3)

        ax.plot(dia_optimo, costo_optimo, 'o', markersize=12, color='blue', label=f"Punto Óptimo (Día {dia_optimo})")
        ax.annotate(
            f"Costo Mínimo: ${costo_optimo:,.0f}\nPeso: {peso_optimo:,.0f} gr",
            xy=(dia_optimo, costo_optimo),
            xytext=(dia_optimo + 1, costo_optimo + 50),
            arrowprops=dict(facecolor='black', shrink=0.05),
            bbox=dict(boxstyle="round,pad=0.3", fc="yellow", ec="black", lw=1, alpha=0.8)
        )
        
        from matplotlib.ticker import StrMethodFormatter
        ax.yaxis.set_major_formatter(StrMethodFormatter('${x:,.0f}'))
        ax.set_xlabel("Día del Ciclo")
        ax.set_ylabel("Costo por Kilo Producido ($)")
        ax.set_title("Evolución del Costo por Kilo a Lo Largo del Ciclo")
        ax.legend()
        ax.grid(True, linestyle='--', alpha=0.6)
        
        try:
            from matplotlib.offsetbox import OffsetImage, AnnotationBbox
            logo_img_f = Image.open(BASE_DIR / "ARCHIVOS" / "log_PEQ.png")
            imagebox = OffsetImage(logo_img_f, zoom=0.2, alpha=0.1)
            ab = AnnotationBbox(imagebox, (0.5, 0.5), xycoords='axes fraction', frameon=False, box_alignment=(0.5, 0.5), zorder=-1)
            ax.add_artist(ab)
        except Exception:
            pass

        st.pyplot(fig)

    else:
        st.warning("No se pudieron generar los datos para la optimización.")

except Exception as e:
    st.error(f"Ocurrió un error al procesar la página de optimización.")
    st.exception(e)
