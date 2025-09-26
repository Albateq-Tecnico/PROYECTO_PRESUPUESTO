# Reemplaza el bloque try...except en pages/2_Simulador_de_Mortalidad.py con esto:

try:
    # --- PASO 1: RECONSTRUCCIÓN COMPLETA DE LA TABLA BASE ---
    tabla_base = df_referencia[
        (df_referencia['RAZA'] == st.session_state.raza_seleccionada) &
        (df_referencia['SEXO'] == st.session_state.sexo_seleccionado)
    ].copy()

    if tabla_base.empty:
        st.warning("No se encontraron datos de referencia para la simulación.")
        st.stop()

    tabla_base['Cons_Acum'] = clean_numeric_column(tabla_base['Cons_Acum'])
    tabla_base['Peso'] = clean_numeric_column(tabla_base['Peso'])
    factor_ajuste = 1 - (st.session_state.restriccion_programada / 100.0)
    tabla_base['Cons_Acum_Ajustado'] = tabla_base['Cons_Acum'] * factor_ajuste
    
    dias_1_14 = tabla_base['Dia'] <= 14
    dias_15_adelante = tabla_base['Dia'] >= 15
    tabla_base.loc[dias_1_14, 'Peso_Estimado'] = calcular_peso_estimado(tabla_base[dias_1_14], df_coeffs_15, st.session_state.raza_seleccionada, st.session_state.sexo_seleccionado)
    tabla_base.loc[dias_15_adelante, 'Peso_Estimado'] = calcular_peso_estimado(tabla_base[dias_15_adelante], df_coeffs, st.session_state.raza_seleccionada, st.session_state.sexo_seleccionado)
    tabla_base['Peso_Estimado'] *= (st.session_state.productividad / 100.0)

    closest_idx = (tabla_base['Peso_Estimado'] - st.session_state.peso_objetivo).abs().idxmin()
    tabla_simulada = tabla_base.loc[:closest_idx].copy()
    
    # --- PASO 2: ASIGNAR FASE DE ALIMENTO ---
    df_interp = tabla_simulada.drop_duplicates(subset=['Peso_Estimado']).sort_values('Peso_Estimado')
    consumo_total_objetivo_ave = np.interp(st.session_state.peso_objetivo, df_interp['Peso_Estimado'], df_interp['Cons_Acum_Ajustado'])
    
    limite_pre = st.session_state.pre_iniciador
    limite_ini = st.session_state.pre_iniciador + st.session_state.iniciador
    limite_ret = consumo_total_objetivo_ave - st.session_state.retiro if st.session_state.retiro > 0 else np.inf
    conditions = [
        tabla_simulada['Cons_Acum_Ajustado'] <= limite_pre,
        tabla_simulada['Cons_Acum_Ajustado'].between(limite_pre, limite_ini, inclusive='right'),
        tabla_simulada['Cons_Acum_Ajustado'] > limite_ret
    ]
    choices = ['Pre-iniciador', 'Iniciador', 'Retiro']
    tabla_simulada['Fase_Alimento'] = np.select(conditions, choices, default='Engorde')

    # --- PASO 3: APLICAR LA SIMULACIÓN DE MORTALIDAD ---
    dia_obj = tabla_simulada['Dia'].iloc[-1]
    total_mortalidad_aves = st.session_state.aves_programadas * (st.session_state.mortalidad_objetivo / 100.0)
    mortalidad_acum_simulada = calcular_curva_mortalidad(dia_obj, total_mortalidad_aves, tipo_escenario, porcentaje_escenario)
    tabla_simulada['Mortalidad_Acumulada'] = mortalidad_acum_simulada
    tabla_simulada['Saldo'] = st.session_state.aves_programadas - tabla_simulada['Mortalidad_Acumulada']

    # --- PASO 4: RECALCULAR CONSUMO DIARIO Y KPIS ---
    tabla_simulada['Cons_Diario_Ave_gr'] = tabla_simulada['Cons_Acum_Ajustado'].diff().fillna(tabla_simulada['Cons_Acum_Ajustado'].iloc[0])
    if st.session_state.unidades_calculo == "Kilos":
        daily_col_name = "Kilos Diarios"
        tabla_simulada[daily_col_name] = (tabla_simulada['Cons_Diario_Ave_gr'] * tabla_simulada['Saldo']) / 1000
    else:
        daily_col_name = "Bultos Diarios"
        tabla_simulada[daily_col_name] = np.ceil((tabla_simulada['Cons_Diario_Ave_gr'] * tabla_simulada['Saldo']) / 40000)

    consumo_por_fase = tabla_simulada.groupby('Fase_Alimento')[daily_col_name].sum()
    factor_kg = 1 if st.session_state.unidades_calculo == "Kilos" else 40
    consumo_total_kg = consumo_por_fase.sum() * factor_kg
    
    costos_kg_map = {
        'Pre-iniciador': st.session_state.val_pre_iniciador, 'Iniciador': st.session_state.val_iniciador,
        'Engorde': st.session_state.val_engorde, 'Retiro': st.session_state.val_retiro
    }
    costo_total_alimento = sum(consumo_por_fase.get(f, 0) * costos_kg_map.get(f, 0) for f in consumo_por_fase.index) * factor_kg
    
    costo_total_pollitos = st.session_state.aves_programadas * st.session_state.costo_pollito
    costo_total_otros = st.session_state.aves_programadas * st.session_state.otros_costos_ave
    costo_total_lote = costo_total_alimento + costo_total_pollitos + costo_total_otros

    aves_producidas = tabla_simulada['Saldo'].iloc[-1]
    peso_obj_final = tabla_simulada['Peso_Estimado'].iloc[-1]
    kilos_totales_producidos = (aves_producidas * peso_obj_final) / 1000 if aves_producidas > 0 else 0

    st.header("2. Resultados de la Simulación")
    if kilos_totales_producidos > 0:
        costo_total_kilo = costo_total_lote / kilos_totales_producidos
        conversion_alimenticia = consumo_total_kg / kilos_totales_producidos
        
        tabla_simulada['Mortalidad_Diaria'] = tabla_simulada['Mortalidad_Acumulada'].diff().fillna(tabla_simulada['Mortalidad_Acumulada'].iloc[0])
        costo_desperdicio = # ... (cálculo de costo desperdicio)

        st.subheader("Indicadores de Eficiencia Clave (Simulado)")
        kpi_cols = st.columns(3)
        kpi_cols[0].metric("Costo Total por Kilo", f"${costo_total_kilo:,.2f}")
        kpi_cols[1].metric("Conversión Alimenticia", f"{conversion_alimenticia:,.3f}")
        kpi_cols[2].metric("Costo por Mortalidad", f"${costo_desperdicio:,.2f}")
        
        st.markdown("---")
        st.subheader("Desglose del Costo por Kilo Producido")

        costo_alimento_kilo = costo_total_alimento / kilos_totales_producidos
        costo_pollitos_kilo = costo_total_pollitos / kilos_totales_producidos
        otros_costos_kilo = costo_total_otros / kilos_totales_producidos

        summary_data = {
            "Componente de Costo": ["Costo Alimento por Kilo", "Costo Pollito por Kilo", "Otros Costos por Kilo", "Costo Total por Kilo"],
            "Valor ($/kg)": [costo_alimento_kilo, costo_pollitos_kilo, otros_costos_kilo, costo_total_kilo]
        }
        df_summary = pd.DataFrame(summary_data)
        
        # --- CAMBIO PARA DEPURACIÓN ---
        st.info("DEBUG: Intentando mostrar la tabla de desglose sin formato.")
        st.dataframe(df_summary, use_container_width=True) # Mostrar sin estilo
        
        st.markdown("---")
        st.subheader("Gráficos del Escenario Simulado")
        # ... (código de los gráficos) ...
    else:
        st.warning("No se pueden calcular los KPIs: los kilos producidos son cero.")

except Exception as e:
    st.error(f"Ocurrió un error inesperado durante la simulación.")
    st.exception(e)
