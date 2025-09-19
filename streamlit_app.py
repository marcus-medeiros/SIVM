import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# =========================
# CONFIGURAÇÃO DA PÁGINA
# =========================
st.set_page_config(
    page_title="Monitor de Máquinas - WebDeck",
    page_icon="✅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================
# SIDEBAR
# =========================
with st.sidebar:
    st.image("Logo_v2.png", width=120)
    escolha_pagina = st.radio(
        "Navegação:",
        ["Visão Geral", "Checagens", "Incidentes"]
    )
    st.markdown("---")
    st.caption("📅 Últimas 24h")
    st.markdown("**Status:** ✅ Online")
    st.markdown("**Monitor:** 🟢 Ativo")

# =========================
# DADOS REAIS (DO SEU CÓDIGO INICIAL)
# =========================
# Aqui você substitui pelas leituras reais do seu código
dados_maquina1 = pd.read_csv("dados_maquina1.csv", parse_dates=["tempo"])
dados_maquina2 = pd.read_csv("dados_maquina2.csv", parse_dates=["tempo"])
dados_maquina3 = pd.read_csv("dados_maquina3.csv", parse_dates=["tempo"])

# =========================
# VISÃO GERAL
# =========================
if escolha_pagina == "Visão Geral":
    st.title("📊 WebDeck - Monitoramento de Máquinas")

    # KPIs gerais
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Tempo de Atividade", "99.8%", "Últimas 24h")
    with col2:
        st.metric("Tempo de Resposta Médio", f"{dados_maquina1['tempo_resposta'].mean():.1f} ms")
    with col3:
        st.metric("Incidentes", "0", "0 s")

    # Tabs para gráficos das máquinas
    tab1, tab2, tab3 = st.tabs(["🖥️ Máquina 1", "🖥️ Máquina 2", "🖥️ Máquina 3"])

    with tab1:
        st.subheader("Histórico - Máquina 1")
        fig, ax = plt.subplots()
        ax.plot(dados_maquina1["tempo"], dados_maquina1["tempo_resposta"], label="Tempo de Resposta (ms)")
        ax.set_xlabel("Tempo")
        ax.set_ylabel("ms")
        ax.legend()
        st.pyplot(fig)

    with tab2:
        st.subheader("Histórico - Máquina 2")
        fig, ax = plt.subplots()
        ax.plot(dados_maquina2["tempo"], dados_maquina2["tempo_resposta"], label="Tempo de Resposta (ms)", color="orange")
        ax.set_xlabel("Tempo")
        ax.set_ylabel("ms")
        ax.legend()
        st.pyplot(fig)

    with tab3:
        st.subheader("Histórico - Máquina 3")
        fig, ax = plt.subplots()
        ax.plot(dados_maquina3["tempo"], dados_maquina3["tempo_resposta"], label="Tempo de Resposta (ms)", color="green")
        ax.set_xlabel("Tempo")
        ax.set_ylabel("ms")
        ax.legend()
        st.pyplot(fig)

# =========================
# CHECAGENS
# =========================
elif escolha_pagina == "Checagens":
    st.title("📋 Checagens Recentes")
    df_check = pd.concat([
        dados_maquina1.assign(maquina="Máquina 1"),
        dados_maquina2.assign(maquina="Máquina 2"),
        dados_maquina3.assign(maquina="Máquina 3")
    ])
    st.dataframe(df_check)

# =========================
# INCIDENTES
# =========================
elif escolha_pagina == "Incidentes":
    st.title("🚨 Incidentes")
    st.info("Nenhum incidente registrado nas últimas 24h ✅")
