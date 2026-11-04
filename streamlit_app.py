import streamlit as st
from streamlit_echarts import st_echarts, JsCode
import pandas as pd
import numpy as np
import datetime
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
    """Carrega arquivo .mat e extrai vetores numéricos 1D válidos."""
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
# 4. PLOTAGEM DO GRÁFICO (ECHARTS COM DUPLO EIXO Y E LEGENDA DINÂMICA)
# =======================================================================
def plotar_grafico_duplo_eixo(
    speed_data,
    soc_data,
    nome_velocidade="Velocidade",
    nome_soc="SOC_calc",
    break_start=None,
    break_end=None,
    titulo="Telemetria"
):
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
        "legend": {
            "top": "8%",
            "data": [nome_velocidade, nome_soc],
        },
        "grid": {"left": "6%", "right": "6%", "bottom": "15%", "containLabel": True},
        "xAxis": [x_axis_config],
        "yAxis": [
            {
                "type": "value",
                "name": nome_velocidade,
                "position": "left",
                "axisLine": {"show": True, "lineStyle": {"color": "#4b7bec"}},
                "splitLine": {"show": True, "lineStyle": {"type": "dashed"}},
            },
            {
                "type": "value",
                "name": nome_soc,
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
                "name": nome_velocidade,
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
                "name": nome_soc,
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

    # -------------------------------------------------------------------
    # ABA ARQUIVO 1
    # -------------------------------------------------------------------
    with tab_mat1:
        if arquivo_1:
            vars_1 = carregar_arquivo_mat(arquivo_1)
            chaves_validas = list(vars_1.keys())
            if len(chaves_validas) >= 2:
                col_sel1, col_sel2 = st.columns(2)
                v_speed_k = col_sel1.selectbox(
                    "Variável de Velocidade (Eixo Y Esquerdo):",
                    chaves_validas,
                    key="v1_speed"
                )
                v_soc_k = col_sel2.selectbox(
                    "Variável de SOC (Eixo Y Direito):",
                    chaves_validas,
                    index=min(1, len(chaves_validas) - 1),
                    key="v1_soc"
                )

                # Customização das Legendas e Título
                with st.expander("⚙️ Personalizar Rótulos da Legenda e Título", expanded=False):
                    col_l1, col_l2, col_l3 = st.columns(3)
                    label_speed_1 = col_l1.text_input("Legenda (Esquerda):", value=f"{v_speed_k} (km/h)", key="lbl1_speed")
                    label_soc_1 = col_l2.text_input("Legenda (Direita):", value=f"{v_soc_k} (%)", key="lbl1_soc")
                    titulo_1 = col_l3.text_input("Título do Gráfico:", value=f"{arquivo_1.name} - Telemetria", key="title_1")

                t_base = int(datetime.datetime(2024, 4, 9, 8, 0, tzinfo=datetime.timezone.utc).timestamp() * 1000)
                speed_s = [[t_base + i * 1000, float(val)] for i, val in enumerate(vars_1[v_speed_k])]
                soc_s = [[t_base + i * 1000, float(val)] for i, val in enumerate(vars_1[v_soc_k])]

                plotar_grafico_duplo_eixo(
                    speed_data=speed_s,
                    soc_data=soc_s,
                    nome_velocidade=label_speed_1,
                    nome_soc=label_soc_1,
                    titulo=titulo_1
                )
            else:
                st.warning("O arquivo precisa conter ao menos 2 variáveis numéricas.")
        else:
            st.info("Envie o Arquivo 1 (.mat) pela barra lateral para visualizar o gráfico.")

    # -------------------------------------------------------------------
    # ABA ARQUIVO 2
    # -------------------------------------------------------------------
    with tab_mat2:
        if arquivo_2:
            vars_2 = carregar_arquivo_mat(arquivo_2)
            chaves_validas2 = list(vars_2.keys())
            if len(chaves_validas2) >= 2:
                col_sel3, col_sel4 = st.columns(2)
                v_speed_k2 = col_sel3.selectbox(
                    "Variável de Velocidade (Eixo Y Esquerdo):",
                    chaves_validas2,
                    key="v2_speed"
                )
                v_soc_k2 = col_sel4.selectbox(
                    "Variável de SOC (Eixo Y Direito):",
                    chaves_validas2,
                    index=min(1, len(chaves_validas2) - 1),
                    key="v2_soc"
                )

                # Customização das Legendas e Título
                with st.expander("⚙️ Personalizar Rótulos da Legenda e Título", expanded=False):
                    col_l4, col_l5, col_l6 = st.columns(3)
                    label_speed_2 = col_l4.text_input("Legenda (Esquerda):", value=f"{v_speed_k2} (km/h)", key="lbl2_speed")
                    label_soc_2 = col_l5.text_input("Legenda (Direita):", value=f"{v_soc_k2} (%)", key="lbl2_soc")
                    titulo_2 = col_l6.text_input("Título do Gráfico:", value=f"{arquivo_2.name} - Telemetria", key="title_2")

                t_base = int(datetime.datetime(2024, 4, 9, 8, 0, tzinfo=datetime.timezone.utc).timestamp() * 1000)
                speed_s2 = [[t_base + i * 1000, float(val)] for i, val in enumerate(vars_2[v_speed_k2])]
                soc_s2 = [[t_base + i * 1000, float(val)] for i, val in enumerate(vars_2[v_soc_k2])]

                plotar_grafico_duplo_eixo(
                    speed_data=speed_s2,
                    soc_data=soc_s2,
                    nome_velocidade=label_speed_2,
                    nome_soc=label_soc_2,
                    titulo=titulo_2
                )
            else:
                st.warning("O arquivo precisa conter ao menos 2 variáveis numéricas.")
        else:
            st.info("Envie o Arquivo 2 (.mat) pela barra lateral para visualizar o gráfico.")

    # -------------------------------------------------------------------
    # ABA DADOS SIMULADOS
    # -------------------------------------------------------------------
    with tab_sim:
        st.caption("Demonstração usando gerador sintético com intervalo de almoço (breaks no eixo X).")
        
        with st.expander("⚙️ Personalizar Rótulos da Legenda e Título", expanded=False):
            col_ls1, col_ls2, col_ls3 = st.columns(3)
            label_speed_sim = col_ls1.text_input("Legenda (Esquerda):", value="Velocidade (km/h)", key="lbl_sim_spd")
            label_soc_sim = col_ls2.text_input("Legenda (Direita):", value="SOC_calc (%)", key="lbl_sim_soc")
            titulo_sim = col_ls3.text_input("Título do Gráfico:", value="Simulação de Viagem (Intervalo 11:30 às 13:00)", key="title_sim")

        sim_data = gerar_dados_simulados()
        plotar_grafico_duplo_eixo(
            speed_data=sim_data["speedData"],
            soc_data=sim_data["socData"],
            nome_velocidade=label_speed_sim,
            nome_soc=label_soc_sim,
            break_start=sim_data["breakStart"],
            break_end=sim_data["breakEnd"],
            titulo=titulo_sim
        )

# =======================================================================
# 6. FLUXO DE EXECUÇÃO
# =======================================================================
if st.session_state["authenticated"]:
    main_app()
else:
    check_login()
