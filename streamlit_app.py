import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from datetime import datetime
from streamlit_option_menu import option_menu

# =======================================================================
# INICIALIZAÇÃO DOS ESTADOS (para não perder valores ao trocar de página)
# =======================================================================
if "limites_tensao" not in st.session_state:
    st.session_state["limites_tensao"] = (120.0, 140.0)

# =======================================================================
# GERAÇÃO DE DADOS SIMULADOS
# =======================================================================
@st.cache_data
def gerar_dados_eletricos():
    n_pontos = 2 * 24 * 60
    fs = 60 * 32
    t = np.arange(n_pontos) / fs
    timestamps = pd.date_range(end=datetime.now(), periods=n_pontos, freq='T')

    def gerar_onda(amplitude, freq, n, ruido_amp=0.5, harm3=0.05, harm5=0.02):
        sinal_fundamental = amplitude * np.sin(2 * np.pi * freq * t[:n])
        sinal_3a = harm3 * amplitude * np.sin(2 * np.pi * (3 * freq) * t[:n])
        sinal_5a = harm5 * amplitude * np.sin(2 * np.pi * (5 * freq) * t[:n])
        ruido = np.random.normal(0, ruido_amp, n)
        return sinal_fundamental + sinal_3a + sinal_5a + ruido

    tensao_a = 127 + gerar_onda(10, 60, n_pontos)
    tensao_b = 127 + gerar_onda(10, 60, n_pontos, ruido_amp=1)
    tensao_c = 127 + gerar_onda(10, 60, n_pontos, ruido_amp=2)

    corrente_a = 10 + gerar_onda(2, 60, n_pontos, ruido_amp=0.2)
    corrente_b = 8.5 + gerar_onda(1.5, 60, n_pontos, ruido_amp=0.15)
    corrente_c = 11 + gerar_onda(2.5, 60, n_pontos, ruido_amp=0.25)

    fp = 0.92
    dados = {
        'Tensão Fase A': tensao_a,
        'Tensão Fase B': tensao_b,
        'Tensão Fase C': tensao_c,
        'Corrente A': corrente_a,
        'Corrente B': corrente_b,
        'Corrente C': corrente_c,
    }

    for fase in ['A', 'B', 'C']:
        dados[f'Potência Ativa {fase}'] = dados[f'Tensão Fase {fase}'] * dados[f'Corrente {fase}'] * fp

    return pd.DataFrame(dados, index=timestamps)

df_original = gerar_dados_eletricos()

# =======================================================================
# VALORES FIXOS DAS MÁQUINAS
# =======================================================================
confianca_fix = {"A": 95.0, "B": 90.0, "C": 85.0}
tempo_op_fix = {"A": 520, "B": 610, "C": 450}
falhas_fix = {"A": 0, "B": 1, "C": 3}

# =======================================================================
# SIDEBAR
# =======================================================================
with st.sidebar:
    # ===============================
    # TÍTULO CHAMATIVO
    # ===============================
    st.markdown("""
        <h1 style='color: #ce4545; font-size: 36px; text-align: center; 
                   text-shadow: 2px 2px #aaa; font-weight: bold; margin-bottom: 20px;'>
            - SIVM -
        </h1>
        """, unsafe_allow_html=True)
    
    # ===============================
    # MENU DE NAVEGAÇÃO
    # ===============================
    escolha_pagina = option_menu(
        menu_title=None,
        options=["Página Inicial", "Histórico", "Configurações"],
        icons=["house", "clock-history", "gear"],
        default_index=0,
        styles={
            "container": {"padding": "5!important", "background-color": "#ffffff"},
            "icon": {"color": "#ce4545", "font-size": "20px"},  # cor do ícone não selecionado
            "nav-link": {
                "font-size": "16px",
                "text-align": "left",
                "margin": "0px",
                "--hover-color": "#eee"
            },
            "nav-link-selected": {
                "background-color": "#ce4545",
                "color": "white",        # texto selecionado
                "icon-color": "white"    # ícone selecionado
            },
        }
    )

    # =======================================================================
    # INDICADORES DE ALERTAS NA SIDEBAR
    # =======================================================================
    min_limite, max_limite = st.session_state["limites_tensao"]

    def gerar_alarm_table(nome_maquina, tensao):
        df_alarme = tensao[(tensao < min_limite) | (tensao > max_limite)].to_frame(name="Tensão (V)")
        if df_alarme.empty:
            df_alarme = pd.DataFrame({"Tensão (V)": [], "Alarme": []})
        else:
            df_alarme["Alarme"] = df_alarme["Tensão (V)"].apply(
                lambda x: "Acima do limite" if x > max_limite else "Abaixo do limite"
            )
        return df_alarme

    def indicador_alertas(df_alarme):
        n_alertas = len(df_alarme)
        if n_alertas == 0:
            return "🟢"  # sem alertas
        elif n_alertas <= 20:
            return "🟠"  # poucos alertas
        else:
            return "🔴"  # muitos alertas

    # Calcular indicadores para cada máquina
    tabela_a = gerar_alarm_table("A", df_original['Tensão Fase A'])
    tabela_b = gerar_alarm_table("B", df_original['Tensão Fase B'])
    tabela_c = gerar_alarm_table("C", df_original['Tensão Fase C'])

    # Exibir indicadores na sidebar
    with st.sidebar:
        st.markdown("###  --- Status das Máquinas")
        st.markdown(f" ->  **Máquina A:** {indicador_alertas(tabela_a)}")
        st.markdown(f" ->  **Máquina B:** {indicador_alertas(tabela_b)}")
        st.markdown(f" ->  **Máquina C:** {indicador_alertas(tabela_c)}")
        st.markdown("---")
# =======================================================================
# CONFIGURAÇÕES
# =======================================================================
if escolha_pagina == "Configurações":
    st.markdown("#### Configurações")
    max_tensao = st.number_input("Valor máximo da tensão (V)", value=st.session_state["limites_tensao"][1], step=1.0)
    min_tensao = st.number_input("Valor mínimo da tensão (V)", value=st.session_state["limites_tensao"][0], step=1.0)
    

    if st.button("Salvar limites"):
        if (min_tensao < max_tensao):
            st.session_state["limites_tensao"] = (min_tensao, max_tensao)
            st.success(f"✅ Limites salvos: {min_tensao} V - {max_tensao} V")
        else: 
            st.error((f"Limite Inferior: {min_tensao}V é superior ao limite máximo {max_tensao} V"))

# =======================================================================
# PÁGINA HISTÓRICO
# =======================================================================
if escolha_pagina == "Histórico":
    st.markdown("#### Histórico")

    min_limite, max_limite = st.session_state["limites_tensao"]

    # Função para gerar tabela de alarmes para uma máquina
    def gerar_alarm_table(nome_maquina, tensao):
        df_alarme = tensao[(tensao < min_limite) | (tensao > max_limite)].to_frame(name="Tensão (V)")
        if df_alarme.empty:
            df_alarme = pd.DataFrame({"Tensão (V)": [], "Alarme": []})
        else:
            df_alarme["Alarme"] = df_alarme["Tensão (V)"].apply(
                lambda x: "Acima do limite" if x > max_limite else "Abaixo do limite"
            )
        return df_alarme

    # Criar abas por máquina
    tab_a, tab_b, tab_c = st.tabs(["Máquina A", "Máquina B", "Máquina C"])

    with tab_a:
        st.write("### Máquina A")
        tabela_a = gerar_alarm_table("A", df_original['Tensão Fase A'])
        st.dataframe(tabela_a)

    with tab_b:
        st.write("### Máquina B")
        tabela_b = gerar_alarm_table("B", df_original['Tensão Fase B'])
        st.dataframe(tabela_b)

    with tab_c:
        st.write("### Máquina C")
        tabela_c = gerar_alarm_table("C", df_original['Tensão Fase C'])
        st.dataframe(tabela_c)


# =======================================================================
# PÁGINA INICIAL
# =======================================================================
if escolha_pagina == "Página Inicial":
    st.markdown("#### Página Inicial")
    min_limite, max_limite = st.session_state["limites_tensao"]

    dados_a = df_original[['Tensão Fase A', 'Potência Ativa A']]
    dados_b = df_original[['Tensão Fase B', 'Potência Ativa B']]
    dados_c = df_original[['Tensão Fase C', 'Potência Ativa C']]

    media_conf = np.mean(list(confianca_fix.values()))
    tab1, tab2, tab3 = st.tabs(["Máquina A", "Máquina B", "Máquina C"])

    def exibir_maquina(nome_maquina, tensao, conf, tempo, falhas):
        col1, col2, col3 = st.columns(3)

        # Métrica de confiança
        delta_conf = ((conf - media_conf) / media_conf) * 100
        col1.metric("Confiança do Equipamento", f"{conf:.1f} %", delta=f"{delta_conf:+.1f} %")

        # Métrica de tempo de operação comparando com a média
        media_tempo = np.mean(list(tempo_op_fix.values()))
        delta_tempo = ((tempo - media_tempo) / media_tempo) * 100
        col2.metric("Tempo de Operação", f"{tempo} h", delta=f"{delta_tempo:+.1f} %")

        # Métrica de falhas comparando com a média
        media_falhas = np.mean(list(falhas_fix.values()))
        delta_falhas = ((falhas - media_falhas) / (media_falhas+0.01)) * 100  # evitar divisão por zero
        col3.metric("Falhas Detectadas", f"{falhas}", delta=f"{delta_falhas:+.1f} %")

        col_rms, col_fft = st.columns(2)

        with col_rms:
            st.markdown("### RMS (Tensão)")
            df_tensao = pd.DataFrame({"timestamp": tensao.index, "tensao": tensao.values})
            y_min = tensao.min() - 5
            y_max = tensao.max() + 5
            chart_rms = alt.Chart(df_tensao).mark_line(color="red", strokeWidth=2).encode(
                x="timestamp:T",
                y=alt.Y("tensao:Q", scale=alt.Scale(domain=[y_min, y_max]))
            )

            if min_limite and max_limite:
                linha_min = alt.Chart(pd.DataFrame({"y": [min_limite]})).mark_rule(
                    strokeDash=[4, 4], color="black", size=3
                ).encode(y="y:Q")
                linha_max = alt.Chart(pd.DataFrame({"y": [max_limite]})).mark_rule(
                    strokeDash=[4, 4], color="black", size=3
                ).encode(y="y:Q")
                chart_rms = chart_rms + linha_min + linha_max
            st.altair_chart(chart_rms, use_container_width=True)

        with col_fft:
            st.markdown("### FFT (Tensão)")
            fft_vals = np.abs(np.fft.rfft(tensao.values))
            freq = np.fft.rfftfreq(len(tensao.values), d=1/1920)  # fs = 60*32
            df_fft = pd.DataFrame({"freq": freq, "FFT": fft_vals})
            chart_fft = alt.Chart(df_fft).mark_line(color="red").encode(
                x=alt.X("freq:Q", title="Frequência (Hz)"),
                y=alt.Y("FFT:Q", title="Amplitude")
            )
            st.altair_chart(chart_fft, use_container_width=True)

    with tab1:
        exibir_maquina("Máquina A", dados_a['Tensão Fase A'], confianca_fix["A"], tempo_op_fix["A"], falhas_fix["A"])
    with tab2:
        exibir_maquina("Máquina B", dados_b['Tensão Fase B'], confianca_fix["B"], tempo_op_fix["B"], falhas_fix["B"])
    with tab3:
        exibir_maquina("Máquina C", dados_c['Tensão Fase C'], confianca_fix["C"], tempo_op_fix["C"], falhas_fix["C"])

    st.divider()
