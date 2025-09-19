import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from datetime import datetime
from streamlit_option_menu import option_menu

# =======================================================================
# GERAÇÃO DE DADOS SIMULADOS (df_original)
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
    tensao_b = 127 + gerar_onda(10, 60, n_pontos, ruido_amp=0.4)
    tensao_c = 127 + gerar_onda(10, 60, n_pontos, ruido_amp=0.6)

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
# SIDEBAR MODERNA
# =======================================================================
with st.sidebar:
    st.image("Logo_v2.png", width=120)
    escolha_pagina = option_menu(
        menu_title=None,
        options=["Página Inicial", "Histórico", "Configurações"],
        icons=["house", "clock-history", "gear"],
        default_index=0,
        styles={
            "container": {"padding": "5!important", "background-color": "#ffffff"},
            "icon": {"color": "#FFFFFF", "font-size": "20px"},
            "nav-link": {"font-size": "16px", "text-align": "left", "margin": "0px", "--hover-color": "#eee"},
            "nav-link-selected": {"background-color": "#ce4545", "color": "white"},
        }
    )

# =======================================================================
# CONFIGURAÇÕES
# =======================================================================
if escolha_pagina == "Configurações":
    st.subheader("Configurações de Limites dos Gráficos")
    st.markdown("Defina o limite mínimo e máximo das tensões")

    min_tensao = st.number_input("Valor mínimo da tensão (V)", value=120.0, step=1.0)
    max_tensao = st.number_input("Valor máximo da tensão (V)", value=140.0, step=1.0)

    st.session_state["limites_tensao"] = (min_tensao, max_tensao)
    st.success(f"Limites definidos: {min_tensao} V - {max_tensao} V")

# =======================================================================
# PÁGINA INICIAL
# =======================================================================
if escolha_pagina == "Página Inicial":
    limites = st.session_state.get("limites_tensao", (None, None))
    min_limite, max_limite = limites

    dados_a = df_original[['Tensão Fase A', 'Potência Ativa A']]
    dados_b = df_original[['Tensão Fase B', 'Potência Ativa B']]
    dados_c = df_original[['Tensão Fase C', 'Potência Ativa C']]

    media_conf = np.mean(list(confianca_fix.values()))
    tab1, tab2, tab3 = st.tabs(["Máquina A", "Máquina B", "Máquina C"])

    def exibir_maquina(nome_maquina, tensao, conf, tempo, falhas):
        col1, col2, col3 = st.columns(3)
        delta_conf = ((conf - media_conf) / media_conf) * 100
        col1.metric("Confiança do Equipamento", f"{conf:.1f} %", delta=f"{delta_conf:+.1f} %")
        col2.metric("Tempo de Operação", f"{tempo} h")
        col3.metric("Falhas Detectadas", f"{falhas}")

        st.markdown("### RMS (Tensão)")

        df_tensao = pd.DataFrame({"timestamp": tensao.index, "tensao": tensao.values})

        chart = alt.Chart(df_tensao).mark_line(color="red").encode(
            x="timestamp:T",
            y="tensao:Q"
        )

        # Adiciona linhas horizontais tracejadas se os limites existirem
        if min_limite is not None and max_limite is not None:
            linha_min = alt.Chart(pd.DataFrame({"y": [min_limite]})).mark_rule(
                strokeDash=[4, 4], color="gray"
            ).encode(y="y:Q")
            linha_max = alt.Chart(pd.DataFrame({"y": [max_limite]})).mark_rule(
                strokeDash=[4, 4], color="gray"
            ).encode(y="y:Q")
            chart = chart + linha_min + linha_max

        st.altair_chart(chart, use_container_width=True)

    with tab1:
        exibir_maquina("Máquina A", dados_a['Tensão Fase A'], confianca_fix["A"], tempo_op_fix["A"], falhas_fix["A"])
    with tab2:
        exibir_maquina("Máquina B", dados_b['Tensão Fase B'], confianca_fix["B"], tempo_op_fix["B"], falhas_fix["B"])
    with tab3:
        exibir_maquina("Máquina C", dados_c['Tensão Fase C'], confianca_fix["C"], tempo_op_fix["C"], falhas_fix["C"])

    st.divider()
