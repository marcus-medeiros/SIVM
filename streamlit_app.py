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
    page_title="SIVM - Telemetria, Estatística & Análise",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Passo de tempo de amostragem fixado em 0.1 s
DT_AMOSTRAGEM = 0.1

VARIAVEIS_PLOTAVEIS = [
    "fSpeed_com", 
    "fAceleracao_com",
    "fCorrenteBSG_com",
    "fCorrenteFiltro", 
    "fCorrenteConsumoExterno_com",
    "fFluxoVolume_com", 
    "fLoadCarga_com", 
    "fRPM_com", 
    "fSOC_calc", 
    "fTempBattery_com", 
    "fTempCatalisador_com", 
    "fTensaoAC1_norm", 
    "fTensaoBSG_com", 
    "fTensaoChumbo_com", 
    "fTensaoFreio_com", 
    "fThrottle_com",
    "fPowerBattery_com",
    "fEnergia_liquida_Wh",
    "hSpeed_com", 
    "hAceleracao_com",
    "hCorrenteBSG_com",
    "hCorrenteFiltro", 
    "hCorrenteConsumoExterno_com",
    "hFluxoVolume_com",
    "hLoadCarga_com", 
    "hRPM_com", 
    "hSOC_calc", 
    "hTempBattery_com", 
    "hTempCatalisador_com", 
    "hTensaoAC1_norm", 
    "hTensaoBSG_com", 
    "hTensaoChumbo_com", 
    "hTensaoFreio_com", 
    "hThrottle_com",
    "hPowerBattery_com",
    "hEnergia_liquida_Wh"
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
            if usuario == "ITEMM" and senha == "lobos":
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

def identificar_bateria(nome_arquivo):
    """
    Identifica o tipo de bateria pelo nome:
    AGM - L2 - 23092026 - FTP.mat
    AGM - L3 - 24092026 - Highway.mat
    """

    nome = nome_arquivo.upper()

    match = re.search(
        r"AGM\s*-\s*(L2|L3)\s*-\s*(\d{8})\s*-\s*(FTP|HIGHWAY)",
        nome
    )

    if not match:
        raise ValueError(
            f"Nome de arquivo fora do padrão esperado: {nome_arquivo}"
        )

    return match.group(1), match.group(2)

def obter_escalar_mat(variaveis, nome_variavel):
    """Retorna uma variável escalar de um arquivo MAT como float."""
    if nome_variavel not in variaveis:
        raise KeyError(f"A variável '{nome_variavel}' não foi encontrada no arquivo MAT.")

    valores = np.asarray(variaveis[nome_variavel]).reshape(-1)
    if valores.size == 0:
        raise ValueError(f"A variável '{nome_variavel}' está vazia.")

    return float(valores[0])

# =======================================================================
# 5. GRÁFICO TEMPORAL MULTIVARIÁVEL (ECHARTS)
# =======================================================================
def plotar_grafico_duplo_eixo(
    serie_esq,
    serie_dir,
    nome_eixo_esq,
    nome_eixo_dir,
    titulo=None,
    key=None
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

    st_echarts(options=options, height="480px", key=key)

# =======================================================================
# 6. GRÁFICO DE PIZZA (ESTATÍSTICA DAS CONDIÇÕES)
# =======================================================================
def plotar_pizza_condicoes(dados_condicoes, titulo="Distribuição das Condições", key=None):
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

    st_echarts(options=options, height="450px", key=key)

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
            "text": "Distribuição Percentual por Condição (FTP-75 e Highway)",
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
                "data": [round(float(v), 2) for v in dados_segmentos["Boost"]]
            },
            {
                "name": "Neutro / Cargas",
                "type": "bar",
                "stack": "total",
                "itemStyle": {"color": COR_NEUTRO, "borderColor": "#333", "borderWidth": 0.5},
                "label": {"show": True, "formatter": "{c}%", "color": "#fff", "fontWeight": "bold"},
                "data": [round(float(v), 2) for v in dados_segmentos["Neutro"]]
            },
            {
                "name": "Alternador",
                "type": "bar",
                "stack": "total",
                "itemStyle": {"color": COR_ALTERNADOR, "borderColor": "#333", "borderWidth": 0.5},
                "label": {"show": True, "formatter": "{c}%", "color": "#fff", "fontWeight": "bold"},
                "data": [round(float(v), 2) for v in dados_segmentos["Alternador"]]
            },
            {
                "name": "Frenagem Reg.",
                "type": "bar",
                "stack": "total",
                "itemStyle": {"color": COR_REGEN, "borderColor": "#333", "borderWidth": 0.5},
                "label": {"show": True, "formatter": "{c}%", "color": "#fff", "fontWeight": "bold"},
                "data": [round(float(v), 2) for v in dados_segmentos["Frenagem"]]
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
            "text": "Balanço de Carga por Modo (FTP-75 e Highway)",
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
                "data": [round(float(v), 2) for v in dados_balanco["Cargas Auxiliares"]]
            },
            {
                "name": "Boost",
                "type": "bar",
                "itemStyle": {"color": COR_BOOST, "borderColor": "#000", "borderWidth": 0.5},
                "label": {"show": True, "position": "bottom", "fontWeight": "bold"},
                "data": [round(float(v), 2) for v in dados_balanco["Boost"]]
            },
            {
                "name": "Frenagem Regenerativa",
                "type": "bar",
                "itemStyle": {"color": COR_REGEN, "borderColor": "#000", "borderWidth": 0.5},
                "label": {"show": True, "position": "top", "fontWeight": "bold"},
                "data": [round(float(v), 2) for v in dados_balanco["Frenagem"]]
            },
            {
                "name": "Alternador",
                "type": "bar",
                "itemStyle": {"color": COR_ALTERNADOR, "borderColor": "#000", "borderWidth": 0.5},
                "label": {"show": True, "position": "top", "fontWeight": "bold"},
                "data": [round(float(v), 2) for v in dados_balanco["Alternador"]]
            }
        ]
    }
    st_echarts(options=options, height="480px")


def plotar_emissoes_e_tempos(vars_ftp, vars_hgw, nome_ftp, nome_hgw):
    """
    Exibe:
    1. Emissão média, emissão de referência e CO2 total.
    2. Tempos de Start-Stop e Cut-off.
    3. Quantidade de eventos Start-Stop válidos.

    Os nomes dos arquivos MAT são apresentados nos subtítulos.
    """

    ciclos = [
        {
            "nome": "ITEMM FTP",
            "dados": vars_ftp or {},
            "prefixo": "f"
        },
        {
            "nome": "ITEMM HGW",
            "dados": vars_hgw or {},
            "prefixo": "h"
        }
    ]

    nomes_ciclos = [ciclo["nome"] for ciclo in ciclos]

    titulo_arquivos = (
        f"FTP: {nome_ftp} | HIGHWAY: {nome_hgw}"
    )

    # ---------------------------------------------------------
    # EXTRAÇÃO DOS VALORES ESCALARES
    # ---------------------------------------------------------
    def obter_valor(dados, nome):
        bruto = dados.get(nome)

        if bruto is None:
            return None

        try:
            valores = np.asarray(bruto, dtype=float).squeeze()

            if valores.size == 0:
                return None

            valor = float(valores.flat[0])

            return valor if np.isfinite(valor) else None

        except (TypeError, ValueError):
            return None

    # Arredondamento para duas casas decimais
    def arredondar_lista(lista):
        return [
            round(valor, 2) if valor is not None else None
            for valor in lista
        ]

    # Formatador JavaScript: duas casas decimais e vírgula
    formatador_decimal = JsCode("""
        function(params) {
            if (params.value == null || isNaN(params.value)) {
                return '';
            }

            return Number(params.value).toFixed(2).replace('.', ',');
        }
    """)

    formatador_tempo = JsCode("""
        function(params) {
            if (params.value == null || isNaN(params.value)) {
                return '';
            }

            return Number(params.value).toFixed(2).replace('.', ',') + ' s';
        }
    """)

    formatador_tooltip = JsCode("""
        function(value) {
            if (value == null || isNaN(value)) {
                return 'N/D';
            }

            return Number(value).toFixed(2).replace('.', ',');
        }
    """)

    # =========================================================
    # 1. DADOS DE EMISSÃO
    # =========================================================
    emissao_media = []
    emissao_referencia = []
    co2_total = []

    for ciclo in ciclos:
        dados = ciclo["dados"]
        prefixo = ciclo["prefixo"]

        emissao_media.append(
            obter_valor(dados, f"{prefixo}emissao_media_g_km")
        )

        emissao_referencia.append(
            obter_valor(dados, f"{prefixo}emissao_ref")
        )

        co2_total.append(
            obter_valor(dados, f"{prefixo}co2_total_g")
        )

    # Arredondamento dos dados
    emissao_media = arredondar_lista(emissao_media)
    emissao_referencia = arredondar_lista(emissao_referencia)
    co2_total = arredondar_lista(co2_total)

    # ---------------------------------------------------------
    # GRÁFICO DE EMISSÕES
    # ---------------------------------------------------------
    possui_emissao = any(
        valor is not None
        for lista in [
            emissao_media,
            emissao_referencia,
            co2_total
        ]
        for valor in lista
    )

    if possui_emissao:

        opcoes_emissao = {
            "title": {
                "text": "Emissões de CO₂",
                "subtext": titulo_arquivos,
                "left": "center",
                "top": "1%",
                "textStyle": {
                    "fontSize": 17,
                    "fontWeight": "bold"
                },
                "subtextStyle": {
                    "fontSize": 11,
                    "color": "#757575"
                }
            },

            "tooltip": {
                "trigger": "axis",
                "axisPointer": {
                    "type": "shadow"
                },
                "valueFormatter": formatador_tooltip
            },

            "legend": {
                "top": "16%",
                "data": [
                    "Emissão média",
                    "Referência",
                    "CO₂ total"
                ]
            },

            "grid": {
                "left": "10%",
                "right": "15%",
                "bottom": "12%",
                "top": "28%",
                "containLabel": True
            },

            "xAxis": {
                "type": "category",
                "data": nomes_ciclos,
                "axisLabel": {
                    "fontSize": 12
                }
            },

            "yAxis": [
                {
                    "type": "value",
                    "name": "Emissão (g/km)",
                    "position": "left",
                    "nameLocation": "middle",
                    "nameGap": 45
                },
                {
                    "type": "value",
                    "name": "CO₂ total (g)",
                    "position": "right",
                    "nameLocation": "middle",
                    "nameGap": 55,
                    "splitLine": {"show": False
                    }
                }
            ],

            "series": [
                {
                    "name": "Emissão média",
                    "type": "bar",
                    "yAxisIndex": 0,
                    "data": emissao_media,
                    "barMaxWidth": 45,
                    "itemStyle": {
                        "color": "#702082"
                    },
                    "label": {
                        "show": True,
                        "position": "top",
                        "formatter": formatador_decimal
                    }
                },
                {
                    "name": "Referência",
                    "type": "bar",
                    "yAxisIndex": 0,
                    "data": emissao_referencia,
                    "barMaxWidth": 45,
                    "itemStyle": {
                        "color": "#9e9e9e"
                    },
                    "label": {
                        "show": True,
                        "position": "top",
                        "formatter": formatador_decimal
                    }
                },
                {
                    "name": "CO₂ total",
                    "type": "line",
                    "yAxisIndex": 1,
                    "data": co2_total,
                    "symbol": "circle",
                    "symbolSize": 10,
                    "lineStyle": {
                        "width": 3,
                        "color": "#008848"
                    },
                    "itemStyle": {
                        "color": "#008848"
                    },
                    "label": {
                        "show": True,
                        "position": "top",
                        "formatter": formatador_decimal
                    }
                }
            ]
        }

        st_echarts(
            options=opcoes_emissao,
            height="440px",
            key="grafico_emissoes_itemm"
        )

    else:
        st.warning(
            "Não foram encontrados dados de emissão nos arquivos MAT."
        )

    # =========================================================
    # 2. DADOS DE START-STOP E CUT-OFF
    # =========================================================
    tempo_start_stop = []
    tempo_cutoff = []
    eventos_start_stop = []

    for ciclo in ciclos:
        dados = ciclo["dados"]
        prefixo = ciclo["prefixo"]

        tempo_start_stop.append(
            obter_valor(dados, f"{prefixo}s_start_stop")
        )

        tempo_cutoff.append(
            obter_valor(dados, f"{prefixo}s_cut")
        )

        eventos_start_stop.append(
            obter_valor(dados, f"{prefixo}_ss_eventos_validos")
        )

    # Arredondamento dos tempos
    tempo_start_stop = arredondar_lista(tempo_start_stop)
    tempo_cutoff = arredondar_lista(tempo_cutoff)

    # ---------------------------------------------------------
    # GRÁFICO DE TEMPOS
    # ---------------------------------------------------------
    possui_tempos = any(
        valor is not None
        for lista in [
            tempo_start_stop,
            tempo_cutoff
        ]
        for valor in lista
    )

    if possui_tempos:

        opcoes_tempos = {
            "title": {
                "text": "Tempos de Start-Stop e Cut-off",
                "subtext": titulo_arquivos,
                "left": "center",
                "top": "1%",
                "textStyle": {
                    "fontSize": 17,
                    "fontWeight": "bold"
                },
                "subtextStyle": {
                    "fontSize": 11,
                    "color": "#757575"
                }
            },

            "tooltip": {
                "trigger": "axis",
                "axisPointer": {
                    "type": "shadow"
                },
                "valueFormatter": JsCode("""
                    function(value) {
                        if (value == null || isNaN(value)) {
                            return 'N/D';
                        }

                        return Number(value).toFixed(2).replace('.', ',') + ' s';
                    }
                """)
            },

            "legend": {
                "top": "16%",
                "data": [
                    "Start-Stop",
                    "Cut-off"
                ]
            },

            "grid": {
                "left": "10%",
                "right": "5%",
                "bottom": "12%",
                "top": "28%",
                "containLabel": True
            },

            "xAxis": {
                "type": "category",
                "data": nomes_ciclos,
                "axisLabel": {
                    "fontSize": 12
                }
            },

            "yAxis": {
                "type": "value",
                "name": "Tempo (s)",
                "nameLocation": "middle",
                "nameGap": 45
            },

            "series": [
                {
                    "name": "Start-Stop",
                    "type": "bar",
                    "data": tempo_start_stop,
                    "barMaxWidth": 50,
                    "itemStyle": {
                        "color": "#f39200"
                    },
                    "label": {
                        "show": True,
                        "position": "top",
                        "formatter": formatador_tempo
                    }
                },
                {
                    "name": "Cut-off",
                    "type": "bar",
                    "data": tempo_cutoff,
                    "barMaxWidth": 50,
                    "itemStyle": {
                        "color": "#008848"
                    },
                    "label": {
                        "show": True,
                        "position": "top",
                        "formatter": formatador_tempo
                    }
                }
            ]
        }

        st_echarts(
            options=opcoes_tempos,
            height="420px",
            key="grafico_tempos_start_stop_cutoff"
        )

    else:
        st.warning(
            "Não foram encontrados dados de tempo de Start-Stop ou Cut-off."
        )

    # =========================================================
    # 3. QUANTIDADE DE EVENTOS START-STOP
    # =========================================================
    st.subheader("Eventos de Start-Stop")

    col1, col2 = st.columns(2)

    for coluna, nome_ciclo, quantidade in zip(
        [col1, col2],
        nomes_ciclos,
        eventos_start_stop
    ):

        with coluna:

            if quantidade is not None:
                valor_exibido = (
                    f"{quantidade:,.0f}".replace(",", ".")
                )
            else:
                valor_exibido = "N/D"

            st.metric(
                label=f"Eventos válidos — {nome_ciclo}",
                value=valor_exibido
            )




def plotar_kpis_ciclo(variaveis, prefixo, nome_ciclo):
    """
    Exibe seis KPIs do ciclo:

    Primeira linha:
        - Distância percorrida (km)
        - Combustível consumido (L)
        - Autonomia do ciclo (km/L)

    Segunda linha:
        - Capacidade da bateria (Ah)
        - SOC mínimo medido (%)
        - SOC máximo medido (%)
    """

    # ---------------------------------------------------------
    # FUNÇÃO PARA EXTRAIR VALORES ESCALARES
    # ---------------------------------------------------------
    def obter_valor(nome_variavel):
        bruto = variaveis.get(nome_variavel)

        if bruto is None:
            return None

        try:
            valores = np.asarray(bruto, dtype=float).ravel()
            valores = valores[np.isfinite(valores)]

            if valores.size == 0:
                return None

            return float(valores[0])

        except (TypeError, ValueError):
            return None

    # ---------------------------------------------------------
    # FUNÇÃO PARA EXTRAIR SÉRIES TEMPORAIS
    # ---------------------------------------------------------
    def obter_serie(nome_variavel):
        bruto = variaveis.get(nome_variavel)

        if bruto is None:
            return None

        try:
            valores = np.asarray(bruto, dtype=float).ravel()
            valores = valores[np.isfinite(valores)]

            if valores.size == 0:
                return None

            return valores

        except (TypeError, ValueError):
            return None

    # ---------------------------------------------------------
    # FORMATAÇÃO NUMÉRICA BRASILEIRA
    # ---------------------------------------------------------
    def formatar_br(valor):
        if valor is None:
            return "N/D"

        return (
            f"{valor:,.2f}"
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

    # =========================================================
    # 1. EXTRAÇÃO DOS INDICADORES DO CICLO
    # =========================================================

    distancia = obter_valor(
        f"{prefixo}distancia_total_km"
    )

    combustivel = obter_valor(
        f"{prefixo}litros_totais"
    )

    autonomia = obter_valor(
        f"{prefixo}autonomia_final"
    )

    # =========================================================
    # 2. CAPACIDADE DA BATERIA
    # =========================================================

    capacidade_bateria = obter_valor(
        f"{prefixo}Capacidade_Ah"
    )

    # =========================================================
    # 3. SOC MÍNIMO E MÁXIMO MEDIDOS
    # =========================================================

    serie_soc = obter_serie(
        f"{prefixo}SOC_calc"
    )

    if serie_soc is not None:

        soc_min = float(np.min(serie_soc))
        soc_max = float(np.max(serie_soc))

        # Verifica se o SOC está normalizado entre 0 e 1
        if soc_min >= 0 and soc_max <= 1:
            soc_min *= 100
            soc_max *= 100

    else:
        soc_min = None
        soc_max = None

    # =========================================================
    # 4. PRIMEIRA LINHA DE KPIs
    # =========================================================

    st.subheader(f"Indicadores do ciclo — {nome_ciclo}")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="Distância percorrida",
            value=(
                f"{formatar_br(distancia)} km"
                if distancia is not None else "N/D"
            )
        )

    with col2:
        st.metric(
            label="Combustível consumido",
            value=(
                f"{formatar_br(combustivel)} L"
                if combustivel is not None else "N/D"
            )
        )

    with col3:
        st.metric(
            label="Autonomia do ciclo",
            value=(
                f"{formatar_br(autonomia)} km/L"
                if autonomia is not None else "N/D"
            )
        )

    # =========================================================
    # 5. SEGUNDA LINHA DE KPIs
    # =========================================================

    col4, col5, col6 = st.columns(3)

    with col4:
        st.metric(
            label="Capacidade da bateria",
            value=(
                f"{formatar_br(capacidade_bateria)} Ah"
                if capacidade_bateria is not None else "N/D"
            )
        )

    with col5:
        st.metric(
            label="SOC mínimo medido",
            value=(
                f"{formatar_br(soc_min)} %"
                if soc_min is not None else "N/D"
            )
        )

    with col6:
        st.metric(
            label="SOC máximo medido",
            value=(
                f"{formatar_br(soc_max)} %"
                if soc_max is not None else "N/D"
            )
        )


def renderizar_analise_estatistica(arquivo_1, arquivo_2):
    """
    Módulo de análise estatística operacional.

    Permite:
    - Selecionar FTP ou Highway.
    - Selecionar condição operacional.
    - Selecionar variável de interesse.
    - Calcular estatísticas descritivas e percentis.
    - Plotar histograma e curva normal de referência.
    - Plotar heatmaps de densidade operacional.
    """

    # =========================================================
    # 1. FUNÇÕES AUXILIARES
    # =========================================================

    def obter_serie(dados, nome):
        bruto = dados.get(nome)

        if bruto is None:
            return None

        try:
            valores = np.asarray(bruto, dtype=float).ravel()

            if valores.size == 0:
                return None

            return valores

        except (TypeError, ValueError):
            return None

    def formatar_numero(valor, casas=2):
        if valor is None or not np.isfinite(valor):
            return "N/D"

        return (
            f"{valor:,.{casas}f}"
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

    def nome_amigavel(nome, prefixo):
        sufixo = nome[len(prefixo):]

        nomes = {
            "Speed_com": "Velocidade (km/h)",
            "Aceleracao_com": "Aceleração (m/s²)",
            "CorrenteBSG_com": "Corrente BSG (A)",
            "CorrenteFiltro": "Corrente da bateria (A)",
            "CorrenteConsumoExterno_com": "Corrente cargas externas (A)",
            "FluxoVolume_com": "Fluxo volumétrico",
            "FluxoMassa": "Fluxo de massa",
            "LoadCarga_com": "Carga do motor (%)",
            "RPM_com": "Rotação do motor (RPM)",
            "SOC_calc": "SOC (%)",
            "TempBattery_com": "Temperatura da bateria (°C)",
            "TempCatalisador_com": "Temperatura do catalisador (°C)",
            "TensaoAC1_norm": "Tensão AC1",
            "TensaoBSG_com": "Tensão BSG (V)",
            "TensaoChumbo_com": "Tensão da bateria (V)",
            "TensaoFreio_com": "Tensão do freio",
            "Throttle_com": "Pedal do acelerador (%)",
            "PowerBattery_com": "Potência da bateria (W)",
            "PowerBSG_com": "Potência BSG (W)"
        }

        return nomes.get(
            sufixo,
            sufixo.replace("_", " ").title()
        )

    def listar_variaveis(dados, prefixo):
        variaveis = []

        for nome, valor in dados.items():

            if not nome.startswith(prefixo):
                continue

            # Condições operacionais não são variáveis de interesse
            if nome.startswith(f"{prefixo}condicao"):
                continue

            try:
                serie = np.asarray(valor, dtype=float).ravel()

                if serie.size > 1 and np.isfinite(serie).any():
                    variaveis.append(nome)

            except (TypeError, ValueError):
                continue

        return sorted(
            variaveis,
            key=lambda x: nome_amigavel(x, prefixo).lower()
        )

    def extrair_serie_condicionada(
        dados,
        nome_variavel,
        nome_condicao=None
    ):
        serie = obter_serie(dados, nome_variavel)

        if serie is None:
            return np.array([])

        # Todas as amostras
        if nome_condicao is None:
            return serie[np.isfinite(serie)]

        condicao = obter_serie(dados, nome_condicao)

        if condicao is None:
            return np.array([])

        n = min(len(serie), len(condicao))

        serie = serie[:n]
        condicao = condicao[:n]

        mascara = (
            np.isfinite(serie)
            & np.isfinite(condicao)
            & (condicao != 0)
        )

        return serie[mascara]

    def extrair_par_condicionado(
        dados,
        nome_x,
        nome_y,
        nome_condicao=None
    ):
        serie_x = obter_serie(dados, nome_x)
        serie_y = obter_serie(dados, nome_y)

        if serie_x is None or serie_y is None:
            return np.array([]), np.array([])

        if nome_condicao is None:
            n = min(len(serie_x), len(serie_y))

            x = serie_x[:n]
            y = serie_y[:n]

            mascara = np.isfinite(x) & np.isfinite(y)

        else:
            condicao = obter_serie(dados, nome_condicao)

            if condicao is None:
                return np.array([]), np.array([])

            n = min(
                len(serie_x),
                len(serie_y),
                len(condicao)
            )

            x = serie_x[:n]
            y = serie_y[:n]
            condicao = condicao[:n]

            mascara = (
                np.isfinite(x)
                & np.isfinite(y)
                & np.isfinite(condicao)
                & (condicao != 0)
            )

        return x[mascara], y[mascara]

    # =========================================================
    # 2. CARREGAMENTO DOS ARQUIVOS
    # =========================================================

    ciclos = []

    if arquivo_1:
        dados_ftp = carregar_arquivo_mat(arquivo_1)

        if dados_ftp:
            ciclos.append({
                "nome": f"FTP — {arquivo_1.name}",
                "dados": dados_ftp,
                "prefixo": "f"
            })

    if arquivo_2:
        dados_hgw = carregar_arquivo_mat(arquivo_2)

        if dados_hgw:
            ciclos.append({
                "nome": f"Highway — {arquivo_2.name}",
                "dados": dados_hgw,
                "prefixo": "h"
            })

    if not ciclos:
        st.info(
            "Envie pelo menos um arquivo .mat na barra lateral "
            "para iniciar a análise estatística."
        )
        return

    st.title("Análise Estatística das Condições Operacionais")

    # =========================================================
    # 3. SELEÇÃO DO CICLO
    # =========================================================

    nomes_ciclos = [
        ciclo["nome"] for ciclo in ciclos
    ]

    ciclo_selecionado = st.selectbox(
        "Ciclo de condução:",
        nomes_ciclos,
        key="estat_ciclo"
    )

    ciclo = next(
        c for c in ciclos
        if c["nome"] == ciclo_selecionado
    )

    dados = ciclo["dados"]
    prefixo = ciclo["prefixo"]

    # =========================================================
    # 4. SELEÇÃO DA CONDIÇÃO OPERACIONAL
    # =========================================================

    condicoes = {
        "Todas as amostras": None,
        "Alternador": f"{prefixo}condicao_alt",
        "Boost": f"{prefixo}condicao_boo",
        "Frenagem regenerativa": f"{prefixo}condicao_fre",
        "Neutro": f"{prefixo}condicao_neu"
    }

    condicoes_disponiveis = {
        nome: chave
        for nome, chave in condicoes.items()
        if chave is None or chave in dados
    }

    col1, col2 = st.columns(2)

    with col1:
        condicao_selecionada = st.selectbox(
            "Condição operacional:",
            list(condicoes_disponiveis.keys()),
            key=f"estat_condicao_{prefixo}"
        )

    nome_condicao = condicoes_disponiveis[
        condicao_selecionada
    ]

    with col2:

        # =====================================================
        # 5. SELEÇÃO DA VARIÁVEL
        # =====================================================

        variaveis_disponiveis = listar_variaveis(
            dados,
            prefixo
        )

        if not variaveis_disponiveis:
            st.warning(
                "Não foram encontradas séries temporais numéricas "
                "para análise neste arquivo."
            )
            return

        variavel_selecionada = st.selectbox(
            "Variável analisada:",
            variaveis_disponiveis,
            format_func=lambda nome: nome_amigavel(nome, prefixo),
            key=f"estat_variavel_{prefixo}"
        )

    nome_variavel = nome_amigavel(
        variavel_selecionada,
        prefixo
    )

    # =========================================================
    # 6. FILTRAGEM DOS DADOS
    # =========================================================

    valores = extrair_serie_condicionada(
        dados,
        variavel_selecionada,
        nome_condicao
    )

    st.divider()

    st.markdown(
        f"**Ciclo:** {ciclo['nome']}  \n"
        f"**Condição:** {condicao_selecionada}  \n"
        f"**Variável:** {nome_variavel}"
    )

    if len(valores) < 2:
        st.warning(
            "Não existem amostras suficientes para realizar "
            "a análise nesta condição."
        )
        return

    # =========================================================
    # 7. INDICADORES ESTATÍSTICOS
    # =========================================================

    media = float(np.mean(valores))
    mediana = float(np.median(valores))
    desvio = float(np.std(valores, ddof=1))

    minimo = float(np.min(valores))
    maximo = float(np.max(valores))

    percentis = np.percentile(
        valores,
        [10, 25, 50, 75, 90]
    )

    coef_variacao = (
        (desvio / abs(media)) * 100
        if abs(media) > 1e-12
        else None
    )

    st.subheader("Indicadores estatísticos")

    colunas = st.columns(4)

    indicadores = [
        ("Amostras válidas", f"{len(valores):,}".replace(",", ".")),
        ("Média", formatar_numero(media)),
        ("Mediana", formatar_numero(mediana)),
        ("Desvio-padrão", formatar_numero(desvio)),
        ("Mínimo", formatar_numero(minimo)),
        ("Máximo", formatar_numero(maximo)),
        ("Coef. de variação", (
            f"{formatar_numero(coef_variacao)} %"
            if coef_variacao is not None else "N/D"
        )),
        ("Amplitude", formatar_numero(maximo - minimo))
    ]

    for i, (rotulo, valor) in enumerate(indicadores):
        with colunas[i % 4]:
            st.metric(rotulo, valor)

    tabela_percentis = pd.DataFrame({
        "Percentil": ["P10", "P25", "P50", "P75", "P90"],
        "Valor": [
            formatar_numero(v)
            for v in percentis
        ]
    })

    st.markdown("**Distribuição por percentis**")

    st.dataframe(
        tabela_percentis,
        use_container_width=True,
        hide_index=True
    )

    # =========================================================
    # 8. HISTOGRAMA E CURVA NORMAL
    # =========================================================

    st.divider()
    st.subheader("Distribuição de probabilidade")

    quantidade_bins = min(
        30,
        max(5, int(np.sqrt(len(valores))))
    )

    frequencias, limites = np.histogram(
        valores,
        bins=quantidade_bins
    )

    centros = (
        limites[:-1] + limites[1:]
    ) / 2

    largura_bin = float(
        np.mean(np.diff(limites))
    )

    # Distribuição normal de referência
    if desvio > 0:

        pdf_normal = (
            1 / (desvio * np.sqrt(2 * np.pi))
        ) * np.exp(
            -0.5 * ((centros - media) / desvio) ** 2
        )

        frequencia_normal = (
            pdf_normal * len(valores) * largura_bin
        )

    else:
        frequencia_normal = np.zeros_like(centros)

    opcoes_distribuicao = {
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {
                "type": "shadow"
            }
        },

        "legend": {
            "top": "2%",
            "data": [
                "Frequência observada",
                "Normal de referência"
            ]
        },

        "grid": {
            "left": "8%",
            "right": "5%",
            "bottom": "15%",
            "top": "18%",
            "containLabel": True
        },

        "xAxis": {
            "type": "category",
            "name": nome_variavel,
            "nameLocation": "middle",
            "nameGap": 35,
            "data": [
                formatar_numero(v)
                for v in centros
            ],
            "axisLabel": {
                "rotate": 35,
                "interval": "auto"
            },
            "splitLine": {
                "show": False
            }
        },

        "yAxis": {
            "type": "value",
            "name": "Frequência",
            "splitLine": {
                "show": False
            }
        },

        "series": [
            {
                "name": "Frequência observada",
                "type": "bar",
                "data": frequencias.tolist(),
                "barMaxWidth": 35,
                "itemStyle": {
                    "color": "#702082",
                    "opacity": 0.7
                }
            },
            {
                "name": "Normal de referência",
                "type": "line",
                "data": frequencia_normal.tolist(),
                "smooth": True,
                "symbol": "none",
                "lineStyle": {
                    "width": 3,
                    "color": "#008848"
                }
            }
        ]
    }

    st_echarts(
        options=opcoes_distribuicao,
        height="430px",
        key=f"estat_distribuicao_{prefixo}"
    )

    st.caption(
        "A curva normal é uma referência calculada com a média "
        "e o desvio-padrão da amostra. Ela não implica que os "
        "dados sigam necessariamente uma distribuição normal."
    )

    # =========================================================
    # 9. HEATMAPS DE DENSIDADE OPERACIONAL
    # =========================================================

    st.divider()
    st.subheader("Mapas de densidade operacional")

    st.caption(
        "A intensidade da cor representa o percentual de amostras "
        "da condição selecionada em cada região do mapa."
    )

    preditores = [
        ("Velocidade", f"{prefixo}Speed_com"),
        ("SOC", f"{prefixo}SOC_calc"),
        ("RPM", f"{prefixo}RPM_com"),
        ("Carga do motor", f"{prefixo}LoadCarga_com"),
        ("Pedal do acelerador", f"{prefixo}Throttle_com")
    ]

    # Remove variáveis indisponíveis e comparações da variável consigo mesma
    preditores_validos = [
        (nome, chave)
        for nome, chave in preditores
        if chave in dados and chave != variavel_selecionada
    ]

    if not preditores_validos:
        st.info(
            "Não existem variáveis disponíveis para gerar os heatmaps."
        )
        return

    for indice in range(0, len(preditores_validos), 2):

        colunas_heatmap = st.columns(2)

        for posicao in range(2):

            indice_atual = indice + posicao

            if indice_atual >= len(preditores_validos):
                continue

            nome_x, chave_x = preditores_validos[indice_atual]

            x, y = extrair_par_condicionado(
                dados,
                chave_x,
                variavel_selecionada,
                nome_condicao
            )

            with colunas_heatmap[posicao]:

                st.markdown(
                    f"**{nome_x} × {nome_variavel}**"
                )

                if len(x) < 5:
                    st.info(
                        "Amostras insuficientes para este heatmap."
                    )
                    continue

                if np.ptp(x) == 0 or np.ptp(y) == 0:
                    st.info(
                        "Não há variação suficiente nos dados "
                        "para construir este heatmap."
                    )
                    continue

                # Histograma bidimensional
                matriz, limites_x, limites_y = np.histogram2d(
                    x,
                    y,
                    bins=24
                )

                # Conversão para percentual de amostras
                matriz_percentual = (
                    matriz / len(x)
                ) * 100

                rotulos_x = [
                    formatar_numero(
                        (limites_x[i] + limites_x[i + 1]) / 2,
                        1
                    )
                    for i in range(len(limites_x) - 1)
                ]

                rotulos_y = [
                    formatar_numero(
                        (limites_y[i] + limites_y[i + 1]) / 2,
                        1
                    )
                    for i in range(len(limites_y) - 1)
                ]

                dados_heatmap = []

                for i in range(matriz_percentual.shape[0]):
                    for j in range(matriz_percentual.shape[1]):

                        valor = matriz_percentual[i, j]

                        if valor > 0:
                            dados_heatmap.append([
                                i,
                                j,
                                round(float(valor), 3)
                            ])

                maior_percentual = float(
                    np.max(matriz_percentual)
                )

                opcoes_heatmap = {
                    "tooltip": {
                        "position": "top",
                        "formatter": JsCode("""
                            function(params) {
                                return (
                                    'Faixa X: ' + params.value[0] +
                                    '<br>Faixa Y: ' + params.value[1] +
                                    '<br>Concentração: ' +
                                    params.value[2].toFixed(3) + '%'
                                );
                            }
                        """)
                    },

                    "grid": {
                        "left": "15%",
                        "right": "10%",
                        "bottom": "25%",
                        "top": "8%",
                        "containLabel": True
                    },

                    "xAxis": {
                        "type": "category",
                        "name": nome_x,
                        "data": rotulos_x,
                        "splitLine": {
                            "show": False
                        },
                        "axisLabel": {
                            "rotate": 45,
                            "interval": 3,
                            "fontSize": 9
                        }
                    },

                    "yAxis": {
                        "type": "category",
                        "name": nome_variavel,
                        "data": rotulos_y,
                        "splitLine": {
                            "show": False
                        },
                        "axisLabel": {
                            "fontSize": 9
                        }
                    },

                    "visualMap": {
                        "min": 0,
                        "max": maior_percentual,
                        "calculable": True,
                        "orient": "horizontal",
                        "left": "center",
                        "bottom": "0%",
                        "dimension": 2,
                        "text": [
                            "Maior",
                            "Menor"
                        ]
                    },

                    "series": [
                        {
                            "name": "Concentração",
                            "type": "heatmap",
                            "data": dados_heatmap,
                            "emphasis": {
                                "itemStyle": {
                                    "shadowBlur": 8
                                }
                            }
                        }
                    ]
                }

                st_echarts(
                    options=opcoes_heatmap,
                    height="390px",
                    key=(
                        f"heatmap_{prefixo}_"
                        f"{chave_x}_{variavel_selecionada}"
                    )
                )



# =======================================================================
# 8. APLICAÇÃO PRINCIPAL
# =======================================================================
def main_app():
    with st.sidebar:
        st.markdown("<h2 style='color: #ce4545; text-align: center;'>- LOBOS ELETRIFICADOS -</h2>", unsafe_allow_html=True)

        # Menu de navegação
        pagina_selecionada = st.sidebar.radio(
            "Navegação",
            [
                "📈 Telemetria",
                "📊 Estatística",
                "📉 Análise",
                "⚖️ Comparação"
            ]
        )
        st.markdown("---")
        st.markdown("### 📂 Upload de Arquivos .mat")
        arquivo_1 = st.file_uploader("Arquivo FTP (.mat)", type=["mat"], key="file1")
        arquivo_2 = st.file_uploader("Arquivo Highway (.mat)", type=["mat"], key="file2")

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
                        titulo=f"{arquivo_1.name} — {var_esq} vs {var_dir}",
                        key="grafico_arq1"
                    )
                else:
                    st.warning("O arquivo precisa conter ao menos 2 variáveis numéricas.")
                plotar_kpis_ciclo(vars_1, prefixo="f", nome_ciclo="ITEMM FTP")  
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
                        titulo=f"{arquivo_2.name} — {var_esq2} vs {var_dir2}",
                        key="grafico_arq2"
                    )
                else:
                    st.warning("O arquivo precisa conter ao menos 2 variáveis numéricas.")
                plotar_kpis_ciclo(vars_2, prefixo="h", nome_ciclo="ITEMM HGW")  
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
                    plotar_pizza_condicoes(condicoes_1, titulo=f"Condições — {arquivo_1.name}", key="grafico_pizza_arq1")
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
                    plotar_pizza_condicoes(condicoes_2, titulo=f"Condições — {arquivo_2.name}", key="grafico_pizza_arq2")
                else:
                    st.warning("Nenhuma variável de condição foi identificada no Arquivo 2.")
            else:
                st.info("Faça o upload do Arquivo 2 na barra lateral.")

        st.divider()

        renderizar_analise_estatistica(
            arquivo_1,
            arquivo_2
        )

    # -------------------------------------------------------------------
    # MÓDULO 3: ANÁLISE ITEMM
    # -------------------------------------------------------------------
    elif pagina_selecionada == "📉 Análise":

        st.title("Análise de Condições Operacionais — ITEMM")

        st.markdown(
            "Análise dos resultados obtidos nos ensaios ITEMM, "
            "considerando os ciclos FTP e Highway."
        )

        if arquivo_1 and arquivo_2:

            # Carregar arquivos MAT
            vars_ftp = carregar_arquivo_mat(arquivo_1)
            vars_hgw = carregar_arquivo_mat(arquivo_2)

            nome_ftp = arquivo_1.name
            nome_hgw = arquivo_2.name

            titulo_arquivos = (
                f"FTP: {nome_ftp} | HIGHWAY: {nome_hgw}"
            )

            # ---------------------------------------------------------
            # EMISSÕES E TEMPOS DE START-STOP / CUT-OFF
            # ---------------------------------------------------------
            st.divider()

            st.markdown("### 1. Análise de Emissão de CO2 e Start-Stop")

            plotar_emissoes_e_tempos(
                vars_ftp,
                vars_hgw,
                arquivo_1.name,
                arquivo_2.name
            )

            st.divider()

            # Variáveis de distribuição percentual
            variaveis_percentuais_ftp = [
                "fpor_boost",
                "fpor_idle",
                "fpor_alternador",
                "fpor_frenagem"
            ]

            variaveis_percentuais_hgw = [
                "hpor_boost",
                "hpor_idle",
                "hpor_alternador",
                "hpor_frenagem"
            ]

            # Variáveis de capacidade em Ah
            variaveis_capacidade_ftp = [
                "fCapacidade_auxiliares",
                "fCapacidade_boost",
                "fCapacidade_frenagem",
                "fCapacidade_alternador"
            ]

            variaveis_capacidade_hgw = [
                "hCapacidade_auxiliares",
                "hCapacidade_boost",
                "hCapacidade_frenagem",
                "hCapacidade_alternador"
            ]

            # Verificar variáveis ausentes
            faltantes_ftp = [
                nome for nome in (
                    variaveis_percentuais_ftp +
                    variaveis_capacidade_ftp
                )
                if nome not in vars_ftp
            ]

            faltantes_hgw = [
                nome for nome in (
                    variaveis_percentuais_hgw +
                    variaveis_capacidade_hgw
                )
                if nome not in vars_hgw
            ]

            if faltantes_ftp or faltantes_hgw:

                if faltantes_ftp:
                    st.error(
                        "O arquivo FTP não contém estas variáveis: "
                        + ", ".join(faltantes_ftp)
                    )

                if faltantes_hgw:
                    st.error(
                        "O arquivo Highway não contém estas variáveis: "
                        + ", ".join(faltantes_hgw)
                    )

            else:

                # =======================================================
                # 1. DISTRIBUIÇÃO PERCENTUAL POR CONDIÇÃO
                # =======================================================

                ciclos_horizontais = [
                    "ITEMM HGW",
                    "ITEMM FTP"
                ]

                dados_horizontais = {

                    "Boost": [
                        obter_escalar_mat(vars_hgw, "hpor_boost"),
                        obter_escalar_mat(vars_ftp, "fpor_boost")
                    ],

                    "Neutro": [
                        obter_escalar_mat(vars_hgw, "hpor_idle"),
                        obter_escalar_mat(vars_ftp, "fpor_idle")
                    ],

                    "Alternador": [
                        obter_escalar_mat(vars_hgw, "hpor_alternador"),
                        obter_escalar_mat(vars_ftp, "fpor_alternador")
                    ],

                    "Frenagem": [
                        obter_escalar_mat(vars_hgw, "hpor_frenagem"),
                        obter_escalar_mat(vars_ftp, "fpor_frenagem")
                    ]

                }

                st.markdown("### 3. Proporção das Condições por Ciclo (%) ")

                plotar_barras_horizontais_condicoes(
                    ciclos_horizontais,
                    dados_horizontais
                )

                st.markdown("---")

                # =======================================================
                # 2. BALANÇO DE CARGA POR MODO
                # =======================================================

                ciclos_balanco = [
                    "ITEMM FTP",
                    "ITEMM HGW"
                ]

                dados_balanco = {

                    "Cargas Auxiliares": [
                        obter_escalar_mat(
                            vars_ftp,
                            "fCapacidade_auxiliares"
                        ),
                        obter_escalar_mat(
                            vars_hgw,
                            "hCapacidade_auxiliares"
                        )
                    ],

                    "Boost": [
                        obter_escalar_mat(
                            vars_ftp,
                            "fCapacidade_boost"
                        ),
                        obter_escalar_mat(
                            vars_hgw,
                            "hCapacidade_boost"
                        )
                    ],

                    "Frenagem": [
                        obter_escalar_mat(
                            vars_ftp,
                            "fCapacidade_frenagem"
                        ),
                        obter_escalar_mat(
                            vars_hgw,
                            "hCapacidade_frenagem"
                        )
                    ],

                    "Alternador": [
                        obter_escalar_mat(
                            vars_ftp,
                            "fCapacidade_alternador"
                        ),
                        obter_escalar_mat(
                            vars_hgw,
                            "hCapacidade_alternador"
                        )
                    ]

                }

                st.markdown(
                    "### 4. Balanço de Carga por Modo (Ah)"
                )

                plotar_balanco_carga_positivo_negativo(
                    ciclos_balanco,
                    dados_balanco
                )

        else:

            st.info(
                "Envie os dois arquivos MAT: o arquivo com os dados FTP "
                "e o arquivo com os dados Highway."
            )

# =======================================================================
# 9. CONTROLE DE FLUXO
# =======================================================================
if st.session_state["authenticated"]:
    main_app()
else:
    check_login()
