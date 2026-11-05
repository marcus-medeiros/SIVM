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
    page_title="SIVM - Telemetria, Estatística & Simulação",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Passo de tempo de amostragem fixado em 0.1 s
DT_AMOSTRAGEM = 0.1

VARIAVEIS_PLOTAVEIS = [
    "fSpeed_com",
    "fSOC_calc",
    "hSpeed_com",
    "hSOC_calc",
    "fRPM_com",
    "hRPM_com",
    "fThrottle_com",
    "hThrottle_com",
    "fTempBattery_com",
    "hTempBattery_com"
]

# Cores oficiais extraídas das figuras
COR_BOOST = "#702082"        # Roxo
COR_NEUTRO = "#9e9e9e"       # Cinza (ou Cargas Auxiliares / Neutro)
COR_ALTERNADOR = "#f39200"   # Laranja
COR_REGEN = "#008848"        # Verde
COR_CARGAS_AUX = "#424242"   # Cinza Escuro

# Inicialização de variáveis de sessão
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

# =======================================================================
# 1. DETECÇÃO AUTOMÁTICA DE UNIDADES
# =======================================================================
def extrair_unidade(nome_var: str) -> str:
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
# 5. GRÁFICO TEMPORAL MULTIVARIÁVEL (ECHARTS)
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

    st_echarts(options=options, height="480px")

# =======================================================================
# 6. GRÁFICO DE PIZZA (ESTATÍSTICA DAS CONDIÇÕES)
# =======================================================================
def plotar_pizza_condicoes(dados_condicoes, titulo="Distribuição das Condições"):
    pie_data = [{"value": int(v), "name": str(k)} for k, v in dados_condicoes.items() if v > 0]
    total_pontos = sum(item["value"] for item in pie_data) if pie_data else 1

    options = {
        "title": {
            "text": titulo,
            "subtext": "Tempo em cada condição",
            "left": "center",
        },
        "tooltip": {
            "trigger": "item",
            "formatter": "{a} <br/>{b}: <b>{c} amostras</b> ({d}%)"
        },
        "legend": {
            "orient": "vertical",
            "left": "left",
            "formatter": JsCode(f"""
                (name) => {{
                    let data = {pie_data};
                    let total = {total_pontos};
                    let target = data.find(item => item.name === name);
                    if (target) {{
                        let pct = ((target.value / total) * 100).toFixed(1);
                        return name + ': ' + pct + '%';
                    }}
                    return name;
                }}
            """).js_code,
        },
        "series": [
            {
                "name": "Condição",
                "type": "pie",
                "radius": "55%",
                "data": pie_data,
                "label": {
                    "show": True,
                    "formatter": "{b}\n{d}%",
                    "fontSize": 12,
                    "fontWeight": "bold"
                },
                "labelLine": {"show": True, "length": 15, "length2": 10},
                "emphasis": {
                    "itemStyle": {
                        "shadowBlur": 10,
                        "shadowOffsetX": 0,
                        "shadowColor": "rgba(0, 0, 0, 0.5)",
                    }
                },
            }
        ],
    }

    st_echarts(options=options, height="450px")

def extrair_condicoes_automaticamente(vars_dict):
    resultado = {}
    for chave, vetor in vars_dict.items():
        chave_lower = chave.lower()
        if "condicao" in chave_lower or "cond" in chave_lower:
            resultado[chave] = int(np.sum(vetor > 0))
    
    if not resultado:
        for chave, vetor in vars_dict.items():
            chave_lower = chave.lower()
            if any(termo in chave_lower for termo in ["boo", "neu", "alt"]):
                resultado[chave] = int(np.sum(vetor > 0))

    return resultado

# =======================================================================
# 7. GRÁFICOS DO NOVO MÓDULO DE SIMULAÇÃO
# =======================================================================

# 7.1 Gráfico de Barras Horizontais Empilhadas (Tipo Figura 1 com mesmas cores)
def plotar_barras_horizontais_condicoes(ciclos, dados_segmentos):
    """
    ciclos: Lista com os nomes dos ciclos/testes (ex: ['EB HGW', 'ITEMM HGW', 'EB FTP', 'ITEMM FTP'])
    dados_segmentos: Dicionário contendo os valores em porcentagem (%) para cada categoria
    """
    options = {
        "title": {
            "text": "Distribuição Percentual por Condição (100% Empilhado)",
            "left": "center"
        },
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"},
            "formatter": JsCode("""
                (params) => {
                    let res = '<b>' + params[0].name + '</b><br/>';
                    params.forEach(item => {
                        res += item.marker + ' ' + item.seriesName + ': <b>' + item.value + '%</b><br/>';
                    });
                    return res;
                }
            """).js_code
        },
        "legend": {
            "top": "8%",
            "data": ["Boost", "Neutro / Cargas", "Alternador", "Frenagem Reg."]
        },
        "grid": {
            "left": "12%",
            "right": "8%",
            "bottom": "10%",
            "top": "18%",
            "containLabel": True
        },
        "xAxis": {
            "type": "value",
            "max": 100,
            "axisLabel": {"formatter": "{value}%"},
            "splitLine": {"show": True, "lineStyle": {"type": "dashed"}}
        },
        "yAxis": {
            "type": "category",
            "data": ciclos,
            "axisLine": {"show": True}
        },
        "series": [
            {
                "name": "Boost",
                "type": "bar",
                "stack": "total",
                "itemStyle": {"color": COR_BOOST, "borderColor": "#333", "borderWidth": 0.5},
                "label": {"show": True, "formatter": "{c}%", "color": "#fff", "fontWeight": "bold"},
                "data": dados_segmentos["Boost"]
            },
            {
                "name": "Neutro / Cargas",
                "type": "bar",
                "stack": "total",
                "itemStyle": {"color": COR_NEUTRO, "borderColor": "#333", "borderWidth": 0.5},
                "label": {"show": True, "formatter": "{c}%", "color": "#fff", "fontWeight": "bold"},
                "data": dados_segmentos["Neutro"]
            },
            {
                "name": "Alternador",
                "type": "bar",
                "stack": "total",
                "itemStyle": {"color": COR_ALTERNADOR, "borderColor": "#333", "borderWidth": 0.5},
                "label": {"show": True, "formatter": "{c}%", "color": "#fff", "fontWeight": "bold"},
                "data": dados_segmentos["Alternador"]
            },
            {
                "name": "Frenagem Reg.",
                "type": "bar",
                "stack": "total",
                "itemStyle": {"color": COR_REGEN, "borderColor": "#333", "borderWidth": 0.5},
                "label": {"show": True, "formatter": "{c}%", "color": "#fff", "fontWeight": "bold"},
                "data": dados_segmentos["Frenagem"]
            }
        ]
    }
    st_echarts(options=options, height="450px")

# 7.2 Gráfico de Barras com Eixo Positivo e Negativo (Balanço de Carga por Modo)
def plotar_balanco_carga_positivo_negativo(categorias_ciclo, dados_balanco):
    """
    categorias_ciclo: Lista com os ciclos ['ITEMM FTP', 'EB FTP', 'ITEMM HGW', 'EB HGW']
    dados_balanco: Dicionário contendo os valores positivos e negativos de cada modo
    """
    options = {
        "title": {
            "text": "Balanço de Carga por Modo",
            "left": "center"
        },
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"}
        },
        "legend": {
            "top": "8%",
            "data": ["Cargas Auxiliares", "Boost", "Frenagem Regenerativa", "Alternador"]
        },
        "grid": {
            "left": "6%",
            "right": "6%",
            "bottom": "10%",
            "top": "18%",
            "containLabel": True
        },
        "xAxis": {
            "type": "category",
            "data": categorias_ciclo,
            "axisTick": {"alignWithLabel": True},
            "axisLine": {"onZero": True}  # Coloca a linha do eixo exatamente no 0
        },
        "yAxis": {
            "type": "value",
            "name": "Balanço de Carga (Ah)",
            "nameLocation": "middle",
            "nameGap": 35,
            "splitLine": {"show": True, "lineStyle": {"type": "dashed"}}
        },
        "series": [
            {
                "name": "Cargas Auxiliares",
                "type": "bar",
                "itemStyle": {"color": COR_CARGAS_AUX, "borderColor": "#000", "borderWidth": 0.5},
                "label": {"show": True, "position": "bottom", "fontWeight": "bold"},
                "data": dados_balanco["Cargas Auxiliares"]
            },
            {
                "name": "Boost",
                "type": "bar",
                "itemStyle": {"color": COR_BOOST, "borderColor": "#000", "borderWidth": 0.5},
                "label": {"show": True, "position": "bottom", "fontWeight": "bold"},
                "data": dados_balanco["Boost"]
            },
            {
                "name": "Frenagem Regenerativa",
                "type": "bar",
                "itemStyle": {"color": COR_REGEN, "borderColor": "#000", "borderWidth": 0.5},
                "label": {"show": True, "position": "top", "fontWeight": "bold"},
                "data": dados_balanco["Frenagem"]
            },
            {
                "name": "Alternador",
                "type": "bar",
                "itemStyle": {"color": COR_ALTERNADOR, "borderColor": "#000", "borderWidth": 0.5},
                "label": {"show": True, "position": "top", "fontWeight": "bold"},
                "data": dados_balanco["Alternador"]
            }
        ]
    }
    st_echarts(options=options, height="480px")

# =======================================================================
# 8. APLICAÇÃO PRINCIPAL
# =======================================================================
def main_app():
    with st.sidebar:
        st.markdown("<h2 style='color: #ce4545; text-align: center;'>- SIVM -</h2>", unsafe_allow_html=True)
        
        # Menu de Navegação com a nova opção "Simulação"
        pagina_selecionada = st.radio(
            "Selecione o Módulo:",
            options=["📈 Telemetria", "📊 Estatística", "🎯 Simulação"],
            index=0
        )
        st.markdown("---")
        st.markdown("### 📂 Upload de Arquivos .mat")
        arquivo_1 = st.file_uploader("Arquivo 1 (.mat)", type=["mat"], key="file1")
        arquivo_2 = st.file_uploader("Arquivo 2 (.mat)", type=["mat"], key="file2")

        st.markdown("---")
        st.info(f"⏱️ **Passo de Amostragem:** Fixo em `{DT_AMOSTRAGEM} s`")

        if st.button("🚪 Sair", use_container_width=True):
            st.session_state["authenticated"] = False
            st.rerun()

    # -------------------------------------------------------------------
    # MÓDULO 1: TELEMETRIA
    # -------------------------------------------------------------------
    if pagina_selecionada == "📈 Telemetria":
        st.title("Painel de Telemetria Multivariável")

        tab_mat1, tab_mat2 = st.tabs(["📁 Arquivo .MAT 1", "📁 Arquivo .MAT 2"])

        with tab_mat1:
            if arquivo_1:
                vars_1 = carregar_arquivo_mat(arquivo_1)
                chaves = [
                var for var in VARIAVEIS_PLOTAVEIS
                if var in vars_1
                ]
                if len(chaves) >= 2:
                    col1, col2 = st.columns(2)
                    var_esq = col1.selectbox("Variável Esquerda (Área):", chaves, key="v1_left")
                    var_dir = col2.selectbox("Variável Direita (Linha):", chaves, index=1, key="v1_right")

                    dados_esq = [[round(i * DT_AMOSTRAGEM, 2), float(v)] for i, v in enumerate(vars_1[var_esq])]
                    dados_dir = [[round(i * DT_AMOSTRAGEM, 2), float(v)] for i, v in enumerate(vars_1[var_dir])]

                    plotar_grafico_duplo_eixo(
                        serie_esq=dados_esq,
                        serie_dir=dados_dir,
                        nome_eixo_esq=var_esq,
                        nome_eixo_dir=var_dir,
                        titulo=f"{arquivo_1.name} — {var_esq} vs {var_dir}"
                    )
                else:
                    st.warning("O arquivo precisa conter ao menos 2 variáveis numéricas.")
            else:
                st.info("Envie o Arquivo 1 (.mat) na barra lateral para carregar a telemetria.")

        with tab_mat2:
            if arquivo_2:
                vars_2 = carregar_arquivo_mat(arquivo_2)
                chaves2 = [
                var for var in VARIAVEIS_PLOTAVEIS
                if var in vars_2
                ]
                if len(chaves2) >= 2:
                    col3, col4 = st.columns(2)
                    var_esq2 = col3.selectbox("Variável Esquerda (Área):", chaves2, key="v2_left")
                    var_dir2 = col4.selectbox("Variável Direita (Linha):", chaves2, index=1, key="v2_right")

                    dados_esq2 = [[round(i * DT_AMOSTRAGEM, 2), float(v)] for i, v in enumerate(vars_2[var_esq2])]
                    dados_dir2 = [[round(i * DT_AMOSTRAGEM, 2), float(v)] for i, v in enumerate(vars_2[var_dir2])]

                    plotar_grafico_duplo_eixo(
                        serie_esq=dados_esq2,
                        serie_dir=dados_dir2,
                        nome_eixo_esq=var_esq2,
                        nome_eixo_dir=var_dir2,
                        titulo=f"{arquivo_2.name} — {var_esq2} vs {var_dir2}"
                    )
                else:
                    st.warning("O arquivo precisa conter ao menos 2 variáveis numéricas.")
            else:
                st.info("Envie o Arquivo 2 (.mat) na barra lateral para carregar a telemetria.")
    # -------------------------------------------------------------------
    # MÓDULO 2: ESTATÍSTICA (PIZZAS)
    # -------------------------------------------------------------------
    elif pagina_selecionada == "📊 Estatística":
        st.title("Estatística de Condições Operacionais")
        st.markdown("Comparativo percentual de permanência em cada condição de operação.")

        col_arq1, col_arq2 = st.columns(2)

        with col_arq1:
            st.subheader("📁 Arquivo 1")
            if arquivo_1:
                vars_1 = carregar_arquivo_mat(arquivo_1)
                condicoes_1 = extrair_condicoes_automaticamente(vars_1)
                if condicoes_1:
                    plotar_pizza_condicoes(condicoes_1, titulo=f"Condições — {arquivo_1.name}")
                else:
                    st.warning("Nenhuma variável de condição foi identificada no Arquivo 1.")
            else:
                st.info("Faça o upload do Arquivo 1 na barra lateral.")

        with col_arq2:
            st.subheader("📁 Arquivo 2")
            if arquivo_2:
                vars_2 = carregar_arquivo_mat(arquivo_2)
                condicoes_2 = extrair_condicoes_automaticamente(vars_2)
                if condicoes_2:
                    plotar_pizza_condicoes(condicoes_2, titulo=f"Condições — {arquivo_2.name}")
                else:
                    st.warning("Nenhuma variável de condição foi identificada no Arquivo 2.")
            else:
                st.info("Faça o upload do Arquivo 2 na barra lateral.")
    # -------------------------------------------------------------------
    # MÓDULO 3: SIMULAÇÃO (BARRAS HORIZONTAIS 100% E BALANÇO DE CARGA +/-)
    # -------------------------------------------------------------------
    elif pagina_selecionada == "🎯 Simulação":
        st.title("Módulo de Simulação e Balanço Energético")

        # ===============================================================
        # VALORES CONFIGURÁVEIS (Edite diretamente aqui os seus dados)
        # ===============================================================
        
        # 1. Dados do Gráfico de Barras Horizontais Empilhadas (Tipo Figura 1)
        # Ordem de exibição de baixo para cima no eixo Y:
        ciclos_horizontais = ["EB HGW", "ITEMM HGW", "EB FTP", "ITEMM FTP"]
        dados_horizontais = {
            "Boost": [9.3, 8.6, 7.4, 5.4],
            "Neutro": [12.6, 15.0, 43.1, 43.9],
            "Alternador": [49.9, 69.7, 28.7, 38.9],
            "Frenagem": [28.3, 6.8, 20.8, 11.8],
        }

        # 2. Dados do Gráfico de Balanço de Carga (+/-) (Tipo Figura 2)
        ciclos_balanco = ["ITEMM FTP", "EB FTP", "ITEMM HGW", "EB HGW"]
        dados_balanco = {
            "Cargas Auxiliares": [-11.7, -11.7, -9.6, -9.6],
            "Boost": [-3.0, -3.9, -1.9, -2.1],
            "Frenagem": [3.6, 6.6, 1.1, 4.7],
            "Alternador": [10.8, 7.9, 12.1, 8.4],
        }

        # Renderização dos Gráficos
        st.markdown("### 1. Proporção das Condições por Ciclo (Barras Horizontais 100%)")
        plotar_barras_horizontais_condicoes(ciclos_horizontais, dados_horizontais)

        st.markdown("---")

        st.markdown("### 2. Balanço de Carga por Modo (Valores Positivos e Negativos)")
        plotar_balanco_carga_positivo_negativo(ciclos_balanco, dados_balanco)

# =======================================================================
# 9. CONTROLE DE FLUXO
# =======================================================================
if st.session_state["authenticated"]:
    main_app()
else:
    check_login()
