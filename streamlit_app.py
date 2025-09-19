import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from streamlit_option_menu import option_menu

# =======================================================================
# GERAÇÃO DE DADOS SIMULADOS (df_original)
# =======================================================================
@st.cache_data
def gerar_dados_eletricos():
    n_pontos = 2 * 24 * 60  # 2 dias, 1 ponto/minuto
    fs = 60 * 32  # amostragem "virtual" 32 amostras por ciclo de 60Hz
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
        dados[f'Potência Reativa {fase}'] = dados[f'Tensão Fase {fase}'] * dados[f'Corrente {fase}'] * np.sin(np.arccos(fp))
        dados[f'Potência Aparente {fase}'] = dados[f'Tensão Fase {fase}'] * dados[f'Corrente {fase}']

    return pd.DataFrame(dados, index=timestamps)

df_original = gerar_dados_eletricos()

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
            "container": {"padding": "5!important", "background-color": "#f9f9f9"},
            "icon": {"color": "#4a90e2", "font-size": "20px"},
            "nav-link": {
                "font-size": "16px",
                "text-align": "left",
                "margin": "0px",
                "--hover-color": "#eee",
            },
            "nav-link-selected": {"background-color": "#4a90e2", "color": "white"},
        }
    )

# =======================================================================
# PÁGINA INICIAL
# =======================================================================
if escolha_pagina == "Página Inicial":
    st.header("🖥️ Geral")

    # Dados individuais por máquina
    dados_a = df_original[['Tensão Fase A', 'Corrente A', 'Potência Ativa A', 'Potência Reativa A', 'Potência Aparente A']]
    dados_b = df_original[['Tensão Fase B', 'Corrente B', 'Potência Ativa B', 'Potência Reativa B', 'Potência Aparente B']]
    dados_c = df_original[['Tensão Fase C', 'Corrente C', 'Potência Ativa C', 'Potência Reativa C', 'Potência Aparente C']]

    pot_ativa_max_a = dados_a['Potência Ativa A'].max()
    pot_ativa_max_b = dados_b['Potência Ativa B'].max()
    pot_ativa_max_c = dados_c['Potência Ativa C'].max()
    media_pw = (pot_ativa_max_a + pot_ativa_max_b + pot_ativa_max_c) / 3

    tab1, tab2, tab3 = st.tabs(["Máquina A", "Máquina B", "Máquina C"])

    def exibir_maquina(nome_maquina, tensao, corrente, pot_ativa, pot_reativa, pot_aparente, pot_ativa_max, delta_pot):
        st.subheader(f"{nome_maquina}")

        col1, col2, col3 = st.columns(3)
        confianca = max(0, min(100, 100 - abs(delta_pot) / media_pw * 100))
        tempo_operacao = np.random.randint(100, 1000)
        falhas = np.random.randint(0, 5)

        col1.metric("Confiança do Equipamento", f"{confianca:.1f} %")
        col2.metric("Tempo de Operação", f"{tempo_operacao} h")
        col3.metric("Falhas Detectadas", f"{falhas}")

        st.markdown("---")

        col_rms, col_fft = st.columns(2)
        with col_rms:
            st.write("### RMS (Tensão)")
            st.line_chart(tensao)

        with col_fft:
            st.write("### FFT (Tensão)")
            fft_vals = np.abs(np.fft.rfft(tensao.values))
            fft_df = pd.DataFrame({"FFT": fft_vals})
            st.line_chart(fft_df)

    with tab1:
        exibir_maquina("Máquina A", dados_a['Tensão Fase A'], dados_a['Corrente A'],
                       dados_a['Potência Ativa A'], dados_a['Potência Reativa A'], dados_a['Potência Aparente A'],
                       pot_ativa_max_a, pot_ativa_max_a - media_pw)

    with tab2:
        exibir_maquina("Máquina B", dados_b['Tensão Fase B'], dados_b['Corrente B'],
                       dados_b['Potência Ativa B'], dados_b['Potência Reativa B'], dados_b['Potência Aparente B'],
                       pot_ativa_max_b, pot_ativa_max_b - media_pw)

    with tab3:
        exibir_maquina("Máquina C", dados_c['Tensão Fase C'], dados_c['Corrente C'],
                       dados_c['Potência Ativa C'], dados_c['Potência Reativa C'], dados_c['Potência Aparente C'],
                       pot_ativa_max_c, pot_ativa_max_c - media_pw)

    st.divider()
