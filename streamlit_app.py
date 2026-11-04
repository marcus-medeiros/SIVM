import streamlit as st
from streamlit_echarts import st_echarts, JsCode
import pandas as pd
import numpy as np
import re
import math
import random
from scipy.io import loadmat

# Configuração da página inicial
st.set_page_config(
    page_title="SIVM - Telemetria & Sinais",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicialização de variáveis de sessão
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

# =======================================================================
# 1. DETECÇÃO AUTOMÁTICA DE UNIDADES
# =======================================================================
def extrair_unidade(nome_var: str) -> str:
    """Extrai unidades entre parênteses/colchetes ou por palavras-chave."""
    match = re.search(r"[\(\[]([^\)\]]+)[\)\]]", nome_var)
    if match:
        return match.group(1).strip()

    unidades_conhecidas = {
        "soc": "%",
        "speed": "km/h",
        "velocidade": "km/h",
        "tensao": "V",
        "voltage": "V",
        "corrente": "A",
        "current": "A",
        "potencia": "kW",
        "power": "kW",
        "temperatura": "°C",
        "temp": "°C",
        "torque": "Nm",
        "pressao": "bar",
        "pressure": "bar",
    }
    nome_lower = nome_var.lower()
    for chave, unid in unidades_conhecidas.items():
        if chave in nome_lower:
            return unid
    return ""

# =======================================================================
# 2. TELA DE LOGIN
# =======================================================================
def check_login():
    st.markdown("""
        <style>
            .stApp { background-color: #f0f2f6; }
            .login-title { 
                text-align: center; 
                color: #ce4545; 
                font-weight: bold; 
                margin-bottom: 2rem; 
            }
            div.stButton > button { 
                background-color: #ce4545; 
                color: white; 
                height: 3em; 
                font-weight: bold; 
                border: none;
                border-radius: 6px;
            }
            div.stButton > button:hover { 
                background-color: #a83838; 
                color: white; 
            }
        </style>
    """, unsafe_allow_html=True)

    _, col_login, _ = st.columns([1, 1.2, 1])
    with col_login:
        st.markdown("<h1 class='login-title'>- SIVM -</h1>", unsafe_allow_html=True)
        usuario = st.text_input("👤 Usuário", placeholder="admin")
        senha = st.text_input("🔑 Senha", type="password", placeholder="admin")

        if st.button("Entrar", use_container_width=True):
            if usuario == "admin" and senha == "admin":
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")

# =======================================================================
# 3. PROCESSAMENTO DE ARQUIVOS .MAT
# =======================================================================
def carregar_arquivo_mat(arquivo_upload):
    """Carrega arquivo .mat e extrai vetores numéricos 1D."""
    try:
        conteudo = loadmat(arquivo_upload)
        variaveis = {
            k: np.array(v).flatten()
            for k, v in conteudo.items()
            if not k.startswith("__") and np.issubdtype(np.array(v).dtype, np.number)
        }
        return variaveis
    except Exception as e:
        st.error(f"Erro ao ler {arquivo_upload.name}: {e}")
        return {}

# =======================================================================
# 4. GERAÇÃO DE DADOS DE TESTE (TEMPO INICIANDO EM 0s)
# =======================================================================
def gerar_dados_simulados(num_pontos=360, dt=1.0):
    speed_data = []
    soc_data = []

    speed = 40.0
    soc = 100.0

    for i in range(num_pontos):
        t_sec = round(i * dt, 2)
        speed_change = (random.random() - 0.48) * 4
        speed = max(0.0, min(140.0, speed + speed_change))
        
        soc_drop = (speed / 140.0) * 0.15 + 0.02
        soc = max(0.0, soc - soc_drop)

        speed_data.append([t_sec, round(speed, 2)])
        soc_data.append([t_sec, round(soc, 2)])

    return {
        "speedData": speed_data,
        "socData": soc_data,
    }

# =======================================================================
# 5. PLOTAGEM COM TEMPO DE SIMULAÇÃO (EIXO X NUMÉRICO COMEÇANDO EM 0)
# =======================================================================
def plotar_grafico_duplo_eixo(
    serie_esq,
    serie_dir,
    nome_eixo_esq,
    nome_eixo_dir,
    titulo=None
):
    if not titulo:
        titulo = f"{nome_eixo_esq} vs {nome_eixo_dir}"

    unidade_esq = extrair_unidade(nome_eixo_esq)
    unidade_dir = extrair_unidade(nome_eixo_dir)

    fmt_esq = f"{{value}} {unidade_esq}".strip() if unidade_esq else "{value}"
    fmt_dir = f"{{value}} {unidade_dir}".strip() if unidade_dir else "{value}"

    options = {
        "title": {"text": titulo, "left": "center"},
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "cross"},
            "formatter": JsCode(f"""
                (params) => {{
                    if (!params || params.length === 0) return '';
                    let tempo = params[0].value[0];
                    let res = '<b>Tempo: ' + Number(tempo).toFixed(2) + ' s</b><br/>';
                    params.forEach(item => {{
                        let val = Number(item.value[1]).toFixed(2);
                        let unid = item.seriesIndex === 0 ? '{unidade_esq}' : '{unidade_dir}';
                        res += item.marker + ' ' + item.seriesName + ': <b>' + val + ' ' + unid + '</b><br/>';
                    }});
                    return res;
                }}
            """).js_code,
        },
        "legend": {
            "top": "8%",
            "data": [nome_eixo_esq, nome_eixo_dir],
        },
        "grid": {"left": "6%", "right": "6%", "bottom": "15%", "containLabel": True},
        "xAxis": [
            {
                "type": "value",
                "name": "Tempo (s)",
                "nameLocation": "middle",
                "nameGap": 30,
                "min": 0,
                "axisLabel": {"formatter": "{value} s"},
                "splitLine": {"show": True, "lineStyle": {"type": "dashed"}},
            }
        ],
        "yAxis": [
            {
                "type": "value",
                "name": f"{nome_eixo_esq} ({unidade_esq})" if unidade_esq and unidade_esq not in nome_eixo_esq else nome_eixo_esq,
                "position": "left",
                "scale": True,
                "axisLabel": {"formatter": fmt_esq},
                "axisLine": {"show": True, "lineStyle": {"color": "#4b7bec"}},
                "splitLine": {"show": True, "lineStyle": {"type": "dashed"}},
            },
            {
                "type": "value",
                "name": f"{nome_eixo_dir} ({unidade_dir})" if unidade_dir and unidade_dir not in nome_eixo_dir else nome_eixo_dir,
                "position": "right",
                "scale": True,
                "axisLabel": {"formatter": fmt_dir},
                "axisLine": {"show": True, "lineStyle": {"color": "#20bf6b"}},
                "splitLine": {"show": False},
            },
        ],
        "dataZoom": [
            {"type": "inside", "xAxisIndex": 0},
            {"type": "slider", "xAxisIndex": 0, "bottom": "2%"},
        ],
        "series": [
            {
                "name": nome_eixo_esq,
                "type": "line",
                "yAxisIndex": 0,
                "symbolSize": 0,
                "itemStyle": {"color": "#4b7bec"},
                "areaStyle": {
                    "color": {
                        "type": "linear",
                        "x": 0, "y": 0, "x2": 0, "y2": 1,
                        "colorStops": [
                            {"offset": 0, "color": "rgba(75, 123, 236, 0.6)"},
                            {"offset": 1, "color": "rgba(75, 123, 236, 0.05)"}
                        ]
                    }
                },
                "data": serie_esq,
            },
            {
                "name": nome_eixo_dir,
                "type": "line",
                "yAxisIndex": 1,
                "symbolSize": 0,
                "itemStyle": {"color": "#20bf6b"},
                "lineStyle": {"width": 2.5},
                "data": serie_dir,
            },
        ],
    }

    st_echarts(options=options, height="520px")

# =======================================================================
# 6. APLICAÇÃO PRINCIPAL
# =======================================================================
def main_app():
    with st.sidebar:
        st.markdown("<h2 style='color: #ce4545; text-align: center;'>- SIVM -</h2>", unsafe_allow_html=True)
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state["authenticated"] = False
            st.rerun()

        st.markdown("---")
        st.markdown("### 📂 Upload de Arquivos .mat")
        arquivo_1 = st.file_uploader("Arquivo 1 (.mat)", type=["mat"], key="file1")
        arquivo_2 = st.file_uploader("Arquivo 2 (.mat)", type=["mat"], key="file2")
        
        st.markdown("---")
        st.markdown("### ⏱️ Configuração de Tempo")
        dt_amostragem = st.number_input("Passo de tempo (Δt em segundos)", min_value=0.0001, value=1.0, step=0.1, format="%.4f")

    st.title("Painel de Telemetria Multivariável")

    tab_mat1, tab_mat2, tab_sim = st.tabs(["📁 Arquivo .MAT 1", "📁 Arquivo .MAT 2", "📊 Dados Simulados"])

    # -------------------------------------------------------------------
    # ABA ARQUIVO 1
    # -------------------------------------------------------------------
    with tab_mat1:
        if arquivo_1:
            vars_1 = carregar_arquivo_mat(arquivo_1)
            chaves = list(vars_1.keys())
            if len(chaves) >= 2:
                col1, col2 = st.columns(2)
                var_esq = col1.selectbox("Variável do Eixo Esquerdo (Área):", chaves, key="v1_left")
                var_dir = col2.selectbox("Variável do Eixo Direito (Linha):", chaves, index=1, key="v1_right")

                # Vetor de tempo iniciando em 0.0s com passo dt
                dados_esq = [[round(i * dt_amostragem, 4), float(v)] for i, v in enumerate(vars_1[var_esq])]
                dados_dir = [[round(i * dt_amostragem, 4), float(v)] for i, v in enumerate(vars_1[var_dir])]

                plotar_grafico_duplo_eixo(
                    serie_esq=dados_esq,
                    serie_dir=dados_dir,
                    nome_eixo_esq=var_esq,
                    nome_eixo_dir=var_dir,
                    titulo=f"{arquivo_1.name} — {var_esq} vs {var_dir}"
                )
            else:
                st.warning("O arquivo precisa ter no mínimo 2 variáveis numéricas.")
        else:
            st.info("Envie o Arquivo 1 (.mat) na barra lateral para exibir os dados.")

    # -------------------------------------------------------------------
    # ABA ARQUIVO 2
    # -------------------------------------------------------------------
    with tab_mat2:
        if arquivo_2:
            vars_2 = carregar_arquivo_mat(arquivo_2)
            chaves2 = list(vars_2.keys())
            if len(chaves2) >= 2:
                col3, col4 = st.columns(2)
                var_esq2 = col3.selectbox("Variável do Eixo Esquerdo (Área):", chaves2, key="v2_left")
                var_dir2 = col4.selectbox("Variável do Eixo Direito (Linha):", chaves2, index=1, key="v2_right")

                dados_esq2 = [[round(i * dt_amostragem, 4), float(v)] for i, v in enumerate(vars_2[var_esq2])]
                dados_dir2 = [[round(i * dt_amostragem, 4), float(v)] for i, v in enumerate(vars_2[var_dir2])]

                plotar_grafico_duplo_eixo(
                    serie_esq=dados_esq2,
                    serie_dir=dados_dir2,
                    nome_eixo_esq=var_esq2,
                    nome_eixo_dir=var_dir2,
                    titulo=f"{arquivo_2.name} — {var_esq2} vs {var_dir2}"
                )
            else:
                st.warning("O arquivo precisa ter no mínimo 2 variáveis numéricas.")
        else:
            st.info("Envie o Arquivo 2 (.mat) na barra lateral para exibir os dados.")

    # -------------------------------------------------------------------
    # ABA DADOS SIMULADOS
    # -------------------------------------------------------------------
    with tab_sim:
        st.caption("Sinal simulado iniciando em 0 segundos.")
        sim_data = gerar_dados_simulados(num_pontos=300, dt=dt_amostragem)
        plotar_grafico_duplo_eixo(
            serie_esq=sim_data["speedData"],
            serie_dir=sim_data["socData"],
            nome_eixo_esq="Velocidade (km/h)",
            nome_eixo_dir="SOC_calc (%)",
            titulo="Simulação Numérica: Tempo decorrido a partir de 0s"
        )

# =======================================================================
# 7. CONTROLE DE FLUXO
# =======================================================================
if st.session_state["authenticated"]:
    main_app()
else:
    check_login()
