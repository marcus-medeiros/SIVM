import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from scipy.io import loadmat

# Configuração da página inicial
st.set_page_config(page_title="SIVM - Análise de Sinais", layout="wide")

# =======================================================================
# CONTROLE DE ESTADO
# =======================================================================
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

# =======================================================================
# TELA DE LOGIN
# =======================================================================
def check_login():
    st.markdown("""
        <style>
            .stApp { background-color: #f0f2f6; }
            .login-title { text-align: center; color: #ce4545; font-weight: bold; margin-bottom: 2rem; }
            div.stButton > button { background-color: #ce4545; color: white; height: 3em; font-weight: bold; }
            div.stButton > button:hover { background-color: #a83838; color: white; }
        </style>
    """, unsafe_allow_html=True)

    _, col2, _ = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<h1 class='login-title'>- SIVM -</h1>", unsafe_allow_html=True)
        user = st.text_input("👤 Usuário", placeholder="admin")
        pwd = st.text_input("🔑 Senha", type="password", placeholder="admin")

        if st.button("Entrar", use_container_width=True):
            if user == "admin" and pwd == "admin":
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")

# =======================================================================
# LEITURA E PROCESSAMENTO DE ARQUIVOS .MAT
# =======================================================================
def extrair_sinais_mat(uploaded_file):
    """Lê um arquivo .mat e retorna um dicionário de vetores 1D."""
    try:
        dados = loadmat(uploaded_file)
        # Filtra metadados internos do MATLAB (__header__, etc.)
        variaveis_validas = {
            k: np.array(v).flatten()
            for k, v in dados.items()
            if not k.startswith("__") and np.issubdtype(np.array(v).dtype, np.number)
        }
        return variaveis_validas
    except Exception as e:
        st.error(f"Erro ao ler {uploaded_file.name}: {e}")
        return {}

def plotar_sinal_e_fft(sinal, titulo, fs=1920):
    """Gera gráficos temporais e FFT para um sinal 1D."""
    st.subheader(titulo)
    col1, col2 = st.columns(2)

    # Gráfico temporal / RMS
    with col1:
        st.markdown("**Sinal no Tempo**")
        df_tempo = pd.DataFrame({
            "Amostra": np.arange(len(sinal)),
            "Amplitude": sinal
        })
        grafico_tempo = alt.Chart(df_tempo).mark_line(color="#ce4545").encode(
            x=alt.X("Amostra:Q", title="Amostra"),
            y=alt.Y("Amplitude:Q", title="Tensão / Sinal")
        ).properties(height=300)
        st.altair_chart(grafico_tempo, use_container_width=True)

    # Gráfico FFT
    with col2:
        st.markdown("**Espectro de Frequência (FFT)**")
        fft_vals = np.abs(np.fft.rfft(sinal))
        freqs = np.fft.rfftfreq(len(sinal), d=1.0 / fs)
        df_fft = pd.DataFrame({"Frequência (Hz)": freqs, "Magnitude": fft_vals})
        
        grafico_fft = alt.Chart(df_fft).mark_line(color="#2980b9").encode(
            x=alt.X("Frequência (Hz):Q", title="Frequência (Hz)"),
            y=alt.Y("Magnitude:Q", title="Magnitude")
        ).properties(height=300)
        st.altair_chart(grafico_fft, use_container_width=True)

# =======================================================================
# APLICAÇÃO PRINCIPAL
# =======================================================================
def main_app():
    # Sidebar: Logout e Carregamento de Arquivos
    with st.sidebar:
        st.markdown("<h2 style='color: #ce4545; text-align: center;'>- SIVM -</h2>", unsafe_allow_html=True)
        if st.button("Sair (Logout)"):
            st.session_state["authenticated"] = False
            st.rerun()

        st.markdown("---")
        st.markdown("### 📂 Upload de Arquivos .mat")
        arquivo_1 = st.file_uploader("Arquivo 1 (.mat)", type=["mat"], key="mat1")
        arquivo_2 = st.file_uploader("Arquivo 2 (.mat)", type=["mat"], key="mat2")
        taxa_amostragem = st.number_input("Taxa de Amostragem (Hz)", value=1920, step=100)

    st.title("Visualizador de Sinais (.MAT)")

    # Abas para os dois arquivos
    tab1, tab2 = st.tabs(["📁 Arquivo 1", "📁 Arquivo 2"])

    for tab, arquivo, nome_padrao in [(tab1, arquivo_1, "Arquivo 1"), (tab2, arquivo_2, "Arquivo 2")]:
        with tab:
            if arquivo is not None:
                variaveis = extrair_sinais_mat(arquivo)
                if variaveis:
                    var_selecionada = st.selectbox(
                        f"Selecione a variável do {arquivo.name}:",
                        options=list(variaveis.keys()),
                        key=f"select_{arquivo.name}"
                    )
                    sinal = variaveis[var_selecionada]
                    plotar_sinal_e_fft(sinal, f"{arquivo.name} - Variável: {var_selecionada}", fs=taxa_amostragem)
                else:
                    st.warning("Nenhum vetor numérico 1D encontrado dentro do arquivo .mat.")
            else:
                st.info(f"Faça o upload do {nome_padrao} na barra lateral para exibir a análise.")

# Fluxo de navegação
if st.session_state["authenticated"]:
    main_app()
else:
    check_login()
