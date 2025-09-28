# --- CONFIGURACIÓN DE PÁGINA ---
# Debe ser el primer comando de Streamlit
try:
    page_icon_image = Image.open(Path(__file__).resolve().parent / "ARCHIVOS" / "log_PEQ.png")
except FileNotFoundError:
    page_icon_image = "🐔"

st.set_page_config(
    page_title="Presupuesto Avícola",
    page_icon=page_icon_image, 
    layout="wide",
)

# --- DEFINICIÓN DE RUTAS Y CARGA DE DATOS ---
BASE_DIR = Path(__file__).resolve().parent
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
except Exception:
    st.sidebar.warning("Logo no encontrado.")

# ... (El resto del código del sidebar completo aquí, es igual al anterior)
st.sidebar.subheader("Datos del Lote")
st.session_state.aves_programadas = st.sidebar.number_input(...)
# ... etc.

st.sidebar.markdown("---")
if st.sidebar.button("Generar Presupuesto", type="primary", use_container_width=True):
    st.session_state.start_calculation = True

# =============================================================================
# --- ÁREA PRINCIPAL ---
# =============================================================================
st.title("🐔 Presupuesto Avícola")

if 'start_calculation' not in st.session_state or not st.session_state.start_calculation:
    st.info("👈 Para empezar, ajusta los parámetros en el Panel de Control y luego haz clic en 'Generar Presupuesto'.")
else:
    st.markdown("---")
    if st.session_state.aves_programadas <= 0 or st.session_state.peso_objetivo <= 0:
        st.error("Por favor, asegúrate de que las 'Aves Programadas' y el 'Peso Objetivo' sean mayores a cero.")
    else:
        try:
            # 1. FILTRAR DATOS Y CÁLCULOS BASE
            tabla_filtrada = df_referencia[
                (df_referencia['RAZA'] == st.session_state.raza_seleccionada) &
                (df_referencia['SEXO'] == st.session_state.sexo_seleccionado)
            ].copy()

            if tabla_filtrada.empty:
                st.warning(f"No se encontraron datos de referencia para {st.session_state.raza_seleccionada} - {st.session_state.sexo_seleccionado}.")
                st.stop()
            
            st.header("Resultados del Presupuesto")
            
            tabla_filtrada['Cons_Acum'] = clean_numeric_column(tabla_filtrada['Cons_Acum'])
            tabla_filtrada['Peso'] = clean_numeric_column(tabla_filtrada['Peso'])
            factor_ajuste = 1 - (st.session_state.restriccion_programada / 100.0)
            tabla_filtrada['Cons_Acum_Ajustado'] = tabla_filtrada['Cons_Acum'] * factor_ajuste

            dias_1_14 = tabla_filtrada['Dia'] <= 14
            dias_15_adelante = tabla_filtrada['Dia'] >= 15
            tabla_filtrada.loc[dias_1_14, 'Peso_Estimado'] = calcular_peso_estimado(tabla_filtrada[dias_1_14], df_coeffs_15, st.session_state.raza_seleccionada, st.session_state.sexo_seleccionado)
            tabla_filtrada.loc[dias_15_adelante, 'Peso_Estimado'] = calcular_peso_estimado(tabla_filtrada[dias_15_adelante], df_coeffs, st.session_state.raza_seleccionada, st.session_state.sexo_seleccionado)
            tabla_filtrada['Peso_Estimado'] *= (st.session_state.productividad / 100.0)

            closest_idx = (tabla_filtrada['Peso_Estimado'] - st.session_state.peso_objetivo).abs().idxmin()
            tabla_filtrada = tabla_filtrada.loc[:closest_idx].copy()
            
            df_interp = tabla_filtrada.drop_duplicates(subset=['Peso_Estimado']).sort_values('Peso_Estimado')
            consumo_total_objetivo_ave = np.interp(st.session_state.peso_objetivo, df_interp['Peso_Estimado'], df_interp['Cons_Acum_Ajustado'])
            
            limite_pre = st.session_state.pre_iniciador
            limite_ini = st.session_state.pre_iniciador + st.session_state.iniciador
            limite_ret = consumo_total_objetivo_ave - st.session_state.retiro if st.session_state.retiro > 0 else np.inf
            conditions = [
                tabla_filtrada['Cons_Acum_Ajustado'] <= limite_pre,
                tabla_filtrada['Cons_Acum_Ajustado'].between(limite_pre, limite_ini, inclusive='right'),
                tabla_filtrada['Cons_Acum_Ajustado'] > limite_ret
            ]
            choices = ['Pre-iniciador', 'Iniciador', 'Retiro']
            tabla_filtrada['Fase_Alimento'] = np.select(conditions, choices, default='Engorde')

            # 2. CÁLCULOS DE MORTALIDAD Y CONSUMO (ESCENARIO BASE: LINEAL)
            dia_obj = tabla_filtrada.loc[closest_idx, 'Dia']
            total_mortalidad_aves = st.session_state.aves_programadas * (st.session_state.mortalidad_objetivo / 100.0)
            mortalidad_diaria_prom = total_mortalidad_aves / dia_obj if dia_obj > 0 else 0
            tabla_filtrada['Mortalidad_Acumulada'] = (tabla_filtrada['Dia'] * mortalidad_diaria_prom).apply(np.floor)
            tabla_filtrada['Saldo'] = st.session_state.aves_programadas - tabla_filtrada['Mortalidad_Acumulada']
            tabla_filtrada['Fecha'] = tabla_filtrada['Dia'].apply(lambda d: st.session_state.fecha_llegada + timedelta(days=d - 1))
            
            tabla_filtrada['Cons_Diario_Ave_gr'] = tabla_filtrada['Cons_Acum_Ajustado'].diff().fillna(tabla_filtrada['Cons_Acum_Ajustado'].iloc[0])
            if st.session_state.unidades_calculo == "Kilos":
                daily_col = "Kilos Diarios"
                total_col = "Kilos Totales"
                tabla_filtrada[daily_col] = (tabla_filtrada['Cons_Diario_Ave_gr'] * tabla_filtrada['Saldo']) / 1000
            else:
                daily_col = "Bultos Diarios"
                total_col = "Bultos Totales"
                tabla_filtrada[daily_col] = np.ceil((tabla_filtrada['Cons_Diario_Ave_gr'] * tabla_filtrada['Saldo']) / 40000)
            tabla_filtrada[total_col] = tabla_filtrada[daily_col].cumsum()

            # 3. VISUALIZACIONES
            st.subheader(f"Tabla de Proyección para {st.session_state.aves_programadas} aves ({st.session_state.raza_seleccionada} - {st.session_state.sexo_seleccionado})")
            columnas_a_mostrar = ['Dia', 'Fecha', 'Saldo', 'Cons_Acum_Ajustado', 'Peso_Estimado', daily_col, total_col, 'Fase_Alimento']
            format_dict = {col: "{:,.0f}" for col in columnas_a_mostrar if col not in ['Fecha', 'Fase_Alimento']}
            styler = tabla_filtrada[columnas_a_mostrar].style.format(format_dict)
            styler.apply(lambda row: ['background-color: #ffcccc' if row.name == closest_idx else '' for _ in row], axis=1)
            st.dataframe(styler.hide(axis="index"), use_container_width=True)
            
            # 4. ANÁLISIS ECONÓMICO
            st.subheader("Resumen del Presupuesto de Alimento")
            consumo_por_fase = tabla_filtrada.groupby('Fase_Alimento')[daily_col].sum()
            
            fases = ['Pre-iniciador', 'Iniciador', 'Engorde', 'Retiro']
            unidades = [consumo_por_fase.get(f, 0) for f in fases]
            factor_kg = 1 if st.session_state.unidades_calculo == "Kilos" else 40
            costos_kg = [st.session_state.val_pre_iniciador, st.session_state.val_iniciador, st.session_state.val_engorde, st.session_state.val_retiro]
            
            costos = [(u * factor_kg) * c for u, c in zip(unidades, costos_kg)]
            costo_total_alimento = sum(costos)

            df_resumen = pd.DataFrame({
                "Fase de Alimento": fases + ["Total"],
                f"Consumo ({st.session_state.unidades_calculo})": unidades + [sum(unidades)],
                "Valor del Alimento ($)": costos + [costo_total_alimento]
            })
            styler_resumen = df_resumen.style.format({f"Consumo ({st.session_state.unidades_calculo})": "{:,.0f}", "Valor del Alimento ($)": "${:,.2f}"})
            st.dataframe(styler_resumen.hide(axis="index"), use_container_width=True)

            # --- CÁLCULO DE KPIS Y GUARDADO EN SESIÓN ---
            costo_total_pollitos = st.session_state.aves_programadas * st.session_state.costo_pollito
            costo_total_otros = st.session_state.aves_programadas * st.session_state.otros_costos_ave
            costo_total_lote = costo_total_alimento + costo_total_pollitos + costo_total_otros

            aves_producidas = tabla_filtrada['Saldo'].iloc[-1]
            peso_obj_final = tabla_filtrada['Peso_Estimado'].iloc[-1]
            kilos_totales_producidos = (aves_producidas * peso_obj_final) / 1000 if aves_producidas > 0 else 0
            consumo_total_kg = tabla_filtrada[daily_col].sum() * factor_kg
            
            if kilos_totales_producidos > 0:
                costo_total_kilo = costo_total_lote / kilos_totales_producidos
                conversion_alimenticia = consumo_total_kg / kilos_totales_producidos
                costo_alimento_kilo = costo_total_alimento / kilos_totales_producidos
                costo_pollito_kilo = costo_total_pollitos / kilos_totales_producidos
                costo_otros_kilo = costo_total_otros / kilos_totales_producidos
                
                st.session_state['resultados_base'] = {
                    "kilos_totales_producidos": kilos_totales_producidos,
                    "consumo_total_kg": consumo_total_kg,
                    "costo_total_alimento": costo_total_alimento,
                    "costo_total_pollitos": costo_total_pollitos,
                    "costo_total_otros": costo_total_otros,
                    "costo_total_lote": costo_total_lote,
                    "costo_alimento_kilo": costo_alimento_kilo,
                    "costo_pollito_kilo": costo_pollito_kilo,
                    "costo_otros_kilo": costo_otros_kilo,
                    "costo_total_por_kilo": costo_total_kilo,
                    "conversion_alimenticia": conversion_alimenticia
                }

                costo_map = {
                    'Pre-iniciador': st.session_state.val_pre_iniciador, 'Iniciador': st.session_state.val_iniciador,
                    'Engorde': st.session_state.val_engorde, 'Retiro': st.session_state.val_retiro
                }
                tabla_filtrada['Costo_Kg_Dia'] = tabla_filtrada['Fase_Alimento'].map(costo_map)
                tabla_filtrada['Costo_Alimento_Diario_Ave'] = (tabla_filtrada['Cons_Diario_Ave_gr'] / 1000) * tabla_filtrada['Costo_Kg_Dia']
                tabla_filtrada['Costo_Alimento_Acum_Ave'] = tabla_filtrada['Costo_Alimento_Diario_Ave'].cumsum()
                tabla_filtrada['Mortalidad_Diaria'] = tabla_filtrada['Mortalidad_Acumulada'].diff().fillna(tabla_filtrada['Mortalidad_Acumulada'].iloc[0])
                costo_alimento_desperdiciado = (tabla_filtrada['Mortalidad_Diaria'] * tabla_filtrada['Costo_Alimento_Acum_Ave']).sum()
                
                aves_muertas_total = st.session_state.aves_programadas - aves_producidas
                costo_pollitos_perdidos = aves_muertas_total * st.session_state.costo_pollito
                costo_desperdicio_total = costo_pollitos_perdidos + costo_alimento_desperdiciado

                st.subheader("Indicadores de Eficiencia Clave")
                kpi_cols = st.columns(3)
                kpi_cols[0].metric("Costo Total por Kilo", f"${costo_total_kilo:,.2f}")
                kpi_cols[1].metric("Conversión Alimenticia", f"{conversion_alimenticia:,.3f}")
                kpi_cols[2].metric("Costo por Mortalidad", f"${costo_desperdicio_total:,.2f}", help="Suma del costo de los pollitos perdidos y el alimento que consumieron.")

                st.markdown("---")
                st.subheader("Análisis de Costos Detallado")
                kpi_data = {
                    "Métrica": [
                        "Aves Producidas", "Kilos Totales Producidos", "Consumo / Ave (gr)", "Peso / Ave (gr)",
                        "Costo Alimento / Kilo ($)", "Costo Pollitos / Kilo ($)", "Costo Otros / Kilo ($)", "**Costo Total / Kilo ($)**",
                        "Costo Total Alimento ($)", "Costo Total Pollitos ($)", "Costo Total Otros ($)", "Costo por Mortalidad ($)", "**Costo Total de Producción ($)**"
                    ], "Valor": [
                        round(aves_producidas), round(kilos_totales_producidos), round(consumo_total_objetivo_ave), round(peso_obj_final),
                        costo_alimento_kilo, costo_pollito_kilo, costo_otros_kilo, costo_total_kilo,
                        costo_total_alimento, costo_total_pollitos, costo_total_otros, costo_desperdicio_total, costo_total_lote
                    ]
                }
                df_kpi = pd.DataFrame(kpi_data).set_index("Métrica")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.dataframe(style_kpi_df(df_kpi.iloc[:7]), use_container_width=True)
                with col2:
                    st.dataframe(style_kpi_df(df_kpi.iloc[7:]), use_container_width=True)

                st.markdown("---")
                st.subheader("Gráficos de Resultados")
                col1_graf, col2_graf = st.columns(2)
                with col1_graf:
                    fig, ax = plt.subplots()
                    ax.plot(tabla_filtrada['Dia'], tabla_filtrada['Peso'], color='darkred', label='Peso de Referencia')
                    ax.plot(tabla_filtrada['Dia'], tabla_filtrada['Peso_Estimado'], color='lightcoral', label='Peso Estimado')
                    ax.plot(dia_obj, peso_obj_final, 'o', color='blue', markersize=8, label=f"Día {dia_obj:.0f}: {peso_obj_final:,.0f} gr")
                    ax.legend()
                    ax.set_xlabel("Día del Ciclo")
                    ax.set_ylabel("Peso (gramos)")
                    ax.set_title("Gráfico de Crecimiento")
                    ax.grid(True, linestyle='--', alpha=0.6)
                    
                    try:
                        from matplotlib.offsetbox import OffsetImage, AnnotationBbox
                        logo_img_f = Image.open(BASE_DIR / "ARCHIVOS" / "log_PEQ.png")
                        imagebox = OffsetImage(logo_img_f, zoom=0.2, alpha=0.15)
                        ab = AnnotationBbox(imagebox, (0.95, 0.05), xycoords='axes fraction', frameon=False, box_alignment=(1, 0))
                        ax.add_artist(ab)
                    except Exception:
                        pass
                    st.pyplot(fig)

                with col2_graf:
                    sizes = [costo_alimento_kilo, costo_pollito_kilo, costo_otros_kilo]
                    labels = [f"Alimento\n${sizes[0]:,.2f}", f"Pollitos\n${sizes[1]:,.2f}", f"Otros Costos\n${sizes[2]:,.2f}"]
                    colors = ['darkred', 'lightblue', 'lightcoral']

                    fig_pie, ax_pie = plt.subplots()
                    ax_pie.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors)
                    ax_pie.set_title(f"Participación de Costos\nCosto Total: ${costo_total_kilo:,.2f}/Kg")
                    st.pyplot(fig_pie)
            else:
                st.warning("No se pueden calcular KPIs: los kilos producidos son cero.")

        except Exception as e:
            st.error("Ocurrió un error inesperado durante el procesamiento.")
            st.exception(e)
        finally:
            st.markdown("---")
            st.markdown("""
            <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; border: 1px solid #ccc;">
            <b>Nota de Responsabilidad:</b> Esta es una herramienta de apoyo para uso en granja...
            </div>
            <div style="text-align: center; margin-top: 15px;">
            Desarrollado por la Dirección Técnica de Albateq | dtecnico@albateq.com
            </div>
            """, unsafe_allow_html=True)
