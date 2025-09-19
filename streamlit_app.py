import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# =========================
# CONFIGURAÇÃO DA PÁGINA
# =========================
st.set_page_config(
    page_title="Site Monitor - WebDeck",
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
    st.caption("📅 Ontem")
    st.markdown("**Status:** ✅ Online")
    st.markdown("**Monitor:** 🟢 Ativo")

# =========================
# SIMULAÇÃO DE DADOS
# =========================
np.random.seed(42)
horas = pd.date_range(datetime.now() - timedelta(hours=12), periods=24, freq="H")
tempo_resposta = np.random.randint(50, 130, size=24)

# =========================
# VISÃO GERAL
# =========================
if escolha_pagina == "Visão Geral":
    st.title("📊 WebDeck")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Tempo de Atividade", "100%", "10h 45min")
    with col2:
        st.metric("Tempo de Resposta Médio", "75 ms", f"{np.mean(tempo_resposta)-75:.1f} ms")
    with col3:
        st.metric("Incidentes", "0", "0 s")

    st.markdown("### 📈 Histórico de Tempo de Resposta")
    st.line_chart(pd.DataFrame({"Tempo de Resposta (ms)": tempo_resposta}, index=horas))

# =========================
# CHECAGENS
# =========================
elif escolha_pagina == "Checagens":
    st.title("📋 Checagens Recentes")
    st.dataframe(
        pd.DataFrame({
            "Horário": horas.strftime("%H:%M"),
            "Status": ["✅ OK" for _ in range(24)],
            "Tempo de Resposta (ms)": tempo_resposta
        })
    )

# =========================
# INCIDENTES
# =========================
elif escolha_pagina == "Incidentes":
    st.title("🚨 Incidentes")
    st.info("Nenhum incidente registrado nas últimas 24h ✅")
