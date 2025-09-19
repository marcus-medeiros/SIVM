import streamlit as st
import pandas as pd
import numpy as np
import time
import matplotlib.pyplot as plt
from datetime import datetime

# =======================================================================
# GERAÇÃO DE DADOS SIMULADOS (df_original)
# =======================================================================
@st.cache_data
def gerar_dados_eletricos():
    n_pontos = 2 * 24 * 60  # 2 dias, 1 ponto/minuto
    timestamps = pd.date_range(end=datetime.now(), periods=n_pontos, freq='T')

    def gerar_serie(base, amp, n):
        tendencia = np.linspace(0, amp, n)
        ruido = np.random.normal(0, amp * 0.1, n)
        return base + tendencia + ruido

    dados = {
        'Tensão Fase A': gerar_serie(125, 3, n_pontos),
        'Tensão Fase B': gerar_serie(126, 2, n_pontos),
        'Tensão Fase C': gerar_serie(124, 4, n_pontos),

        'Corrente A': gerar_serie(10, 2, n_pontos),
        'Corrente B': gerar_serie(9, 1.5, n_pontos),
        'Corrente C': gerar_serie(11, 2.5, n_pontos),
    }
    fp = 0.92
    for fase in ['A', 'B', 'C']:
        dados[f'Potência Ativa {fase}'] = dados[f'Tensão Fase {fase}'] * dados[f'Corrente {fase}'] * fp
        dados[f'Potência Reativa {fase}'] = dados[f'Tensão Fase {fase}'] * dados[f'Corrente {fase}'] * np.sin(np.arccos(fp))
        dados[f'Potência Aparente {fase}'] = dados[f'Tensão Fase {fase}'] * dados[f'Corrente {fase}']

    return pd.DataFrame(dados, index=timestamps)

df_original = gerar_dados_eletricos()

# =======================================================================
# CONFIGURAÇÃO DA PÁGINA
# =======================================================================
st.set_page_config(
    page_title="SIVM",
    page_icon=":zap:",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =======================================================================
# SIDEBAR
# =======================================================================
with st.sidebar:
    st.image("Logo_v2.png", width=100)
    escolha_pagina = st.radio(
        "Escolha uma opção:",
        ["Página Inicial", "Historico", "Configurações"]
    )
    st.markdown("---")

# =======================================================================
# PÁGINA INICIAL
# =======================================================================
if escolha_pagina == "Página Inicial":
    st.header("🖥️ Geral")

    # Filtrando colunas por fase
    dados_a = df_original[['Tensão Fase A', 'Corrente A', 'Potência Ativa A', 'Potência Reativa A', 'Potência Aparente A']]
    dados_b = df_original[['Tensão Fase B', 'Corrente B', 'Potência Ativa B', 'Potência Reativa B', 'Potência Aparente B']]
    dados_c = df_original[['Tensão Fase C', 'Corrente C', 'Potência Ativa C', 'Potência Reativa C', 'Potência Aparente C']]

    pot_ativa_max_a = dados_a['Potência Ativa A'].max()
    pot_ativa_max_b = dados_b['Potência Ativa B'].max()
    pot_ativa_max_c = dados_c['Potência Ativa C'].max()
    media_pw = (pot_ativa_max_a + pot_ativa_max_b + pot_ativa_max_c) / 3

    st.header("Análise das Tensões e Correntes")
    tab1, tab2, tab3 = st.tabs(["Máquina A", "Máquina B", "Máquina C"])

    # Função auxiliar para exibir cada aba
    def exibir_maquina(nome_maquina, dados, pot_ativa_max, delta_pot):
        st.subheader(f"{nome_maquina}")

        col_rms, col_fft = st.columns(2)
        with col_rms:
            st.write("### RMS")
            st.line_chart(dados.iloc[:, [0, 1]])  # Tensão + Corrente
        with col_fft:
            st.write("### FFT")
            fft_vals = np.abs(np.fft.rfft(dados.iloc[:, 0]))  # FFT da tensão
            st.line_chart(fft_vals)

        col1, col2, col3 = st.columns(3)
        col1.metric("Potência Ativa", f"{pot_ativa_max:.2f} W", f"{delta_pot:.2f} W | Média: {media_pw:.2f} W")
        col2.metric("Potência Reativa", f"{dados.iloc[:, 3].mean():.2f} var", "-8%")
        col3.metric("Potência Aparente", f"{dados.iloc[:, 4].mean():.2f} VA", "12%", delta_color="inverse")

    with tab1:
        exibir_maquina("Máquina A", dados_a, pot_ativa_max_a, pot_ativa_max_a - media_pw)

    with tab2:
        exibir_maquina("Máquina B", dados_b, pot_ativa_max_b, pot_ativa_max_b - media_pw)

    with tab3:
        exibir_maquina("Máquina C", dados_c, pot_ativa_max_c, pot_ativa_max_c - media_pw)

    st.divider()
