import streamlit as st
from streamlit_echarts import st_echarts, JsCode
import pandas as pd
import numpy as np
import datetime
import math
import random
from scipy.io import loadmat

# Configuração da página
st.set_page_config(
    page_title="SIVM - Telemetria & Sinais",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicialização de variáveis de sessão
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

# =======================================================================
# 1. TELA DE LOGIN
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
# 2. PROCESSAMENTO DE ARQUIVOS .MAT
# =======================================================================
def carregar_arquivo_mat(arquivo_upload):
    """Carrega arquivo .mat e extrai vetores numéricos válidos."""
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
# 3. GERAÇÃO DE DADOS DE TESTE (FALLBACK QUANDO NÃO HÁ .MAT)
# =======================================================================
def gerar_dados_simulados():
    speed_data = []
    soc_data = []

    start_time = datetime.datetime(2024, 4, 9, 9, 30, tzinfo=datetime.timezone.utc)
    end_time = datetime.datetime(2024, 4, 9, 15, 0, tzinfo=datetime.timezone.utc)
    break_start = datetime.datetime(2024, 4, 9, 11, 30, tzinfo=datetime.timezone.utc)
    break_end = datetime.datetime(2024, 4, 9, 13, 0, tzinfo=datetime.timezone.utc)

    current_time = start_time
    speed = 60.0
    soc = 98.0

    while current_time <= end_time:
        if current_time <= break_start or current_time >= break_end:
            t_ms = int(current_time.timestamp() * 1000)
            
            speed_change = (random.random() - 0.48) * 6
            speed = max(0.0, min(120.0, speed + speed_change))
            
            soc_drop = (speed / 120.0) * 0.35 + 0.05
            soc = max(5.0, soc - soc_drop)

            speed_data.append([t_ms, round(speed, 1)])
            soc_data.append([t_ms, round(soc, 1)])

        current_time += datetime.timedelta(minutes=1)

    return {
        "speedData": speed_data,
        "socData": soc_data,
        "breakStart": int(break_start.timestamp() * 1000),
        "breakEnd": int(break_end.timestamp() * 1000),
    }

# =======================================================================
# 4. PLOTAGEM DO GRÁFICO (ECHARTS COM DUPLO EIXO Y)
# =======================================================================
def plotar_grafico_duplo_eixo(speed_data, soc_data, break_start=None, break_end=None, titulo="Velocidade vs SOC_calc"):
    x_axis_config = {
        "type": "time",
        "interval": 1000 * 60 * 30,
        "axisLabel": {
            "showMinLabel": True,
            "showMaxLabel": True,
            "formatter": JsCode(
                """(value, index, extra) => {
                    if (!extra || !extra.break) {
                        return echarts.time.format(value, '{HH}:{mm}', true);
                    }
                    if (extra.break.type === 'start') {
                        return (
                            echarts.time.format(extra.break.start, '{HH}:{mm}', true) +
                            '/' +
                            echarts.time.format(extra.break.end, '{HH}:{mm}', true)
                        );
                    }
                    return '';
                }"""
            ).js_code,
        },
        "breakLabelLayout": {"moveOverlap": False},
    }

    if break_start and break_end:
        x_axis_config["breaks"] = [{"start": break_start, "end": break_end, "gap": 0}]
        x_axis_config["breakArea"] = {"expandOnClick": False, "zigzagAmplitude": 0, "zigzagZ": 200}

    options = {
        "useUTC": True,
        "title": {"text": titulo, "left": "center"},
        "tooltip": {"show": True, "trigger": "axis", "axisPointer": {"type": "cross"}},
        "legend": {"top": "8%", "data": ["Velocidade (km/h)", "SOC_calc (%)"]},
        "grid": {"left": "6%", "right": "6%", "bottom": "15%", "containLabel": True},
        "xAxis": [x_axis_config],
        "yAxis": [
            {
                "type": "value",
                "name": "Velocidade (km/h)",
                "position": "left",
                "min": 0,
                "axisLine": {"show": True, "lineStyle": {"color": "#4b7bec"}},
                "splitLine": {"show": True, "lineStyle": {"type": "dashed"}},
            },
            {
                "type": "value",
                "name": "SOC (%)",
                "position": "right",
                "min": 0,
                "max": 100,
                "axisLabel": {"formatter": "{value} %"},
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
                "name": "Velocidade (km/h)",
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
                "data": speed_data,
            },
            {
                "name": "SOC_calc (%)",
                "type": "line",
                "yAxisIndex": 1,
                "symbolSize": 0,
                "itemStyle": {"color": "#20bf6b"},
                "lineStyle": {"width": 2.5},
                "data": soc_data,
            },
        ],
    }

    st_echarts(options=options, height="520px")

# =======================================================================
# 5. APLICAÇÃO PRINCIPAL
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

    st.title("Painel de Telemetria: Velocidade e Bateria")

    tab_mat1, tab_mat2, tab_sim = st.tabs(["📁 Arquivo .MAT 1", "📁 Arquivo .MAT 2", "📊 Dados Simulados"])

    # Aba Arquivo 1
    with tab_mat1:
        if arquivo_1:
            vars_1 = carregar_arquivo_mat(arquivo_1)
            if len(vars_1) >= 2:
                c1, c2 = st.columns(2)
                v_speed_k = c1.selectbox("Variável de Velocidade (Eixo Esquerdo):", list(vars_1.keys()), key="v1_speed")
                v_soc_k = c2.selectbox("Variável de SOC (Eixo Direito):", list(vars_1.keys()), index=min(1, len(vars_1)-1), key="v1_soc")

                t_base = int(datetime.datetime(2024, 4, 9, 8, 0, tzinfo=datetime.timezone.utc).timestamp() * 1000)
                speed_s = [[t_base + i * 1000, float(val)] for i, val in enumerate(vars_1[v_speed_k])]
                soc_s = [[t_base + i * 1000, float(val)] for i, val in enumerate(vars_1[v_soc_k])]

                plotar_grafico_duplo_eixo(speed_s, soc_s, titulo=f"{arquivo_1.name}: {v_speed_k} vs {v_soc_k}")
            else:
                st.warning("O arquivo precisa conter pelo menos 2 variáveis numéricas (uma para velocidade e outra para SOC).")
        else:
            st.info("Envie o Arquivo 1 (.mat) na barra lateral para carregar a telemetria.")

    # Aba Arquivo 2
    with tab_mat2:
        if arquivo_2:
            vars_2 = carregar_arquivo_mat(arquivo_2)
            if len(vars_2) >= 2:
                c1, c2 = st.columns(2)
                v_speed_k2 = c1.selectbox("Variável de Velocidade (Eixo Esquerdo):", list(vars_2.keys()), key="v2_speed")
                v_soc_k2 = c2.selectbox("Variável de SOC (Eixo Direito):", list(vars_2.keys()), index=min(1, len(vars_2)-1), key="v2_soc")

                t_base = int(datetime.datetime(2024, 4, 9, 8, 0, tzinfo=datetime.timezone.utc).timestamp() * 1000)
                speed_s2 = [[t_base + i * 1000, float(val)] for i, val in enumerate(vars_2[v_speed_k2])]
                soc_s2 = [[t_base + i * 1000, float(val)] for i, val in enumerate(vars_2[v_soc_k2])]

                plotar_grafico_duplo_eixo(speed_s2, soc_s2, titulo=f"{arquivo_2.name}: {v_speed_k2} vs {v_soc_k2}")
            else:
                st.warning("O arquivo precisa conter pelo menos 2 variáveis numéricas.")
        else:
            st.info("Envie o Arquivo 2 (.mat) na barra lateral para carregar a telemetria.")

    # Aba de Dados Simulados (Demonstração com quebra de intervalo)
    with tab_sim:
        st.caption("Demonstração usando a função geradora sintética com quebra de horário (break time).")
        sim_data = gerar_dados_simulados()
        plotar_grafico_duplo_eixo(
            sim_data["speedData"],
            sim_data["socData"],
            break_start=sim_data["breakStart"],
            break_end=sim_data["breakEnd"],
            titulo="Simulação de Viagem (Intervalo de Almoço das 11:30 às 13:00)"
        )

# =======================================================================
# FLUXO DE EXECUÇÃO
# =======================================================================
if st.session_state["authenticated"]:
    main_app()
else:
    check_login()
