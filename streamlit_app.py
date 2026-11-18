# -*- coding: utf-8 -*-
"""
SIVM - Telemetria, Estatística & Análise (MHEV)

Módulos:
  📈 Telemetria      KPIs, dois eixos livres, velocidade × variável × modos (faixa de modos,
                     sombreado, linha colorida), Ah acumulado por modo
  📊 Estatística     pizzas, estatísticas, histograma, boxplot por modo, heatmaps de densidade
  📉 Análise         emissões, start-stop, proporção por condição, balanço de carga
  🧩 Eventos & KPIs  segmentação por evento, transições, eficiência de regeneração,
                     ineficiências, KPIs avançados, exportação CSV/Excel
  🔗 Correlações     matriz de correlação e dispersão colorida por modo
  ⚖️ Comparação      estatísticas, boxplot, Δ% vs referência, radar, tendência por data,
                     modos, comparação temporal (separada/sobreposta, tempo/distância)

Convenção de nomes dos arquivos: "AGM - L2 - 23092026 - FTP.mat" (bateria - data ddmmaaaa - ciclo)
"""
import hmac
import io
import json
import re
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st
from scipy.io import loadmat
from streamlit_echarts import JsCode, st_echarts

st.set_page_config(
    page_title="SIVM - Telemetria, Estatística & Análise",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =======================================================================
# 0. CONSTANTES
# =======================================================================
DT_AMOSTRAGEM = 0.1      # passo de amostragem fixo (s)
MAX_PTS = 12000          # máximo de pontos desenhados por série (decimação)
MAX_ARQUIVOS_COMPARACAO = 10

COR_BOOST = "#702082"
COR_NEUTRO = "#9e9e9e"
COR_ALTERNADOR = "#f39200"
COR_REGEN = "#008848"
COR_CARGAS_AUX = "#424242"
COR_VEL = "#0077bd"
COR_VAR = "#f05a24"

# Ordem = prioridade crescente na classificação exclusiva (o último sobrescreve)
MODOS = [
    {"cod": "neu", "nome": "Neutro (idle)", "curto": "Neutro", "cor": COR_NEUTRO,
     "sombra": "#a9e5f5", "pct": "por_idle", "cap": "Capacidade_auxiliares"},
    {"cod": "boo", "nome": "Boost", "curto": "Boost", "cor": COR_BOOST,
     "sombra": "#f5dfa0", "pct": "por_boost", "cap": "Capacidade_boost"},
    {"cod": "alt", "nome": "Alternador", "curto": "Alternador", "cor": COR_ALTERNADOR,
     "sombra": "#c9dfb0", "pct": "por_alternador", "cap": "Capacidade_alternador"},
    {"cod": "fre", "nome": "Frenagem Regenerativa", "curto": "Frenagem", "cor": COR_REGEN,
     "sombra": "#e6a9d0", "pct": "por_frenagem", "cap": "Capacidade_frenagem"},
]
NOMES_MODO_IDX = ["Sem modo"] + [m["nome"] for m in MODOS]   # índice 0..4
CURTOS_IDX = ["Sem modo"] + [m["curto"] for m in MODOS]

# sufixo (sem prefixo f/h) -> (nome, unidade)
VARS = {
    "Speed_com": ("Velocidade", "km/h"),
    "Aceleracao_com": ("Aceleração", "m/s²"),
    "CorrenteBSG_com": ("Corrente BSG", "A"),
    "CorrenteFiltro": ("Corrente da bateria", "A"),
    "CorrenteConsumoExterno_com": ("Corrente cargas externas", "A"),
    "FluxoVolume_com": ("Fluxo volumétrico", ""),
    "FluxoMassa": ("Fluxo de massa", ""),
    "LoadCarga_com": ("Carga do motor", "%"),
    "RPM_com": ("Rotação do motor", "RPM"),
    "SOC_calc": ("SOC", "%"),
    "SOH_com": ("SOH", "%"),
    "TempBattery_com": ("Temperatura da bateria", "°C"),
    "TempCatalisador_com": ("Temperatura do catalisador", "°C"),
    "TensaoAC1_norm": ("Tensão AC1", ""),
    "TensaoBSG_com": ("Tensão BSG", "V"),
    "TensaoChumbo_com": ("Tensão da bateria", "V"),
    "TensaoFreio_com": ("Tensão do freio", ""),
    "Throttle_com": ("Pedal do acelerador", "%"),
    "PowerBattery_com": ("Potência da bateria", "W"),
    "PowerBSG_com": ("Potência BSG", "W"),
    "Energia_liquida_Wh": ("Energia líquida acumulada", "Wh"),
}

# KPIs escalares dos arquivos (sufixo -> (rótulo, unidade))
KPIS_ESC = {
    "distancia_total_km": ("Distância", "km"),
    "litros_totais": ("Combustível", "L"),
    "autonomia_final": ("Autonomia", "km/L"),
    "Capacidade_Ah": ("Capacidade da bateria", "Ah"),
    "emissao_media_g_km": ("Emissão média", "g/km"),
    "co2_total_g": ("CO₂ total", "g"),
    "por_boost": ("% Boost", "%"),
    "por_idle": ("% Neutro", "%"),
    "por_alternador": ("% Alternador", "%"),
    "por_frenagem": ("% Frenagem", "%"),
    "Capacidade_boost": ("Ah Boost", "Ah"),
    "Capacidade_auxiliares": ("Ah Cargas aux.", "Ah"),
    "Capacidade_alternador": ("Ah Alternador", "Ah"),
    "Capacidade_frenagem": ("Ah Frenagem", "Ah"),
    "s_start_stop": ("Tempo Start-Stop", "s"),
    "s_cut": ("Tempo Cut-off", "s"),
}

ESTILOS = [
    "Faixa de modos + sombreado",
    "Faixa de modos",
    "Sombreado nos gráficos",
    "Linha colorida + faixa",
]


# =======================================================================
# 1. UTILITÁRIOS
# =======================================================================
def js(codigo: str) -> str:
    """Código JavaScript pronto para uso dentro das opções do ECharts."""
    return JsCode(codigo).js_code


FMT_DEC = js("""function(p){ if (p.value == null || isNaN(p.value)) return '';
    return Number(p.value).toFixed(2).replace('.', ','); }""")
FMT_TEMPO = js("""function(p){ if (p.value == null || isNaN(p.value)) return '';
    return Number(p.value).toFixed(2).replace('.', ',') + ' s'; }""")
FMT_AXIS_BR = js("""function(v){ return Number(v).toFixed(1).replace('.', ','); }""")


def grafico(options: dict, altura: str = "450px", chave: str = None):
    """Renderiza um gráfico ECharts com toolbox de exportação PNG e tema global."""
    options.setdefault("toolbox", {
        "right": "2%",
        "feature": {"saveAsImage": {"title": "Salvar PNG", "pixelRatio": 2}},
    })
    tema = "dark" if st.session_state.get("tema_escuro") else ""
    st_echarts(options=options, height=altura, key=chave, theme=tema)


def fmt_br(valor, casas: int = 2) -> str:
    if valor is None:
        return "N/D"
    try:
        if not np.isfinite(valor):
            return "N/D"
    except TypeError:
        return "N/D"
    return f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def get_serie(dados: dict, nome: str):
    """Série numérica (float) ou None."""
    bruto = dados.get(nome)
    if bruto is None:
        return None
    try:
        v = np.asarray(bruto, dtype=float).ravel()
    except (TypeError, ValueError):
        return None
    return v if v.size > 0 else None


def get_escalar(dados: dict, nome: str):
    v = get_serie(dados, nome)
    if v is None:
        return None
    v = v[np.isfinite(v)]
    return float(v[0]) if v.size else None


def soc_percentual(serie):
    """SOC em %, tratando séries normalizadas em 0-1."""
    if serie is None:
        return None
    s = serie[np.isfinite(serie)]
    if s.size == 0:
        return None
    return serie * 100 if (s.min() >= 0 and s.max() <= 1) else serie


def rotulo_var(sufixo: str, com_unidade: bool = True) -> str:
    nome, un = VARS.get(sufixo, (sufixo.replace("_", " "), ""))
    return f"{nome} ({un})" if (un and com_unidade) else nome


def unidade_var(sufixo: str) -> str:
    return VARS.get(sufixo, ("", ""))[1]


def listar_series(dados: dict, prefixo: str) -> list:
    """Sufixos das séries temporais (mesmo comprimento da velocidade)."""
    vel = get_serie(dados, f"{prefixo}Speed_com")
    tamanhos = [np.asarray(v).size for k, v in dados.items() if k.startswith(prefixo)]
    n_ref = len(vel) if vel is not None else (max(tamanhos) if tamanhos else 0)
    achados = []
    for nome, valor in dados.items():
        if not nome.startswith(prefixo):
            continue
        suf = nome[len(prefixo):]
        if suf.startswith("condicao"):
            continue
        v = np.asarray(valor)
        if v.size == n_ref and v.size > 1 and np.isfinite(v.astype(float)).any():
            achados.append(suf)
    ordem = list(VARS.keys())
    return sorted(achados, key=lambda s: (ordem.index(s) if s in ordem else 999, s))


def vetor_modos(dados: dict, prefixo: str, n: int) -> np.ndarray:
    """Classificação exclusiva: 0 = sem modo, 1..4 = índice em MODOS (prioridade crescente)."""
    modos = np.zeros(n, dtype=np.int8)
    for i, m in enumerate(MODOS, start=1):
        c = get_serie(dados, f"{prefixo}condicao_{m['cod']}")
        if c is None:
            continue
        k = min(n, len(c))
        ativo = np.isfinite(c[:k]) & (c[:k] > 0)
        modos[:k][ativo] = i
    return modos


def segmentos(mascara: np.ndarray):
    """Início e fim (exclusivo) de cada trecho contínuo True."""
    m = np.concatenate([[0], mascara.astype(np.int8), [0]])
    d = np.diff(m)
    return np.flatnonzero(d == 1), np.flatnonzero(d == -1)


def mascara_filtro(dados: dict, prefixo: str, n: int) -> np.ndarray:
    """Filtro global de velocidade definido na barra lateral."""
    mask = np.ones(n, dtype=bool)
    lo, hi = st.session_state.get("filtro_vel", (0, 200))
    if lo <= 0 and hi >= 200:
        return mask
    vel = get_serie(dados, f"{prefixo}Speed_com")
    if vel is None:
        return mask
    k = min(n, len(vel))
    mask[:k] = (vel[:k] >= lo) & (vel[:k] <= (hi if hi < 200 else np.inf))
    mask[k:] = False
    return mask


def extrair(dados, prefixo, nomes, cod=None, com_modos=False, filtrar=True):
    """
    Séries alinhadas, apenas amostras finitas, na condição `cod` (ou todas)
    e dentro do filtro global. Se com_modos=True, acrescenta o vetor de modos.
    """
    vazio = [np.array([])] * (len(nomes) + (1 if com_modos else 0))
    arrs = [get_serie(dados, nm) for nm in nomes]
    if any(a is None for a in arrs):
        return vazio
    n = min(len(a) for a in arrs)
    cond = None
    if cod:
        cond = get_serie(dados, f"{prefixo}condicao_{cod}")
        if cond is None:
            return vazio
        n = min(n, len(cond))
    mask = np.ones(n, dtype=bool)
    for a in arrs:
        mask &= np.isfinite(a[:n])
    if cond is not None:
        mask &= np.isfinite(cond[:n]) & (cond[:n] > 0)
    if filtrar:
        mask &= mascara_filtro(dados, prefixo, n)
    saida = [a[:n][mask] for a in arrs]
    if com_modos:
        saida.append(vetor_modos(dados, prefixo, n)[mask])
    return saida


def to_pts(x, y, extra=None):
    """Pares [x, y(, extra)] serializáveis, com NaN -> None."""
    xs = np.round(np.asarray(x, dtype=float), 3).tolist()
    ys = np.round(np.asarray(y, dtype=float), 4).tolist()
    ys = [None if v != v else v for v in ys]
    if extra is None:
        return [[a, b] for a, b in zip(xs, ys)]
    return [[a, b, c] for a, b, c in zip(xs, ys, np.asarray(extra).tolist())]


def passo_decimacao(n: int) -> int:
    return max(1, n // MAX_PTS)


def parse_nome(nome_arquivo: str):
    """'AGM - L2 - 23092026 - FTP.mat' -> {'bateria','data','ciclo'} ou None."""
    m = re.search(r"(L\d+)\s*-\s*(\d{8})\s*-\s*(FTP|HIGHWAY|HGW)", nome_arquivo, re.I)
    if not m:
        return None
    try:
        data = datetime.strptime(m.group(2), "%d%m%Y")
    except ValueError:
        return None
    ciclo = "FTP" if m.group(3).upper() == "FTP" else "HIGHWAY"
    return {"bateria": m.group(1).upper(), "data": data, "ciclo": ciclo}


def identificar_bateria(nome_arquivo: str):
    info = parse_nome(nome_arquivo)
    if not info:
        raise ValueError(f"Nome de arquivo fora do padrão esperado: {nome_arquivo}")
    return info["bateria"], info["data"].strftime("%d%m%Y")


def excel_bytes(abas: dict):
    try:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            for nome, df in abas.items():
                df.to_excel(w, sheet_name=nome[:31], index=False)
        return buf.getvalue()
    except Exception:
        return None


def csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")


# =======================================================================
# 2. LEITURA DE ARQUIVOS .MAT (com cache)
# =======================================================================
@st.cache_resource(show_spinner="Lendo arquivo .mat...", max_entries=24)
def _ler_mat(conteudo: bytes) -> dict:
    bruto = loadmat(io.BytesIO(conteudo))
    saida = {}
    for k, v in bruto.items():
        if k.startswith("__"):
            continue
        a = np.asarray(v)
        if a.dtype == bool or (np.issubdtype(a.dtype, np.number)
                               and not np.issubdtype(a.dtype, np.complexfloating)):
            saida[k] = a.astype(float).ravel()
    return saida


def carregar_arquivo_mat(arquivo_upload) -> dict:
    try:
        return _ler_mat(arquivo_upload.getvalue())
    except Exception as e:
        st.error(f"Erro ao ler {getattr(arquivo_upload, 'name', 'arquivo')}: {e}")
        return {}


def ciclos_carregados(arquivo_1, arquivo_2) -> list:
    ciclos = []
    for arq, pref, rot in ((arquivo_1, "f", "FTP"), (arquivo_2, "h", "Highway")):
        if arq:
            d = carregar_arquivo_mat(arq)
            if d:
                ciclos.append({"nome": f"{rot} — {arq.name}", "dados": d, "prefixo": pref, "rotulo": rot})
    return ciclos


# =======================================================================
# 3. LOGIN
# =======================================================================
def _igual(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def check_login():
    st.markdown("""
        <style>
            .stApp { background-color: #f0f2f6; }
            .login-title { text-align:center; color:#ce4545; font-weight:bold; margin-bottom:2rem; }
            div.stButton > button { background-color:#ce4545; color:white; height:3em;
                                    font-weight:bold; border:none; border-radius:6px; }
            div.stButton > button:hover { background-color:#a83838; color:white; }
        </style>
    """, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown("<h1 class='login-title'>- SIVM -</h1>", unsafe_allow_html=True)
        usuario = st.text_input("👤 Usuário")
        senha = st.text_input("🔑 Senha", type="password")
        tentativas = st.session_state.get("tentativas", 0)

        if tentativas >= 5:
            st.error("Muitas tentativas incorretas. Recarregue a página para tentar novamente.")
            return

        if st.button("Entrar", use_container_width=True):
            ok = _igual(usuario, str(st.secrets["USER_MASTER"])) and \
                 _igual(senha, str(st.secrets["PASSWORD_MASTER"]))
            if ok:
                st.session_state["authenticated"] = True
                st.session_state["tentativas"] = 0
                st.rerun()
            else:
                st.session_state["tentativas"] = tentativas + 1
                st.error("Usuário ou senha incorretos.")


# =======================================================================
# 4. COMPONENTES GRÁFICOS GENÉRICOS
# =======================================================================
def heatmap_2d(x, y, nome_x, nome_y, chave, altura="400px", bins=24, titulo=None):
    """Heatmap de densidade (% das amostras por célula)."""
    if len(x) < 5:
        st.info("Amostras insuficientes para este heatmap.")
        return
    if np.ptp(x) == 0 or np.ptp(y) == 0:
        st.info("Não há variação suficiente nos sinais para construir este heatmap.")
        return

    matriz, ex, ey = np.histogram2d(x, y, bins=bins)
    pct = matriz / len(x) * 100
    rx = [fmt_br((ex[i] + ex[i + 1]) / 2, 1) for i in range(bins)]
    ry = [fmt_br((ey[i] + ey[i + 1]) / 2, 1) for i in range(bins)]
    dados = [[int(i), int(j), round(float(pct[i, j]), 3)] for i, j in zip(*np.nonzero(pct))]

    tooltip = js("""function(p){
        const rx = __RX__; const ry = __RY__;
        return '<b>' + __TIT__ + '</b><br>' + __NX__ + ': ' + rx[p.value[0]] +
               '<br>' + __NY__ + ': ' + ry[p.value[1]] +
               '<br>Concentração: ' + Number(p.value[2]).toFixed(3).replace('.', ',') + '%';
    }""".replace("__RX__", json.dumps(rx, ensure_ascii=False))
         .replace("__RY__", json.dumps(ry, ensure_ascii=False))
         .replace("__TIT__", json.dumps(titulo or f"{nome_x} × {nome_y}", ensure_ascii=False))
         .replace("__NX__", json.dumps(nome_x, ensure_ascii=False))
         .replace("__NY__", json.dumps(nome_y, ensure_ascii=False)))

    opcoes = {
        "tooltip": {"position": "top", "formatter": tooltip},
        "grid": {"left": "17%", "right": "8%", "bottom": "25%", "top": "8%", "containLabel": True},
        "xAxis": {"type": "category", "name": nome_x, "nameLocation": "middle", "nameGap": 40,
                  "data": rx, "splitLine": {"show": False},
                  "axisLabel": {"rotate": 45, "interval": 3, "fontSize": 9}},
        "yAxis": {"type": "category", "name": nome_y, "nameLocation": "middle", "nameGap": 55,
                  "data": ry, "splitLine": {"show": False}, "axisLabel": {"fontSize": 9}},
        "visualMap": {"min": 0, "max": float(pct.max()), "calculable": True, "orient": "horizontal",
                      "left": "center", "bottom": "0%", "dimension": 2, "text": ["Maior", "Menor"],
                      "inRange": {"color": ["#f7f1fb", "#b388c9", "#702082", "#2d0b36"]}},
        "series": [{"name": "Concentração", "type": "heatmap", "data": dados,
                    "emphasis": {"itemStyle": {"shadowBlur": 8}}}],
    }
    grafico(opcoes, altura, chave)
    st.caption(f"Amostras utilizadas: {fmt_br(len(x), 0)}")


def barras_agrupadas(categorias, series_dict, cores, titulo, subtitulo, unidade, chave, rotacao=35):
    """Barras agrupadas (uma série por modo) com rótulos em formato BR."""
    series = []
    for nome, valores in series_dict.items():
        series.append({
            "name": nome, "type": "bar", "barMaxWidth": 28, "data": valores,
            "itemStyle": {"color": cores[nome]},
            "label": {"show": True, "position": "top", "fontSize": 9, "formatter": FMT_DEC},
        })
    opcoes = {
        "title": {"text": titulo, "subtext": subtitulo, "left": "center", "top": "2%",
                  "textStyle": {"fontSize": 16}},
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
        "legend": {"top": "14%", "data": list(series_dict.keys())},
        "grid": {"left": "8%", "right": "5%", "bottom": "22%", "top": "26%", "containLabel": True},
        "xAxis": {"type": "category", "data": categorias,
                  "axisLabel": {"rotate": rotacao, "interval": 0, "fontSize": 9}},
        "yAxis": {"type": "value", "name": unidade, "splitLine": {"show": False}},
        "series": series,
    }
    grafico(opcoes, "500px", chave)


# =======================================================================
# 5. GRÁFICOS TEMPORAIS
# =======================================================================
def plotar_grafico_duplo_eixo(dados, prefixo, suf_esq, suf_dir, titulo, chave):
    """Dois eixos livres: variável esquerda (área) × variável direita (linha)."""
    a = get_serie(dados, f"{prefixo}{suf_esq}")
    b = get_serie(dados, f"{prefixo}{suf_dir}")
    if a is None or b is None:
        st.warning("Não foi possível extrair as variáveis selecionadas.")
        return
    passo = passo_decimacao(max(len(a), len(b)))
    ta = np.arange(len(a))[::passo] * DT_AMOSTRAGEM
    tb = np.arange(len(b))[::passo] * DT_AMOSTRAGEM
    nome_e, nome_d = rotulo_var(suf_esq), rotulo_var(suf_dir)

    tooltip = js("""function(params){
        if (!params || !params.length) return '';
        let r = '<b>Tempo: ' + Number(params[0].value[0]).toFixed(2).replace('.', ',') + ' s</b><br/>';
        params.forEach(function(it){
            if (!it.value || it.value[1] == null) return;
            r += it.marker + ' ' + it.seriesName + ': <b>' +
                 Number(it.value[1]).toFixed(2).replace('.', ',') + '</b><br/>';
        });
        return r; }""")

    opcoes = {
        "title": {"text": titulo, "left": "center"},
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "cross"}, "formatter": tooltip},
        "legend": {"top": "8%", "data": [nome_e, nome_d]},
        "grid": {"left": "6%", "right": "6%", "bottom": "15%", "top": "18%", "containLabel": True},
        "xAxis": [{"type": "value", "name": "Tempo (s)", "nameLocation": "middle", "nameGap": 30,
                   "min": 0, "axisLabel": {"formatter": "{value} s"},
                   "splitLine": {"show": True, "lineStyle": {"type": "dashed"}}}],
        "yAxis": [
            {"type": "value", "name": nome_e, "position": "left", "scale": True,
             "axisLine": {"show": True, "lineStyle": {"color": "#4b7bec"}},
             "splitLine": {"show": True, "lineStyle": {"type": "dashed"}}},
            {"type": "value", "name": nome_d, "position": "right", "scale": True,
             "axisLine": {"show": True, "lineStyle": {"color": "#20bf6b"}},
             "splitLine": {"show": False}},
        ],
        "dataZoom": [{"type": "inside", "xAxisIndex": 0},
                     {"type": "slider", "xAxisIndex": 0, "bottom": "2%"}],
        "series": [
            {"name": nome_e, "type": "line", "yAxisIndex": 0, "symbolSize": 0,
             "itemStyle": {"color": "#4b7bec"},
             "areaStyle": {"color": {"type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1,
                                     "colorStops": [{"offset": 0, "color": "rgba(75,123,236,0.6)"},
                                                    {"offset": 1, "color": "rgba(75,123,236,0.05)"}]}},
             "data": to_pts(ta, a[::passo])},
            {"name": nome_d, "type": "line", "yAxisIndex": 1, "symbolSize": 0,
             "itemStyle": {"color": "#20bf6b"}, "lineStyle": {"width": 2.5},
             "data": to_pts(tb, b[::passo])},
        ],
    }
    grafico(opcoes, "480px", chave)


def _distancia_km(vel: np.ndarray) -> np.ndarray:
    v = np.nan_to_num(vel) / 3.6 * DT_AMOSTRAGEM
    return (np.concatenate([[0.0], np.cumsum(v[:-1])])) / 1000.0


def _intervalos_modo(modos, x, idx_modo):
    ini, fim = segmentos(modos == idx_modo)
    passo_x = (x[-1] - x[-2]) if len(x) > 1 else DT_AMOSTRAGEM
    saida = []
    for i, f in zip(ini, fim):
        x0 = float(x[i])
        x1 = float(x[f]) if f < len(x) else float(x[-1] + passo_x)
        saida.append([{"xAxis": round(x0, 3)}, {"xAxis": round(x1, 3)}])
    return saida


def grafico_temporal(dados, prefixo, sufixo_dir, subtitulo, chave, estilo=ESTILOS[0],
                     modos_sel=None, janela=None, eixo_x="Tempo (s)", fases=None):
    """
    Velocidade (eixo esquerdo) × variável (eixo direito) com visualização dos modos:
    faixa de modos alinhada abaixo, sombreado, e/ou linha de velocidade colorida pelo modo.
    """
    vel = get_serie(dados, f"{prefixo}Speed_com")
    dire = get_serie(dados, f"{prefixo}{sufixo_dir}")
    if vel is None or dire is None:
        st.warning(f"Não foi possível extrair velocidade ou {rotulo_var(sufixo_dir)}.")
        return
    n = min(len(vel), len(dire))
    if n < 2:
        st.warning("Não existem amostras suficientes.")
        return
    vel, dire = vel[:n], dire[:n]
    modos = vetor_modos(dados, prefixo, n)
    por_tempo = eixo_x.startswith("Tempo")
    x = np.arange(n) * DT_AMOSTRAGEM if por_tempo else _distancia_km(vel)

    i0, i1 = 0, n
    if janela:
        i0 = max(0, int(janela[0] / DT_AMOSTRAGEM))
        i1 = min(n, int(janela[1] / DT_AMOSTRAGEM) + 1)
    if i1 - i0 < 2:
        st.warning("Janela de tempo muito curta.")
        return
    x, vel, dire, modos = x[i0:i1], vel[i0:i1], dire[i0:i1], modos[i0:i1]

    modos_sel = modos_sel or list(range(1, len(MODOS) + 1))
    faixa = estilo in (ESTILOS[0], ESTILOS[1], ESTILOS[3])
    sombra = estilo in (ESTILOS[0], ESTILOS[2])
    colorida = estilo == ESTILOS[3]

    legenda = ["Velocidade", rotulo_var(sufixo_dir)]
    series = []
    for k, m in enumerate(MODOS, start=1):
        if k not in modos_sel:
            continue
        inter = _intervalos_modo(modos, x, k)
        if not inter:
            continue
        legenda.append(m["nome"])
        base = {"name": m["nome"], "type": "line", "data": [], "symbol": "none",
                "lineStyle": {"color": m["cor"], "width": 3}, "itemStyle": {"color": m["cor"]}}
        if sombra:
            series.append({**base, "xAxisIndex": 0, "yAxisIndex": 0,
                           "markArea": {"silent": True, "itemStyle": {"color": m["sombra"], "opacity": 0.45},
                                        "data": inter}})
        if faixa:
            series.append({**base, "xAxisIndex": 1, "yAxisIndex": 1,
                           "markArea": {"silent": True, "itemStyle": {"color": m["cor"], "opacity": 0.92},
                                        "data": inter}})

    passo = passo_decimacao(len(x))
    sl = slice(None, None, passo)
    idx_vel = len(series)
    serie_vel = {
        "name": "Velocidade", "type": "line", "xAxisIndex": 0, "yAxisIndex": 0,
        "data": to_pts(x[sl], vel[sl], modos[sl]), "showSymbol": False, "z": 5,
        "lineStyle": {"color": COR_VEL, "width": 2.5}, "itemStyle": {"color": COR_VEL},
        "areaStyle": {"color": {"type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1,
                                "colorStops": [{"offset": 0, "color": "rgba(0,119,189,0.15)"},
                                               {"offset": 1, "color": "rgba(0,119,189,0.02)"}]}},
        "markPoint": {"symbolSize": 42, "data": [{"type": "max", "name": "Máx"}]},
    }
    if fases and por_tempo:
        pts = [{"xAxis": float(t), "name": nome} for nome, t in fases if x[0] <= t <= x[-1]]
        if pts:
            serie_vel["markLine"] = {"silent": True, "symbol": "none",
                                     "lineStyle": {"type": "dashed", "color": "#888"},
                                     "label": {"formatter": "{b}", "fontSize": 10}, "data": pts}
    series.append(serie_vel)
    series.append({
        "name": rotulo_var(sufixo_dir), "type": "line", "xAxisIndex": 0, "yAxisIndex": 1,
        "data": to_pts(x[sl], dire[sl]), "showSymbol": False, "z": 6,
        "lineStyle": {"color": COR_VAR, "width": 2}, "itemStyle": {"color": COR_VAR},
        "markPoint": {"symbolSize": 42, "data": [{"type": "max", "name": "Máx"}, {"type": "min", "name": "Mín"}]},
        "markLine": {"silent": True, "symbol": "none", "lineStyle": {"type": "dashed", "color": COR_VAR},
                     "label": {"formatter": "Média: {c}"}, "data": [{"type": "average", "name": "Média"}]},
    })

    rot_x = "Tempo (s)" if por_tempo else "Distância (km)"
    tooltip = js("""function(params){
        if (!params || !params.length) return '';
        const nomes = __NOMES__;
        let r = '<b>__XL__: ' + Number(params[0].value[0]).toFixed(2).replace('.', ',') + '</b><br/>';
        params.forEach(function(it){
            if (!it.value || it.value[1] == null) return;
            r += it.marker + ' ' + it.seriesName + ': <b>' +
                 Number(it.value[1]).toFixed(2).replace('.', ',') + '</b><br/>';
            if (it.value.length > 2 && it.value[2] != null)
                r += '&nbsp;&nbsp;&nbsp;Modo: ' + nomes[it.value[2]] + '<br/>';
        });
        return r; }""".replace("__NOMES__", json.dumps(NOMES_MODO_IDX, ensure_ascii=False))
                 .replace("__XL__", rot_x))

    xmin, xmax = round(float(x[0]), 3), round(float(x[-1]), 3)
    eixo_base = {"type": "value", "min": xmin, "max": xmax,
                 "splitLine": {"show": True, "lineStyle": {"type": "dashed", "opacity": 0.35}}}
    if faixa:
        grids = [{"left": "7%", "right": "7%", "top": "24%", "height": "46%", "containLabel": True},
                 {"left": "7%", "right": "7%", "top": "76%", "height": "6%", "containLabel": True}]
        xaxes = [{**eixo_base, "gridIndex": 0, "axisLabel": {"show": False}},
                 {**eixo_base, "gridIndex": 1, "name": rot_x, "nameLocation": "middle", "nameGap": 28,
                  "splitLine": {"show": False}}]
        yaxes_extra = [{"type": "value", "gridIndex": 1, "min": 0, "max": 1, "show": False}]
        zoom_idx, altura = [0, 1], "640px"
    else:
        grids = [{"left": "7%", "right": "7%", "top": "24%", "bottom": "18%", "containLabel": True}]
        xaxes = [{**eixo_base, "gridIndex": 0, "name": rot_x, "nameLocation": "middle", "nameGap": 30}]
        yaxes_extra, zoom_idx, altura = [], [0], "560px"

    yaxes = [
        {"type": "value", "gridIndex": 0, "name": "Velocidade (km/h)", "nameLocation": "middle",
         "nameGap": 45, "position": "left", "min": 0, "scale": True,
         "axisLine": {"show": True, "lineStyle": {"color": COR_VEL}},
         "splitLine": {"show": True, "lineStyle": {"type": "dotted", "opacity": 0.4}}},
        {"type": "value", "gridIndex": 0, "name": rotulo_var(sufixo_dir), "nameLocation": "middle",
         "nameGap": 55, "position": "right", "scale": True,
         "axisLine": {"show": True, "lineStyle": {"color": COR_VAR}},
         "axisLabel": {"formatter": FMT_AXIS_BR}, "splitLine": {"show": False}},
    ]
    # a faixa usa yAxisIndex 1 -> reordena: índice 1 precisa ser a faixa quando existe
    if faixa:
        yaxes = [yaxes[0], yaxes_extra[0], yaxes[1]]
        for s in series:
            if s["name"] == rotulo_var(sufixo_dir):
                s["yAxisIndex"] = 2
            if s["name"] in ("Velocidade",):
                s["yAxisIndex"] = 0

    opcoes = {
        "title": {"text": "Velocidade × variável × modos operacionais", "subtext": subtitulo,
                  "left": "center", "top": "1%", "textStyle": {"fontSize": 16, "fontWeight": "bold"},
                  "subtextStyle": {"fontSize": 11, "color": "#777"}},
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "cross"}, "formatter": tooltip},
        "axisPointer": {"link": [{"xAxisIndex": "all"}]},
        "legend": {"type": "scroll", "top": "12%", "left": "center", "data": legenda},
        "grid": grids, "xAxis": xaxes, "yAxis": yaxes,
        "dataZoom": [{"type": "inside", "xAxisIndex": zoom_idx},
                     {"type": "slider", "xAxisIndex": zoom_idx, "bottom": "1%"}],
        "series": series,
    }
    if colorida:
        opcoes["visualMap"] = {
            "type": "piecewise", "show": False, "seriesIndex": idx_vel, "dimension": 2,
            "pieces": [{"value": 0, "color": COR_VEL}] +
                      [{"value": k, "color": m["cor"]} for k, m in enumerate(MODOS, start=1)],
        }
    grafico(opcoes, altura, chave)


def grafico_sobreposto(dados_a, dados_b, nome_a, nome_b, prefixo, sufixo, eixo_x, chave):
    """Dois ensaios no mesmo gráfico (velocidade à esquerda, variável à direita)."""
    por_tempo = eixo_x.startswith("Tempo")
    series, legenda = [], []
    estilos = [("A", dados_a, "solid", 1.0), ("B", dados_b, "dashed", 0.75)]
    for rot, d, traco, _ in estilos:
        v = get_serie(d, f"{prefixo}Speed_com")
        y = get_serie(d, f"{prefixo}{sufixo}")
        if v is None or y is None:
            st.warning(f"Ensaio {rot}: variáveis ausentes.")
            return
        n = min(len(v), len(y))
        v, y = v[:n], y[:n]
        x = np.arange(n) * DT_AMOSTRAGEM if por_tempo else _distancia_km(v)
        sl = slice(None, None, passo_decimacao(n))
        nv, ny = f"Velocidade — {rot}", f"{rotulo_var(sufixo)} — {rot}"
        legenda += [nv, ny]
        series.append({"name": nv, "type": "line", "yAxisIndex": 0, "showSymbol": False,
                       "data": to_pts(x[sl], v[sl]),
                       "lineStyle": {"color": COR_VEL, "width": 2, "type": traco},
                       "itemStyle": {"color": COR_VEL}})
        series.append({"name": ny, "type": "line", "yAxisIndex": 1, "showSymbol": False,
                       "data": to_pts(x[sl], y[sl]),
                       "lineStyle": {"color": COR_VAR, "width": 2, "type": traco},
                       "itemStyle": {"color": COR_VAR}})
    rot_x = "Tempo (s)" if por_tempo else "Distância (km)"
    opcoes = {
        "title": {"text": "Ensaios sobrepostos", "subtext": f"A: {nome_a} | B: {nome_b} (B tracejado)",
                  "left": "center", "subtextStyle": {"fontSize": 11, "color": "#777"}},
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "cross"}},
        "legend": {"type": "scroll", "top": "12%", "data": legenda},
        "grid": {"left": "7%", "right": "7%", "top": "24%", "bottom": "18%", "containLabel": True},
        "xAxis": {"type": "value", "name": rot_x, "nameLocation": "middle", "nameGap": 30, "min": 0,
                  "splitLine": {"lineStyle": {"type": "dashed", "opacity": 0.35}}},
        "yAxis": [{"type": "value", "name": "Velocidade (km/h)", "min": 0, "scale": True,
                   "axisLine": {"show": True, "lineStyle": {"color": COR_VEL}}},
                  {"type": "value", "name": rotulo_var(sufixo), "scale": True, "position": "right",
                   "axisLine": {"show": True, "lineStyle": {"color": COR_VAR}},
                   "splitLine": {"show": False}}],
        "dataZoom": [{"type": "inside", "xAxisIndex": 0}, {"type": "slider", "xAxisIndex": 0, "bottom": "2%"}],
        "series": series,
    }
    grafico(opcoes, "520px", chave)


def grafico_ah_acumulado(dados, prefixo, subtitulo, chave):
    """Ah acumulado ao longo do tempo, por modo, e saldo líquido."""
    corrente = get_serie(dados, f"{prefixo}CorrenteFiltro")
    if corrente is None:
        st.warning("Variável de corrente da bateria (CorrenteFiltro) não encontrada.")
        return
    n = len(corrente)
    modos = vetor_modos(dados, prefixo, n)
    i0 = np.nan_to_num(corrente)
    t = np.arange(n) * DT_AMOSTRAGEM
    sl = slice(None, None, passo_decimacao(n))

    series, legenda = [], []
    for k, m in enumerate(MODOS, start=1):
        cum = np.cumsum(np.where(modos == k, i0, 0.0)) * DT_AMOSTRAGEM / 3600
        legenda.append(m["curto"])
        series.append({"name": m["curto"], "type": "line", "showSymbol": False,
                       "data": to_pts(t[sl], cum[sl]), "lineStyle": {"color": m["cor"], "width": 2},
                       "itemStyle": {"color": m["cor"]}, "areaStyle": {"color": m["cor"], "opacity": 0.12}})
    saldo = np.cumsum(i0) * DT_AMOSTRAGEM / 3600
    legenda.append("Saldo líquido")
    series.append({"name": "Saldo líquido", "type": "line", "showSymbol": False,
                   "data": to_pts(t[sl], saldo[sl]),
                   "lineStyle": {"color": "#111", "width": 2.5, "type": "dashed"}, "itemStyle": {"color": "#111"}})
    opcoes = {
        "title": {"text": "Ah acumulado por modo operacional", "subtext": subtitulo, "left": "center",
                  "subtextStyle": {"fontSize": 11, "color": "#777"}},
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "cross"}},
        "legend": {"top": "12%", "data": legenda},
        "grid": {"left": "7%", "right": "5%", "top": "24%", "bottom": "18%", "containLabel": True},
        "xAxis": {"type": "value", "name": "Tempo (s)", "nameLocation": "middle", "nameGap": 30, "min": 0},
        "yAxis": {"type": "value", "name": "Ah acumulado", "scale": True,
                  "splitLine": {"lineStyle": {"type": "dashed", "opacity": 0.4}}},
        "dataZoom": [{"type": "inside"}, {"type": "slider", "bottom": "2%"}],
        "series": series,
    }
    grafico(opcoes, "480px", chave)
    st.caption("Sinal do Ah conforme a convenção da corrente da bateria nos arquivos MAT "
               "(nos balanços, Boost e cargas auxiliares aparecem negativos; Alternador e Frenagem positivos).")


# =======================================================================
# 6. KPIs
# =======================================================================
def kpis_ciclo(dados, prefixo, nome_ciclo):
    distancia = get_escalar(dados, f"{prefixo}distancia_total_km")
    combustivel = get_escalar(dados, f"{prefixo}litros_totais")
    autonomia = get_escalar(dados, f"{prefixo}autonomia_final")
    capacidade = get_escalar(dados, f"{prefixo}Capacidade_Ah")
    soc = soc_percentual(get_serie(dados, f"{prefixo}SOC_calc"))
    soc_min = soc_max = None
    if soc is not None:
        s = soc[np.isfinite(soc)]
        if s.size:
            soc_min, soc_max = float(s.min()), float(s.max())

    st.subheader(f"Indicadores do ciclo — {nome_ciclo}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Distância percorrida", f"{fmt_br(distancia)} km" if distancia is not None else "N/D")
    c2.metric("Combustível consumido", f"{fmt_br(combustivel)} L" if combustivel is not None else "N/D")
    c3.metric("Autonomia do ciclo", f"{fmt_br(autonomia)} km/L" if autonomia is not None else "N/D")
    c4, c5, c6 = st.columns(3)
    c4.metric("Capacidade da bateria", f"{fmt_br(capacidade)} Ah" if capacidade is not None else "N/D")
    c5.metric("SOC mínimo medido", f"{fmt_br(soc_min)} %" if soc_min is not None else "N/D")
    c6.metric("SOC máximo medido", f"{fmt_br(soc_max)} %" if soc_max is not None else "N/D")


def calcular_kpis_avancados(dados, prefixo, limiar_dI=5.0):
    """KPIs derivados: Ah/km por modo, balanço, throughput, C-rate, térmica, resistência, combustível."""
    k = {}
    vel = get_serie(dados, f"{prefixo}Speed_com")
    corr = get_serie(dados, f"{prefixo}CorrenteFiltro")
    cap = get_escalar(dados, f"{prefixo}Capacidade_Ah")

    dist = get_escalar(dados, f"{prefixo}distancia_total_km")
    if dist is None and vel is not None:
        dist = float(np.nansum(vel) / 3.6 * DT_AMOSTRAGEM / 1000)
    k["dist"] = dist

    caps = {m["curto"]: get_escalar(dados, f"{prefixo}{m['cap']}") for m in MODOS}
    k["caps"] = caps
    k["ah_km"] = {n: (c / dist if (c is not None and dist) else None) for n, c in caps.items()}
    validos = [c for c in caps.values() if c is not None]
    k["saldo_modos"] = float(sum(validos)) if validos else None

    soc = soc_percentual(get_serie(dados, f"{prefixo}SOC_calc"))
    k["d_soc_ah"] = None
    if soc is not None and cap:
        s = soc[np.isfinite(soc)]
        if s.size > 1:
            k["d_soc_ah"] = float((s[-1] - s[0]) / 100 * cap)

    k["throughput"] = float(np.nansum(np.abs(corr)) * DT_AMOSTRAGEM / 3600) if corr is not None else None
    k["crate_carga"] = k["crate_desc"] = None
    if corr is not None and cap:
        c = corr[np.isfinite(corr)] / cap
        if c.size:
            k["crate_carga"], k["crate_desc"] = float(c.max()), float(c.min())

    temp = get_serie(dados, f"{prefixo}TempBattery_com")
    k["t_max"] = k["taxa_aq"] = None
    if temp is not None:
        tf = temp[np.isfinite(temp)]
        if tf.size > 1:
            k["t_max"] = float(tf.max())
            minutos = len(temp) * DT_AMOSTRAGEM / 60
            k["taxa_aq"] = float((tf[-1] - tf[0]) / minutos) if minutos > 0 else None

    k["r_int"] = None
    volt = get_serie(dados, f"{prefixo}TensaoChumbo_com")
    if corr is not None and volt is not None:
        n = min(len(corr), len(volt))
        dI, dV = np.diff(corr[:n]), np.diff(volt[:n])
        sel = np.isfinite(dI) & np.isfinite(dV) & (np.abs(dI) >= limiar_dI)
        if sel.sum() >= 10:
            k["r_int"] = float(abs(np.median(dV[sel] / dI[sel])) * 1000)   # mΩ

    fluxo = get_serie(dados, f"{prefixo}FluxoVolume_com")
    litros = get_escalar(dados, f"{prefixo}litros_totais")
    k["fluxo_pct"], k["fluxo_litros"] = {}, {}
    if fluxo is not None:
        modos = vetor_modos(dados, prefixo, len(fluxo))
        f0 = np.nan_to_num(fluxo)
        total = f0.sum()
        if total > 0:
            for i, m in enumerate(MODOS, start=1):
                frac = f0[modos == i].sum() / total
                k["fluxo_pct"][m["curto"]] = float(frac * 100)
                k["fluxo_litros"][m["curto"]] = float(frac * litros) if litros is not None else None
    return k


# =======================================================================
# 7. EVENTOS
# =======================================================================
def tabela_eventos(dados, prefixo) -> pd.DataFrame:
    """Uma linha por ocorrência contínua de cada modo (classificação exclusiva)."""
    vel = get_serie(dados, f"{prefixo}Speed_com")
    corr = get_serie(dados, f"{prefixo}CorrenteFiltro")
    thr = get_serie(dados, f"{prefixo}Throttle_com")
    soc = soc_percentual(get_serie(dados, f"{prefixo}SOC_calc"))
    volt = get_serie(dados, f"{prefixo}TensaoChumbo_com")
    ref = vel if vel is not None else corr
    if ref is None:
        return pd.DataFrame()
    modos = vetor_modos(dados, prefixo, len(ref))

    def agg(arr, i, f, fn):
        if arr is None or len(arr) < f or f <= i:
            return np.nan
        seg = arr[i:f]
        seg = seg[np.isfinite(seg)]
        return float(fn(seg)) if seg.size else np.nan

    linhas = []
    for k, m in enumerate(MODOS, start=1):
        ini, fim = segmentos(modos == k)
        for i, f in zip(ini, fim):
            ah = (np.nansum(corr[i:f]) * DT_AMOSTRAGEM / 3600) if corr is not None else np.nan
            v_ini = vel[i] if vel is not None else np.nan
            v_fim = vel[min(f, len(vel)) - 1] if vel is not None else np.nan
            dist = (np.nansum(vel[i:f]) / 3.6 * DT_AMOSTRAGEM / 1000) if vel is not None else np.nan
            d_soc = (soc[min(f, len(soc)) - 1] - soc[i]) if soc is not None and len(soc) > i else np.nan
            linhas.append({
                "Modo": m["curto"],
                "Início (s)": round(i * DT_AMOSTRAGEM, 2),
                "Duração (s)": round((f - i) * DT_AMOSTRAGEM, 2),
                "Ah": float(ah),
                "Corrente média (A)": agg(corr, i, f, np.mean),
                "Pico |I| (A)": agg(corr, i, f, lambda s: np.max(np.abs(s))),
                "Vel. inicial (km/h)": float(v_ini),
                "Vel. final (km/h)": float(v_fim),
                "Vel. média (km/h)": agg(vel, i, f, np.mean),
                "Throttle médio (%)": agg(thr, i, f, np.mean),
                "Tensão média (V)": agg(volt, i, f, np.mean),
                "Distância (km)": float(dist),
                "ΔSOC (%)": float(d_soc),
            })
    df = pd.DataFrame(linhas)
    return df.sort_values("Início (s)").reset_index(drop=True) if not df.empty else df


def matriz_transicoes(modos: np.ndarray) -> np.ndarray:
    seq = modos[modos > 0]
    if seq.size < 2:
        return np.zeros((len(MODOS), len(MODOS)), dtype=int)
    seq = seq[np.concatenate([[True], seq[1:] != seq[:-1]])]
    mat = np.zeros((len(MODOS), len(MODOS)), dtype=int)
    for a, b in zip(seq[:-1], seq[1:]):
        mat[a - 1, b - 1] += 1
    return mat


def eficiencia_regeneracao(df: pd.DataFrame, massa: float, tensao_padrao: float = 13.0):
    """Energia elétrica recuperada / energia cinética perdida em cada frenagem."""
    fre = df[df["Modo"] == "Frenagem"].copy()
    if fre.empty:
        return fre
    vi, vf = fre["Vel. inicial (km/h)"] / 3.6, fre["Vel. final (km/h)"] / 3.6
    fre["E cinética (Wh)"] = (0.5 * massa * (vi ** 2 - vf ** 2)).clip(lower=0) / 3600
    tensao = fre["Tensão média (V)"].fillna(tensao_padrao)
    fre["E elétrica (Wh)"] = fre["Ah"].abs() * tensao
    fre["Eficiência (%)"] = np.where(fre["E cinética (Wh)"] > 0.05,
                                     fre["E elétrica (Wh)"] / fre["E cinética (Wh)"] * 100, np.nan)
    return fre


def pagina_eventos(arquivo_1, arquivo_2):
    st.title("Eventos & KPIs avançados")
    ciclos = ciclos_carregados(arquivo_1, arquivo_2)
    if not ciclos:
        st.info("Envie pelo menos um arquivo .mat na barra lateral.")
        return
    nome = st.selectbox("Ciclo:", [c["nome"] for c in ciclos], key="ev_ciclo")
    c = next(x for x in ciclos if x["nome"] == nome)
    dados, pref = c["dados"], c["prefixo"]

    # ---------------- KPIs avançados ----------------
    st.subheader("KPIs avançados")
    limiar_dI = st.number_input("Limiar de |ΔI| para estimar a resistência interna (A)",
                                1.0, 100.0, 5.0, 1.0, key="ev_dI")
    k = calcular_kpis_avancados(dados, pref, limiar_dI)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Throughput de Ah", f"{fmt_br(k['throughput'])} Ah")
    m2.metric("Balanço líquido (soma dos modos)", f"{fmt_br(k['saldo_modos'])} Ah")
    m3.metric("ΔSOC × capacidade", f"{fmt_br(k['d_soc_ah'])} Ah")
    dif = (k["saldo_modos"] - k["d_soc_ah"]) if (k["saldo_modos"] is not None and k["d_soc_ah"] is not None) else None
    m4.metric("Diferença (consistência)", f"{fmt_br(dif)} Ah")
    m5, m6, m7, m8 = st.columns(4)
    m5.metric("C-rate máx. (carga)", fmt_br(k["crate_carga"]))
    m6.metric("C-rate máx. (descarga)", fmt_br(k["crate_desc"]))
    m7.metric("Temp. máx. / aquecimento",
              f"{fmt_br(k['t_max'], 1)} °C" if k["t_max"] is not None else "N/D",
              f"{fmt_br(k['taxa_aq'])} °C/min" if k["taxa_aq"] is not None else None)
    m8.metric("Resistência interna (est.)", f"{fmt_br(k['r_int'])} mΩ" if k["r_int"] is not None else "N/D")
    st.caption("A resistência é uma estimativa grosseira (mediana de ΔV/ΔI nos degraus de corrente), "
               "sujeita a ruído e dinâmica de tensão. A diferença entre o balanço dos modos e ΔSOC×capacidade "
               "serve como verificação de consistência dos dados.")

    g1, g2 = st.columns(2)
    with g1:
        nomes = [m["curto"] for m in MODOS]
        barras_ah = [None if k["ah_km"][n] is None else round(k["ah_km"][n], 3) for n in nomes]
        if any(v is not None for v in barras_ah):
            grafico({
                "title": {"text": "Ah por km, por modo", "left": "center"},
                "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
                "grid": {"left": "10%", "right": "5%", "bottom": "12%", "top": "18%", "containLabel": True},
                "xAxis": {"type": "category", "data": nomes},
                "yAxis": {"type": "value", "name": "Ah/km", "splitLine": {"show": False}},
                "series": [{"type": "bar", "barMaxWidth": 40, "data": [
                    {"value": v, "itemStyle": {"color": m["cor"]}} for v, m in zip(barras_ah, MODOS)],
                    "label": {"show": True, "position": "top", "formatter": FMT_DEC}}],
            }, "380px", f"ev_ahkm_{pref}")
        else:
            st.info("Ah/km indisponível (faltam capacidades por modo ou distância).")
    with g2:
        if k["fluxo_pct"]:
            nomes_f = list(k["fluxo_pct"].keys())
            grafico({
                "title": {"text": "Combustível por modo (% do fluxo)", "left": "center"},
                "tooltip": {"trigger": "item", "formatter": "{b}: {c}%"},
                "grid": {"left": "10%", "right": "5%", "bottom": "12%", "top": "18%", "containLabel": True},
                "xAxis": {"type": "category", "data": nomes_f},
                "yAxis": {"type": "value", "name": "%", "splitLine": {"show": False}},
                "series": [{"type": "bar", "barMaxWidth": 40, "data": [
                    {"value": round(k["fluxo_pct"][n], 2),
                     "itemStyle": {"color": next(m["cor"] for m in MODOS if m["curto"] == n)}} for n in nomes_f],
                    "label": {"show": True, "position": "top", "formatter": FMT_DEC}}],
            }, "380px", f"ev_fluxo_{pref}")
            if any(v is not None for v in k["fluxo_litros"].values()):
                st.caption("Litros estimados por modo: " + " | ".join(
                    f"{n}: {fmt_br(v)} L" for n, v in k["fluxo_litros"].items() if v is not None))
        else:
            st.info("FluxoVolume_com não encontrado para estimar o combustível por modo.")

    # ---------------- Eventos ----------------
    st.divider()
    st.subheader("Eventos por modo operacional")
    df = tabela_eventos(dados, pref)
    if df.empty:
        st.warning("Não foi possível segmentar eventos (faltam condições ou velocidade).")
        return

    resumo = (df.groupby("Modo").agg(Eventos=("Modo", "size"),
                                      **{"Duração média (s)": ("Duração (s)", "mean"),
                                         "Duração mediana (s)": ("Duração (s)", "median"),
                                         "Duração máx. (s)": ("Duração (s)", "max"),
                                         "Ah total": ("Ah", "sum")})
              .reindex([m["curto"] for m in MODOS]).dropna(how="all").round(2).reset_index())
    st.dataframe(resumo, use_container_width=True, hide_index=True)

    filtro_modos = st.multiselect("Filtrar eventos por modo:", [m["curto"] for m in MODOS],
                                  default=[m["curto"] for m in MODOS], key=f"ev_modos_{pref}")
    df_f = df[df["Modo"].isin(filtro_modos)]
    st.dataframe(df_f.round(2), use_container_width=True, hide_index=True)
    cd1, cd2, _ = st.columns([1, 1, 3])
    cd1.download_button("⬇️ Eventos (CSV)", csv_bytes(df_f.round(4)), f"eventos_{pref}.csv", "text/csv")
    xl = excel_bytes({"Eventos": df.round(4), "Resumo": resumo})
    if xl:
        cd2.download_button("⬇️ Relatório (Excel)", xl, f"relatorio_{pref}.xlsx",
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # Histograma de duração por modo
    st.markdown("#### Distribuição da duração dos eventos")
    dmax = max(float(df["Duração (s)"].max()), 2 * DT_AMOSTRAGEM)
    bordas = np.linspace(0, dmax, 13)
    centros = [fmt_br((bordas[i] + bordas[i + 1]) / 2, 1) for i in range(12)]
    series = []
    for m in MODOS:
        d = df.loc[df["Modo"] == m["curto"], "Duração (s)"].to_numpy()
        if d.size:
            h, _ = np.histogram(d, bins=bordas)
            series.append({"name": m["curto"], "type": "bar", "data": h.tolist(),
                           "itemStyle": {"color": m["cor"]}, "barMaxWidth": 22})
    grafico({
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
        "legend": {"top": "2%", "data": [s["name"] for s in series]},
        "grid": {"left": "7%", "right": "4%", "bottom": "18%", "top": "14%", "containLabel": True},
        "xAxis": {"type": "category", "data": centros, "name": "Duração (s)", "nameLocation": "middle",
                  "nameGap": 32},
        "yAxis": {"type": "value", "name": "Nº de eventos", "splitLine": {"show": False}},
        "series": series,
    }, "380px", f"ev_hist_{pref}")

    # Top eventos por Ah
    st.markdown("#### Eventos mais energéticos (|Ah|)")
    top = df.assign(**{"|Ah|": df["Ah"].abs()}).nlargest(10, "|Ah|")
    st.dataframe(top[["Modo", "Início (s)", "Duração (s)", "Ah", "Pico |I| (A)", "Vel. média (km/h)"]].round(2),
                 use_container_width=True, hide_index=True)

    # Transições
    st.markdown("#### Transições entre modos")
    mat = matriz_transicoes(vetor_modos(dados, pref, int(df["Início (s)"].max() / DT_AMOSTRAGEM + 2)
                                        if False else len(get_serie(dados, f"{pref}Speed_com")
                                                           if get_serie(dados, f"{pref}Speed_com") is not None
                                                           else get_serie(dados, f"{pref}CorrenteFiltro"))))
    nomes_m = [m["curto"] for m in MODOS]
    dados_hm = [[j, i, int(mat[i, j])] for i in range(len(MODOS)) for j in range(len(MODOS))]
    grafico({
        "tooltip": {"formatter": js("""function(p){ return 'De <b>' + __N__[p.value[1]] + '</b> para <b>' +
            __N__[p.value[0]] + '</b>: ' + p.value[2] + ' vezes'; }""".replace("__N__", json.dumps(nomes_m)))},
        "grid": {"left": "14%", "right": "6%", "bottom": "22%", "top": "6%", "containLabel": True},
        "xAxis": {"type": "category", "data": nomes_m, "name": "Para", "nameLocation": "middle", "nameGap": 30},
        "yAxis": {"type": "category", "data": nomes_m, "name": "De", "nameLocation": "middle", "nameGap": 60},
        "visualMap": {"min": 0, "max": max(int(mat.max()), 1), "calculable": True, "orient": "horizontal",
                      "left": "center", "bottom": "0%", "inRange": {"color": ["#f7f1fb", "#702082"]}},
        "series": [{"type": "heatmap", "data": dados_hm, "label": {"show": True}}],
    }, "380px", f"ev_trans_{pref}")

    # Regeneração
    st.markdown("#### Eficiência de regeneração")
    massa = st.number_input("Massa do veículo (kg)", 500.0, 5000.0, 1500.0, 50.0, key=f"ev_massa_{pref}")
    fre = eficiencia_regeneracao(df, massa)
    if fre.empty:
        st.info("Nenhum evento de frenagem regenerativa encontrado.")
    else:
        e_ele, e_cin = fre["E elétrica (Wh)"].sum(), fre["E cinética (Wh)"].sum()
        r1, r2, r3 = st.columns(3)
        r1.metric("Energia elétrica recuperada", f"{fmt_br(e_ele)} Wh")
        r2.metric("Energia cinética dissipada", f"{fmt_br(e_cin)} Wh")
        r3.metric("Eficiência global", f"{fmt_br(e_ele / e_cin * 100)} %" if e_cin > 0 else "N/D")
        st.caption("Estimativa: energia cinética = ½·m·(v₁² − v₂²) por evento; energia elétrica = |Ah| × tensão média. "
                   "Perdas aerodinâmicas e de rolamento não são descontadas, então é um limite inferior da eficiência.")
        st.dataframe(fre[["Início (s)", "Duração (s)", "Vel. inicial (km/h)", "Vel. final (km/h)", "Ah",
                          "E cinética (Wh)", "E elétrica (Wh)", "Eficiência (%)"]].round(2),
                     use_container_width=True, hide_index=True)

    # Ineficiências
    st.markdown("#### Possíveis ineficiências da estratégia")
    i1, i2, i3 = st.columns(3)
    lim_v = i1.number_input("Boost abaixo de (km/h)", 0.0, 100.0, 20.0, 1.0, key=f"ev_limv_{pref}")
    lim_t = i2.number_input("Alternador com pedal acima de (%)", 0.0, 100.0, 60.0, 5.0, key=f"ev_limt_{pref}")
    lim_d = i3.number_input("Pulsos curtos abaixo de (s)", 0.1, 10.0, 1.0, 0.1, key=f"ev_limd_{pref}")
    flag_boost = df[(df["Modo"] == "Boost") & (df["Vel. média (km/h)"] < lim_v)]
    flag_alt = df[(df["Modo"] == "Alternador") & (df["Throttle médio (%)"] > lim_t)]
    flag_curto = df[(df["Duração (s)"] < lim_d) & (df["Modo"].isin(["Boost", "Alternador"]))]
    f1, f2, f3 = st.columns(3)
    f1.metric("Boost em baixa velocidade", len(flag_boost))
    f2.metric("Alternador com pedal alto", len(flag_alt))
    f3.metric("Pulsos curtos (Boost/Alt.)", len(flag_curto))
    with st.expander("Ver eventos sinalizados"):
        for titulo, d in (("Boost em baixa velocidade", flag_boost), ("Alternador com pedal alto", flag_alt),
                          ("Pulsos curtos", flag_curto)):
            st.markdown(f"**{titulo}**")
            st.dataframe(d.round(2), use_container_width=True, hide_index=True)

    # C-rate
    corr = get_serie(dados, f"{pref}CorrenteFiltro")
    cap = get_escalar(dados, f"{pref}Capacidade_Ah")
    if corr is not None and cap:
        st.markdown("#### Distribuição do C-rate")
        cr = corr[np.isfinite(corr)] / cap
        h, b = np.histogram(cr, bins=30)
        grafico({
            "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
            "grid": {"left": "7%", "right": "4%", "bottom": "18%", "top": "8%", "containLabel": True},
            "xAxis": {"type": "category", "data": [fmt_br((b[i] + b[i + 1]) / 2, 2) for i in range(30)],
                      "name": "C-rate", "nameLocation": "middle", "nameGap": 32,
                      "axisLabel": {"rotate": 40, "interval": 2, "fontSize": 9}},
            "yAxis": {"type": "value", "name": "Amostras", "splitLine": {"show": False}},
            "series": [{"type": "bar", "data": h.tolist(), "itemStyle": {"color": COR_BOOST}, "barMaxWidth": 20}],
        }, "340px", f"ev_crate_{pref}")


# =======================================================================
# 8. TELEMETRIA
# =======================================================================
def painel_telemetria(arquivo, prefixo, nome_ciclo, chave):
    dados = carregar_arquivo_mat(arquivo)
    if not dados:
        return
    kpis_ciclo(dados, prefixo, nome_ciclo)
    st.divider()
    sufixos = listar_series(dados, prefixo)
    t_livre, t_modos, t_ah = st.tabs(["Dois eixos livres", "Velocidade × modos", "Ah acumulado por modo"])

    with t_livre:
        if len(sufixos) < 2:
            st.warning("O arquivo precisa conter ao menos 2 séries temporais.")
        else:
            c1, c2 = st.columns(2)
            esq = c1.selectbox("Variável esquerda (área):", sufixos, format_func=rotulo_var, key=f"{chave}_esq")
            dire = c2.selectbox("Variável direita (linha):", sufixos, index=1, format_func=rotulo_var,
                                key=f"{chave}_dir")
            plotar_grafico_duplo_eixo(dados, prefixo, esq, dire,
                                      f"{arquivo.name} — {rotulo_var(esq, False)} vs {rotulo_var(dire, False)}",
                                      f"{chave}_duplo")

    with t_modos:
        opcoes_dir = [s for s in sufixos if s != "Speed_com"]
        if not opcoes_dir:
            st.warning("Sem variáveis adicionais para o eixo direito.")
        else:
            c1, c2, c3 = st.columns([2, 2, 2])
            idx = opcoes_dir.index("SOC_calc") if "SOC_calc" in opcoes_dir else 0
            sufixo = c1.selectbox("Variável do eixo direito:", opcoes_dir, index=idx,
                                  format_func=rotulo_var, key=f"{chave}_mdir")
            estilo = c2.selectbox("Visualização dos modos:", ESTILOS, key=f"{chave}_estilo")
            eixo = c3.radio("Eixo X:", ["Tempo (s)", "Distância (km)"], horizontal=True, key=f"{chave}_eixo")
            sel = st.multiselect("Modos exibidos:", [m["nome"] for m in MODOS],
                                 default=[m["nome"] for m in MODOS], key=f"{chave}_msel")
            modos_idx = [i for i, m in enumerate(MODOS, start=1) if m["nome"] in sel]
            vel = get_serie(dados, f"{prefixo}Speed_com")
            tmax = (len(vel) if vel is not None else 0) * DT_AMOSTRAGEM
            janela = None
            if tmax > 10:
                janela = st.slider("Janela de tempo (s)", 0.0, float(tmax), (0.0, float(tmax)),
                                   step=1.0, key=f"{chave}_janela")
            fases = None
            if prefixo == "f":
                if st.checkbox("Mostrar fases do FTP", key=f"{chave}_fases"):
                    p1, p2 = st.columns(2)
                    t1 = p1.number_input("Fim do transiente a frio (s)", 0.0, 5000.0, 505.0, 1.0, key=f"{chave}_f1")
                    t2 = p2.number_input("Fim da fase estabilizada (s)", 0.0, 5000.0, 1372.0, 1.0, key=f"{chave}_f2")
                    fases = [("Fim transiente a frio", t1), ("Fim fase estabilizada", t2)]
            grafico_temporal(dados, prefixo, sufixo, arquivo.name, f"{chave}_temporal", estilo,
                             modos_idx, janela, eixo, fases)

    with t_ah:
        grafico_ah_acumulado(dados, prefixo, arquivo.name, f"{chave}_ah")


# =======================================================================
# 9. ESTATÍSTICA
# =======================================================================
def contagem_condicoes(dados, prefixo):
    """Itens de pizza: nº de amostras ativas em cada condição."""
    itens = []
    for m in MODOS:
        c = get_serie(dados, f"{prefixo}condicao_{m['cod']}")
        if c is not None:
            itens.append({"value": int(np.sum(c > 0)), "name": m["curto"], "itemStyle": {"color": m["cor"]}})
    if not itens:   # fallback: detecção automática
        for chave, vetor in dados.items():
            kl = chave.lower()
            if "cond" in kl or any(t in kl for t in ("boo", "neu", "alt")):
                itens.append({"value": int(np.sum(np.asarray(vetor) > 0)), "name": chave})
    return [i for i in itens if i["value"] > 0]


def plotar_pizza_condicoes(itens, titulo, chave):
    grafico({
        "title": {"text": titulo, "subtext": "Tempo em cada condição", "left": "center"},
        "tooltip": {"trigger": "item", "formatter": "{b}<br/><b>{c} amostras</b> ({d}%)"},
        "legend": {"orient": "vertical", "left": "left"},
        "series": [{"name": "Condição", "type": "pie", "radius": "55%", "data": itens,
                    "label": {"show": True, "formatter": "{b}\n{d}%", "fontSize": 12, "fontWeight": "bold"},
                    "labelLine": {"show": True, "length": 15, "length2": 10},
                    "emphasis": {"itemStyle": {"shadowBlur": 10, "shadowColor": "rgba(0,0,0,0.5)"}}}],
    }, "450px", chave)


def renderizar_analise_estatistica(arquivo_1, arquivo_2):
    ciclos = ciclos_carregados(arquivo_1, arquivo_2)
    if not ciclos:
        st.info("Envie pelo menos um arquivo .mat na barra lateral para iniciar a análise estatística.")
        return
    st.title("Análise Estatística das Condições Operacionais")

    nome = st.selectbox("Ciclo de condução:", [c["nome"] for c in ciclos], key="estat_ciclo")
    ciclo = next(c for c in ciclos if c["nome"] == nome)
    dados, prefixo = ciclo["dados"], ciclo["prefixo"]

    condicoes = {"Todas as amostras": None}
    for m in MODOS:
        if f"{prefixo}condicao_{m['cod']}" in dados:
            condicoes[m["curto"]] = m["cod"]

    col1, col2 = st.columns(2)
    cond_nome = col1.selectbox("Condição operacional:", list(condicoes.keys()), key=f"estat_cond_{prefixo}")
    cod = condicoes[cond_nome]
    sufixos = listar_series(dados, prefixo)
    if not sufixos:
        st.warning("Não foram encontradas séries temporais numéricas para análise neste arquivo.")
        return
    suf = col2.selectbox("Variável analisada:", sufixos, format_func=rotulo_var, key=f"estat_var_{prefixo}")
    nome_var = rotulo_var(suf)
    (valores,) = extrair(dados, prefixo, [f"{prefixo}{suf}"], cod)

    st.divider()
    st.markdown(f"**Ciclo:** {ciclo['nome']}  \n**Condição:** {cond_nome}  \n**Variável:** {nome_var}")
    if len(valores) < 2:
        st.warning("Não existem amostras suficientes para realizar a análise nesta condição.")
        return

    media, mediana = float(np.mean(valores)), float(np.median(valores))
    desvio = float(np.std(valores, ddof=1))
    minimo, maximo = float(valores.min()), float(valores.max())
    perc = np.percentile(valores, [10, 25, 50, 75, 90])
    cv = desvio / abs(media) * 100 if abs(media) > 1e-12 else None

    st.subheader("Indicadores estatísticos")
    cols = st.columns(4)
    indic = [("Amostras válidas", fmt_br(len(valores), 0)), ("Média", fmt_br(media)),
             ("Mediana", fmt_br(mediana)), ("Desvio-padrão", fmt_br(desvio)),
             ("Mínimo", fmt_br(minimo)), ("Máximo", fmt_br(maximo)),
             ("Coef. de variação", f"{fmt_br(cv)} %" if cv is not None else "N/D"),
             ("Amplitude", fmt_br(maximo - minimo))]
    for i, (r, v) in enumerate(indic):
        cols[i % 4].metric(r, v)
    st.markdown("**Distribuição por percentis**")
    st.dataframe(pd.DataFrame({"Percentil": ["P10", "P25", "P50", "P75", "P90"],
                               "Valor": [fmt_br(v) for v in perc]}),
                 use_container_width=True, hide_index=True)

    # Histograma + normal
    st.divider()
    st.subheader("Distribuição de probabilidade")
    nb = min(30, max(5, int(np.sqrt(len(valores)))))
    freq, limites = np.histogram(valores, bins=nb)
    centros = (limites[:-1] + limites[1:]) / 2
    largura = float(np.mean(np.diff(limites)))
    if desvio > 0:
        pdf = (1 / (desvio * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((centros - media) / desvio) ** 2)
        freq_normal = pdf * len(valores) * largura
    else:
        freq_normal = np.zeros_like(centros)
    grafico({
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
        "legend": {"top": "2%", "data": ["Frequência observada", "Normal de referência"]},
        "grid": {"left": "8%", "right": "5%", "bottom": "15%", "top": "18%", "containLabel": True},
        "xAxis": {"type": "category", "name": nome_var, "nameLocation": "middle", "nameGap": 35,
                  "data": [fmt_br(v) for v in centros], "axisLabel": {"rotate": 35, "interval": "auto"}},
        "yAxis": {"type": "value", "name": "Frequência", "splitLine": {"show": False}},
        "series": [
            {"name": "Frequência observada", "type": "bar", "data": freq.tolist(), "barMaxWidth": 35,
             "itemStyle": {"color": COR_BOOST, "opacity": 0.7}},
            {"name": "Normal de referência", "type": "line", "data": freq_normal.tolist(), "smooth": True,
             "symbol": "none", "lineStyle": {"width": 3, "color": COR_REGEN}},
        ],
    }, "430px", f"estat_dist_{prefixo}")
    st.caption("A curva normal é uma referência calculada com a média e o desvio-padrão da amostra. "
               "Ela não implica que os dados sigam necessariamente uma distribuição normal.")

    # Boxplot por modo
    st.divider()
    st.subheader("Comparação entre modos operacionais")
    caixas, nomes_box, cores_box = [], [], []
    for m in MODOS:
        (v,) = extrair(dados, prefixo, [f"{prefixo}{suf}"], m["cod"])
        if len(v) >= 5:
            p = np.percentile(v, [10, 25, 50, 75, 90])
            caixas.append([round(float(x), 3) for x in p])
            nomes_box.append(m["curto"])
            cores_box.append(m["cor"])
    if caixas:
        grafico({
            "title": {"text": f"{nome_var} por modo", "subtext": "Caixa: P25–P75 | traço: mediana | hastes: P10–P90",
                      "left": "center", "subtextStyle": {"fontSize": 11, "color": "#777"}},
            "tooltip": {"trigger": "item"},
            "grid": {"left": "8%", "right": "5%", "bottom": "10%", "top": "22%", "containLabel": True},
            "xAxis": {"type": "category", "data": nomes_box},
            "yAxis": {"type": "value", "name": nome_var, "scale": True, "splitLine": {"show": False}},
            "series": [{"type": "boxplot", "data": [{"value": c, "itemStyle": {"borderColor": cor, "color": cor + "55"}}
                                                    for c, cor in zip(caixas, cores_box)]}],
        }, "400px", f"estat_box_{prefixo}")
    else:
        st.info("Amostras insuficientes por modo para o boxplot.")

    # Heatmaps de densidade
    st.divider()
    st.subheader("Mapas de densidade operacional")
    st.caption("A intensidade da cor representa o percentual de amostras da condição selecionada em cada região do mapa.")
    preditores = [("Velocidade", "Speed_com"), ("SOC", "SOC_calc"), ("RPM", "RPM_com"),
                  ("Carga do motor", "LoadCarga_com"), ("Pedal do acelerador", "Throttle_com")]
    validos = [(n, s) for n, s in preditores if f"{prefixo}{s}" in dados and s != suf]
    for i in range(0, len(validos), 2):
        cols = st.columns(2)
        for j in range(2):
            if i + j >= len(validos):
                continue
            n_x, s_x = validos[i + j]
            x, y = extrair(dados, prefixo, [f"{prefixo}{s_x}", f"{prefixo}{suf}"], cod)
            with cols[j]:
                st.markdown(f"**{n_x} × {nome_var}**")
                heatmap_2d(x, y, n_x, nome_var, f"hm_{prefixo}_{s_x}_{suf}_{cod}", "390px")

    st.divider()
    st.subheader("Análise térmica e elétrica da bateria")
    st.caption("Relação entre a temperatura da bateria e seus parâmetros elétricos, na condição selecionada.")
    mapas = [("Temperatura × Corrente da bateria", "TempBattery_com", "CorrenteFiltro"),
             ("Temperatura × Tensão da bateria", "TempBattery_com", "TensaoChumbo_com")]
    cols = st.columns(2)
    for col, (titulo, sx, sy) in zip(cols, mapas):
        with col:
            st.markdown(f"**{titulo}**")
            if f"{prefixo}{sx}" not in dados or f"{prefixo}{sy}" not in dados:
                st.warning(f"Variáveis não encontradas: {prefixo}{sx} ou {prefixo}{sy}.")
                continue
            x, y = extrair(dados, prefixo, [f"{prefixo}{sx}", f"{prefixo}{sy}"], cod)
            heatmap_2d(x, y, rotulo_var(sx), rotulo_var(sy), f"hmb_{prefixo}_{sy}_{cod}", "400px", titulo=titulo)


# =======================================================================
# 10. ANÁLISE ITEMM (emissões, proporções, balanço)
# =======================================================================
def plotar_emissoes_e_tempos(vars_ftp, vars_hgw, nome_ftp, nome_hgw):
    ciclos = [("ITEMM FTP", vars_ftp or {}, "f"), ("ITEMM HGW", vars_hgw or {}, "h")]
    nomes = [c[0] for c in ciclos]
    sub = f"FTP: {nome_ftp} | HIGHWAY: {nome_hgw}"

    def lista(sufixo):
        return [None if (v := get_escalar(d, f"{p}{sufixo}")) is None else round(v, 2) for _, d, p in ciclos]

    estilo_titulo = {"left": "center", "top": "1%", "textStyle": {"fontSize": 17, "fontWeight": "bold"},
                     "subtextStyle": {"fontSize": 11, "color": "#757575"}}

    media, ref, co2 = lista("emissao_media_g_km"), lista("emissao_ref"), lista("co2_total_g")
    if any(v is not None for v in media + ref + co2):
        grafico({
            "title": {"text": "Emissões de CO₂", "subtext": sub, **estilo_titulo},
            "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
            "legend": {"top": "16%", "data": ["Emissão média", "Referência", "CO₂ total"]},
            "grid": {"left": "10%", "right": "15%", "bottom": "12%", "top": "28%", "containLabel": True},
            "xAxis": {"type": "category", "data": nomes},
            "yAxis": [{"type": "value", "name": "Emissão (g/km)", "nameLocation": "middle", "nameGap": 45},
                      {"type": "value", "name": "CO₂ total (g)", "position": "right", "nameLocation": "middle",
                       "nameGap": 55, "splitLine": {"show": False}}],
            "series": [
                {"name": "Emissão média", "type": "bar", "yAxisIndex": 0, "data": media, "barMaxWidth": 45,
                 "itemStyle": {"color": COR_BOOST}, "label": {"show": True, "position": "top", "formatter": FMT_DEC}},
                {"name": "Referência", "type": "bar", "yAxisIndex": 0, "data": ref, "barMaxWidth": 45,
                 "itemStyle": {"color": COR_NEUTRO}, "label": {"show": True, "position": "top", "formatter": FMT_DEC}},
                {"name": "CO₂ total", "type": "line", "yAxisIndex": 1, "data": co2, "symbol": "circle",
                 "symbolSize": 10, "lineStyle": {"width": 3, "color": COR_REGEN}, "itemStyle": {"color": COR_REGEN},
                 "label": {"show": True, "position": "top", "formatter": FMT_DEC}},
            ],
        }, "440px", "grafico_emissoes_itemm")
    else:
        st.warning("Não foram encontrados dados de emissão nos arquivos MAT.")

    t_ss, t_cut = lista("s_start_stop"), lista("s_cut")
    if any(v is not None for v in t_ss + t_cut):
        grafico({
            "title": {"text": "Tempos de Start-Stop e Cut-off", "subtext": sub, **estilo_titulo},
            "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
            "legend": {"top": "16%", "data": ["Start-Stop", "Cut-off"]},
            "grid": {"left": "10%", "right": "5%", "bottom": "12%", "top": "28%", "containLabel": True},
            "xAxis": {"type": "category", "data": nomes},
            "yAxis": {"type": "value", "name": "Tempo (s)", "nameLocation": "middle", "nameGap": 45},
            "series": [
                {"name": "Start-Stop", "type": "bar", "data": t_ss, "barMaxWidth": 50,
                 "itemStyle": {"color": COR_ALTERNADOR}, "label": {"show": True, "position": "top", "formatter": FMT_TEMPO}},
                {"name": "Cut-off", "type": "bar", "data": t_cut, "barMaxWidth": 50,
                 "itemStyle": {"color": COR_REGEN}, "label": {"show": True, "position": "top", "formatter": FMT_TEMPO}},
            ],
        }, "420px", "grafico_tempos_start_stop_cutoff")
    else:
        st.warning("Não foram encontrados dados de tempo de Start-Stop ou Cut-off.")

    st.subheader("Eventos de Start-Stop")
    cols = st.columns(2)
    for col, (nome, d, p) in zip(cols, ciclos):
        q = get_escalar(d, f"{p}_ss_eventos_validos")
        col.metric(f"Eventos válidos — {nome}", fmt_br(q, 0) if q is not None else "N/D")


def plotar_barras_horizontais_condicoes(ciclos, dados_segmentos):
    series = []
    for nome, cor, chave in (("Boost", COR_BOOST, "Boost"), ("Neutro / Cargas", COR_NEUTRO, "Neutro"),
                             ("Alternador", COR_ALTERNADOR, "Alternador"), ("Frenagem Reg.", COR_REGEN, "Frenagem")):
        series.append({"name": nome, "type": "bar", "stack": "total",
                       "itemStyle": {"color": cor, "borderColor": "#333", "borderWidth": 0.5},
                       "label": {"show": True, "formatter": "{c}%", "color": "#fff", "fontWeight": "bold"},
                       "data": [round(float(v), 2) for v in dados_segmentos[chave]]})
    grafico({
        "title": {"text": "Distribuição Percentual por Condição (FTP-75 e Highway)", "left": "center"},
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
        "legend": {"top": "8%", "data": ["Boost", "Neutro / Cargas", "Alternador", "Frenagem Reg."]},
        "grid": {"left": "12%", "right": "8%", "bottom": "10%", "top": "18%", "containLabel": True},
        "xAxis": {"type": "value", "max": 100, "axisLabel": {"formatter": "{value}%"},
                  "splitLine": {"show": True, "lineStyle": {"type": "dashed"}}},
        "yAxis": {"type": "category", "data": ciclos},
        "series": series,
    }, "450px", "analise_barras_condicoes")


def plotar_balanco_carga(categorias, dados):
    series = []
    for nome, cor, chave in (("Cargas Auxiliares", COR_CARGAS_AUX, "Cargas Auxiliares"), ("Boost", COR_BOOST, "Boost"),
                             ("Frenagem Regenerativa", COR_REGEN, "Frenagem"), ("Alternador", COR_ALTERNADOR, "Alternador")):
        series.append({"name": nome, "type": "bar", "itemStyle": {"color": cor, "borderColor": "#000", "borderWidth": 0.5},
                       "label": {"show": True, "position": "outside", "fontWeight": "bold", "formatter": FMT_DEC},
                       "data": [round(float(v), 2) for v in dados[chave]]})
    grafico({
        "title": {"text": "Balanço de Carga por Modo (FTP-75 e Highway)", "left": "center"},
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
        "legend": {"top": "8%", "data": ["Cargas Auxiliares", "Boost", "Frenagem Regenerativa", "Alternador"]},
        "grid": {"left": "6%", "right": "6%", "bottom": "10%", "top": "18%", "containLabel": True},
        "xAxis": {"type": "category", "data": categorias, "axisTick": {"alignWithLabel": True},
                  "axisLine": {"onZero": True}},
        "yAxis": {"type": "value", "name": "Balanço de Carga (Ah)", "nameLocation": "middle", "nameGap": 35,
                  "splitLine": {"show": True, "lineStyle": {"type": "dashed"}}},
        "series": series,
    }, "480px", "analise_balanco")


def pagina_analise(arquivo_1, arquivo_2):
    st.title("Análise de Condições Operacionais — ITEMM")
    st.markdown("Análise dos resultados obtidos nos ensaios ITEMM, considerando os ciclos FTP e Highway.")
    if not (arquivo_1 and arquivo_2):
        st.info("Envie os dois arquivos MAT: o arquivo com os dados FTP e o arquivo com os dados Highway.")
        return
    vf, vh = carregar_arquivo_mat(arquivo_1), carregar_arquivo_mat(arquivo_2)

    st.divider()
    st.markdown("### 1. Análise de Emissão de CO2 e Start-Stop")
    plotar_emissoes_e_tempos(vf, vh, arquivo_1.name, arquivo_2.name)
    st.divider()

    obrig_f = [f"f{m['pct']}" for m in MODOS] + [f"f{m['cap']}" for m in MODOS]
    obrig_h = [f"h{m['pct']}" for m in MODOS] + [f"h{m['cap']}" for m in MODOS]
    falt_f = [n for n in obrig_f if n not in vf]
    falt_h = [n for n in obrig_h if n not in vh]
    if falt_f:
        st.error("O arquivo FTP não contém estas variáveis: " + ", ".join(falt_f))
    if falt_h:
        st.error("O arquivo Highway não contém estas variáveis: " + ", ".join(falt_h))
    if falt_f or falt_h:
        return

    def esc(d, n):
        v = get_escalar(d, n)
        if v is None:
            raise ValueError(f"A variável '{n}' está vazia ou ausente.")
        return v

    pct = {m["curto"]: [esc(vh, f"h{m['pct']}"), esc(vf, f"f{m['pct']}")] for m in MODOS}
    st.markdown("### 3. Proporção das Condições por Ciclo (%)")
    plotar_barras_horizontais_condicoes(["ITEMM HGW", "ITEMM FTP"], pct)
    st.markdown("---")

    cap = {m["curto"]: [esc(vf, f"f{m['cap']}"), esc(vh, f"h{m['cap']}")] for m in MODOS}
    cap["Cargas Auxiliares"] = cap.pop("Neutro")
    st.markdown("### 4. Balanço de Carga por Modo (Ah)")
    plotar_balanco_carga(["ITEMM FTP", "ITEMM HGW"], cap)


# =======================================================================
# 11. CORRELAÇÕES
# =======================================================================
def pagina_correlacoes(arquivo_1, arquivo_2):
    st.title("Correlações entre variáveis")
    ciclos = ciclos_carregados(arquivo_1, arquivo_2)
    if not ciclos:
        st.info("Envie pelo menos um arquivo .mat na barra lateral.")
        return
    nome = st.selectbox("Ciclo:", [c["nome"] for c in ciclos], key="cor_ciclo")
    c = next(x for x in ciclos if x["nome"] == nome)
    dados, pref = c["dados"], c["prefixo"]
    sufixos = listar_series(dados, pref)
    if len(sufixos) < 2:
        st.warning("Séries insuficientes neste arquivo.")
        return

    condicoes = {"Todas as amostras": None}
    for m in MODOS:
        if f"{pref}condicao_{m['cod']}" in dados:
            condicoes[m["curto"]] = m["cod"]
    cond_nome = st.selectbox("Condição operacional:", list(condicoes.keys()), key=f"cor_cond_{pref}")
    cod = condicoes[cond_nome]

    padrao = [s for s in ["Speed_com", "SOC_calc", "CorrenteFiltro", "TensaoChumbo_com", "RPM_com",
                          "LoadCarga_com", "Throttle_com", "TempBattery_com"] if s in sufixos]
    sel = st.multiselect("Variáveis na matriz:", sufixos, default=padrao, format_func=rotulo_var,
                         key=f"cor_vars_{pref}")
    if len(sel) < 2:
        st.info("Selecione ao menos duas variáveis.")
        return

    arrs = extrair(dados, pref, [f"{pref}{s}" for s in sel], cod)
    df = pd.DataFrame({rotulo_var(s): a for s, a in zip(sel, arrs)})
    if len(df) < 10:
        st.warning("Amostras insuficientes para calcular correlações.")
        return
    corr = df.corr()
    rot = list(corr.columns)
    dados_hm = [[j, i, round(float(corr.iloc[i, j]), 3) if np.isfinite(corr.iloc[i, j]) else 0.0]
                for i in range(len(rot)) for j in range(len(rot))]
    st.subheader("Matriz de correlação (Pearson)")
    grafico({
        "tooltip": {"formatter": js("""function(p){ return '<b>' + __R__[p.value[1]] + '</b> × <b>' +
            __R__[p.value[0]] + '</b><br>r = ' + Number(p.value[2]).toFixed(3).replace('.', ','); }"""
                                    .replace("__R__", json.dumps(rot, ensure_ascii=False)))},
        "grid": {"left": "22%", "right": "5%", "bottom": "26%", "top": "4%", "containLabel": True},
        "xAxis": {"type": "category", "data": rot, "axisLabel": {"rotate": 40, "fontSize": 10}},
        "yAxis": {"type": "category", "data": rot, "axisLabel": {"fontSize": 10}},
        "visualMap": {"min": -1, "max": 1, "calculable": True, "orient": "horizontal", "left": "center",
                      "bottom": "0%", "inRange": {"color": ["#2166ac", "#f7f7f7", "#b2182b"]}},
        "series": [{"type": "heatmap", "data": dados_hm,
                    "label": {"show": True, "fontSize": 10, "formatter": js(
                        "function(p){ return Number(p.value[2]).toFixed(2).replace('.', ','); }")}}],
    }, "560px", f"cor_matriz_{pref}")

    pares = []
    for i in range(len(rot)):
        for j in range(i + 1, len(rot)):
            r = corr.iloc[i, j]
            if np.isfinite(r):
                pares.append({"Variável A": rot[i], "Variável B": rot[j], "r": round(float(r), 3), "|r|": round(abs(float(r)), 3)})
    if pares:
        st.markdown("**Maiores correlações (em módulo)**")
        st.dataframe(pd.DataFrame(pares).sort_values("|r|", ascending=False).head(10),
                     use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Dispersão colorida por modo")
    c1, c2 = st.columns(2)
    sx = c1.selectbox("Eixo X:", sufixos, index=sufixos.index("Speed_com") if "Speed_com" in sufixos else 0,
                      format_func=rotulo_var, key=f"cor_x_{pref}")
    resto = [s for s in sufixos if s != sx]
    sy = c2.selectbox("Eixo Y:", resto, format_func=rotulo_var, key=f"cor_y_{pref}")
    x, y, md = extrair(dados, pref, [f"{pref}{sx}", f"{pref}{sy}"], cod, com_modos=True)
    if len(x) < 10:
        st.warning("Amostras insuficientes para a dispersão.")
        return
    rng = np.random.default_rng(0)
    series = []
    for k, nm in enumerate(CURTOS_IDX):
        idx = np.flatnonzero(md == k)
        if idx.size == 0:
            continue
        if idx.size > 3000:
            idx = rng.choice(idx, 3000, replace=False)
        cor = "#bbbbbb" if k == 0 else MODOS[k - 1]["cor"]
        series.append({"name": nm, "type": "scatter", "symbolSize": 5, "itemStyle": {"color": cor, "opacity": 0.55},
                       "data": to_pts(x[idx], y[idx])})
    r = float(np.corrcoef(x, y)[0, 1]) if np.ptp(x) > 0 and np.ptp(y) > 0 else float("nan")
    if np.isfinite(r):
        a, b = np.polyfit(x, y, 1)
        xs = np.array([x.min(), x.max()])
        series.append({"name": "Regressão linear", "type": "line", "showSymbol": False,
                       "lineStyle": {"color": "#111", "width": 2, "type": "dashed"},
                       "data": to_pts(xs, a * xs + b)})
    grafico({
        "tooltip": {"trigger": "item"},
        "legend": {"top": "2%", "data": [s["name"] for s in series]},
        "grid": {"left": "8%", "right": "4%", "bottom": "14%", "top": "12%", "containLabel": True},
        "xAxis": {"type": "value", "name": rotulo_var(sx), "nameLocation": "middle", "nameGap": 30, "scale": True},
        "yAxis": {"type": "value", "name": rotulo_var(sy), "scale": True},
        "dataZoom": [{"type": "inside", "xAxisIndex": 0}, {"type": "inside", "yAxisIndex": 0}],
        "series": series,
    }, "500px", f"cor_scatter_{pref}")
    if np.isfinite(r):
        m1, m2, m3 = st.columns(3)
        m1.metric("Correlação (r)", fmt_br(r, 3))
        m2.metric("R²", fmt_br(r ** 2, 3))
        m3.metric("Inclinação", fmt_br(float(a), 4))
        st.caption("Para legibilidade, cada modo exibe no máximo 3.000 pontos amostrados; r, R² e a regressão usam todas as amostras.")


# =======================================================================
# 12. COMPARAÇÃO
# =======================================================================
def tabela_estatistica(arquivos, prefixo, cod):
    registros, ignoradas = [], 0
    for arq in arquivos:
        dados = carregar_arquivo_mat(arq)
        if not dados:
            continue
        mascara = None
        if cod is not None:
            cond = get_serie(dados, f"{prefixo}condicao_{cod}")
            if cond is None:
                st.warning(f"{arq.name}: condição '{cod}' não encontrada. Arquivo ignorado.")
                continue
            mascara = np.isfinite(cond) & (cond > 0)
            if not mascara.any():
                st.warning(f"{arq.name}: não existem amostras para a condição selecionada.")
                continue
        for nome in dados:
            if not nome.startswith(prefixo) or nome.startswith(f"{prefixo}condicao_"):
                continue
            v = get_serie(dados, nome)
            if v is None or v.size < 2:
                continue
            if mascara is not None:
                if len(v) != len(mascara):
                    ignoradas += 1
                    continue
                v = v[mascara]
            v = v[np.isfinite(v)]
            if v.size == 0:
                continue
            p25, p50, p75 = np.percentile(v, [25, 50, 75])
            registros.append({"Arquivo": arq.name, "Variável": nome[len(prefixo):], "Amostras": int(v.size),
                              "Mínimo": float(v.min()), "P25": float(p25), "Mediana": float(p50),
                              "Média": float(v.mean()), "P75": float(p75), "Máximo": float(v.max())})
    if ignoradas and cod is not None:
        st.info(f"{ignoradas} variável(is) ignoradas por não terem o mesmo número de amostras da máscara de condição.")
    return pd.DataFrame(registros)


def grafico_boxplot_arquivos(df_var, variavel, subtitulo, chave):
    nomes = df_var["Arquivo"].tolist()
    caixas = [[round(r["Mínimo"], 3), round(r["P25"], 3), round(r["Mediana"], 3), round(r["P75"], 3),
               round(r["Máximo"], 3)] for _, r in df_var.iterrows()]
    medias = [[i, round(float(r["Média"]), 3)] for i, (_, r) in enumerate(df_var.iterrows())]
    grafico({
        "title": {"text": f"Comparação de {variavel}", "subtext": subtitulo + " | hastes: mín–máx, caixa: P25–P75, ponto: média",
                  "left": "center", "top": "2%", "textStyle": {"fontSize": 17, "fontWeight": "bold"},
                  "subtextStyle": {"fontSize": 11, "color": "#757575"}},
        "tooltip": {"trigger": "item"},
        "grid": {"left": "10%", "right": "6%", "bottom": "25%", "top": "24%", "containLabel": True},
        "xAxis": {"type": "category", "data": nomes, "axisLabel": {"rotate": 35, "interval": 0, "fontSize": 9}},
        "yAxis": {"type": "value", "name": variavel, "scale": True, "splitLine": {"show": False}},
        "series": [
            {"name": "Distribuição", "type": "boxplot", "data": caixas,
             "itemStyle": {"color": "#c9b3d6", "borderColor": COR_BOOST}},
            {"name": "Média", "type": "scatter", "data": medias, "symbolSize": 11,
             "itemStyle": {"color": COR_ALTERNADOR, "borderColor": "#fff"}, "z": 10,
             "tooltip": {"formatter": js("function(p){ return 'Média: <b>' + Number(p.value[1]).toFixed(2).replace('.', ',') + '</b>'; }")}},
        ],
    }, "560px", chave)


def exibir_kpis_e_delta(arquivos, prefixo, chave):
    linhas = []
    for arq in arquivos:
        d = carregar_arquivo_mat(arq)
        linha = {"Arquivo": arq.name}
        for suf, (rot, un) in KPIS_ESC.items():
            linha[f"{rot} ({un})"] = get_escalar(d, f"{prefixo}{suf}")
        linhas.append(linha)
    df = pd.DataFrame(linhas)
    colunas = [c for c in df.columns[1:] if df[c].notna().any()]
    if not colunas:
        st.info("Nenhum KPI escalar encontrado nos arquivos.")
        return
    df = df[["Arquivo"] + colunas]
    st.markdown("**KPIs escalares por arquivo**")
    st.dataframe(df.round(3), use_container_width=True, hide_index=True)

    ref = st.selectbox("Ensaio de referência:", df["Arquivo"].tolist(), key=f"kpi_ref_{chave}")
    base = df.loc[df["Arquivo"] == ref, colunas].iloc[0]
    delta = df.copy()
    for c in colunas:
        b = base[c]
        delta[c] = (df[c] - b) / abs(b) * 100 if pd.notna(b) and b != 0 else np.nan
    st.markdown("**Δ% em relação à referência**")
    st.dataframe(delta.round(2), use_container_width=True, hide_index=True)
    st.download_button("⬇️ KPIs (CSV)", csv_bytes(df.round(4)), f"kpis_{chave}.csv", "text/csv",
                       key=f"kpi_dl_{chave}")

    if len(df) >= 2:
        st.markdown("**Radar normalizado** (100% = maior valor entre os ensaios)")
        padrao = colunas[:6]
        sel = st.multiselect("KPIs no radar:", colunas, default=padrao, key=f"radar_sel_{chave}")
        if len(sel) >= 3:
            maximos = {c: float(df[c].abs().max()) or 1.0 for c in sel}
            grafico({
                "tooltip": {},
                "legend": {"top": "2%", "type": "scroll", "data": df["Arquivo"].tolist()},
                "radar": {"indicator": [{"name": c, "max": 100} for c in sel], "radius": "62%", "center": ["50%", "56%"]},
                "series": [{"type": "radar", "data": [
                    {"name": r["Arquivo"], "value": [round(abs(float(r[c])) / maximos[c] * 100, 1) if pd.notna(r[c]) else 0
                                                     for c in sel]} for _, r in df.iterrows()]}],
            }, "520px", f"radar_{chave}")
        else:
            st.caption("Selecione ao menos 3 KPIs para o radar.")


def exibir_tendencia(arquivos, prefixo, chave):
    itens = []
    for arq in arquivos:
        info = parse_nome(arq.name)
        if info:
            itens.append((arq, info))
    if len(itens) < 2:
        st.info("A tendência por data requer ao menos 2 arquivos nomeados como "
                "'AGM - L2 - 23092026 - FTP.mat' (bateria - data ddmmaaaa - ciclo).")
        return
    opcoes = {f"{rot} ({un})": suf for suf, (rot, un) in KPIS_ESC.items()}
    kpi_nome = st.selectbox("KPI:", list(opcoes.keys()), key=f"tend_kpi_{chave}")
    suf = opcoes[kpi_nome]
    por_bat = {}
    for arq, info in itens:
        v = get_escalar(carregar_arquivo_mat(arq), f"{prefixo}{suf}")
        if v is not None:
            por_bat.setdefault(info["bateria"], []).append([info["data"].strftime("%Y-%m-%d"), round(v, 4), arq.name])
    if not por_bat:
        st.warning("O KPI selecionado não existe nos arquivos.")
        return
    series = []
    for bat, pts in sorted(por_bat.items()):
        pts.sort(key=lambda p: p[0])
        series.append({"name": f"Bateria {bat}", "type": "line", "symbolSize": 9, "data": pts,
                       "label": {"show": True, "position": "top", "formatter": js(
                           "function(p){ return Number(p.value[1]).toFixed(2).replace('.', ','); }")}})
    grafico({
        "title": {"text": f"Tendência — {kpi_nome}", "left": "center"},
        "tooltip": {"trigger": "item", "formatter": js("""function(p){ return '<b>' + p.seriesName + '</b><br>' + p.value[0] +
            '<br>' + Number(p.value[1]).toFixed(2).replace('.', ',') + '<br><small>' + p.value[2] + '</small>'; }""")},
        "legend": {"top": "8%"},
        "grid": {"left": "8%", "right": "6%", "bottom": "12%", "top": "20%", "containLabel": True},
        "xAxis": {"type": "time", "axisLabel": {"formatter": "{dd}/{MM}/{yyyy}"}},
        "yAxis": {"type": "value", "name": kpi_nome, "scale": True, "splitLine": {"show": False}},
        "series": series,
    }, "460px", f"tend_{chave}")


def exibir_graficos_modos(arquivos, prefixo, chave):
    nomes, pcts, caps = [], {m["nome"]: [] for m in MODOS}, {m["nome"]: [] for m in MODOS}
    for arq in arquivos:
        d = carregar_arquivo_mat(arq)
        if not d:
            continue
        nomes.append(arq.name)
        for m in MODOS:
            p = get_escalar(d, f"{prefixo}{m['pct']}")
            if p is None:
                c = get_serie(d, f"{prefixo}condicao_{m['cod']}")
                if c is not None:
                    v = c[np.isfinite(c)]
                    p = float(np.sum(v > 0) / v.size * 100) if v.size else None
            pcts[m["nome"]].append(None if p is None else round(p, 2))
            ah = get_escalar(d, f"{prefixo}{m['cap']}")
            caps[m["nome"]].append(None if ah is None else round(ah, 2))
    cores = {m["nome"]: m["cor"] for m in MODOS}
    if any(v is not None for lst in pcts.values() for v in lst):
        st.subheader("Distribuição percentual dos modos operacionais")
        barras_agrupadas(nomes, pcts, cores, "Percentual por modo operacional",
                         "Comparação entre os arquivos analisados", "Participação (%)", f"comp_pct_{chave}")
    else:
        st.warning("Não foram encontrados dados de percentual dos modos operacionais.")
    if any(v is not None for lst in caps.values() for v in lst):
        st.divider()
        st.subheader("Capacidade elétrica por modo operacional")
        barras_agrupadas(nomes, caps, cores, "Capacidade por modo operacional",
                         "Comparação das capacidades dos arquivos analisados", "Capacidade (Ah)", f"comp_cap_{chave}")
    else:
        st.warning("Não foram encontrados dados de capacidade dos modos operacionais.")
    st.caption("Percentuais e capacidades são indicadores globais extraídos dos arquivos MAT; "
               "não são recalculados pelo filtro de condição das estatísticas.")


def exibir_comparacao_temporal(arquivos, prefixo, chave):
    if len(arquivos) < 2:
        st.info("Selecione pelo menos dois arquivos para habilitar a comparação temporal.")
        return
    idx = list(range(len(arquivos)))
    ca, cb = st.columns(2)
    ia = ca.selectbox("Primeiro arquivo:", idx, format_func=lambda i: arquivos[i].name, key=f"tmp_a_{chave}")
    ib = cb.selectbox("Segundo arquivo:", idx, index=1, format_func=lambda i: arquivos[i].name, key=f"tmp_b_{chave}")
    if ia == ib:
        st.warning("Selecione dois arquivos diferentes.")
        return
    da, db = carregar_arquivo_mat(arquivos[ia]), carregar_arquivo_mat(arquivos[ib])
    if not da or not db:
        return
    comuns = sorted(set(listar_series(da, prefixo)) & set(listar_series(db, prefixo)) - {"Speed_com"},
                    key=lambda s: list(VARS).index(s) if s in VARS else 999)
    if not comuns:
        st.warning("Os arquivos não possuem variáveis temporais em comum para o eixo direito.")
        return
    c1, c2, c3 = st.columns(3)
    sufixo = c1.selectbox("Variável do eixo direito (nos dois ensaios):", comuns, format_func=rotulo_var,
                          index=comuns.index("SOC_calc") if "SOC_calc" in comuns else 0, key=f"tmp_var_{chave}")
    layout = c2.radio("Layout:", ["Separados", "Sobrepostos"], horizontal=True, key=f"tmp_lay_{chave}")
    eixo = c3.radio("Eixo X:", ["Tempo (s)", "Distância (km)"], horizontal=True, key=f"tmp_eixo_{chave}")
    if layout == "Sobrepostos":
        grafico_sobreposto(da, db, arquivos[ia].name, arquivos[ib].name, prefixo, sufixo, eixo, f"tmp_sob_{chave}")
        return
    estilo = st.selectbox("Visualização dos modos:", ESTILOS, key=f"tmp_est_{chave}")
    sel = st.multiselect("Modos exibidos:", [m["nome"] for m in MODOS], default=[m["nome"] for m in MODOS],
                         key=f"tmp_msel_{chave}")
    modos_idx = [i for i, m in enumerate(MODOS, start=1) if m["nome"] in sel]
    fases = [("Fim transiente a frio", 505.0), ("Fim fase estabilizada", 1372.0)] \
        if prefixo == "f" and st.checkbox("Mostrar fases do FTP (505 s / 1372 s)", key=f"tmp_fases_{chave}") else None
    st.markdown("#### Primeiro ensaio")
    grafico_temporal(da, prefixo, sufixo, arquivos[ia].name, f"tmp_ga_{chave}", estilo, modos_idx, None, eixo, fases)
    st.markdown("#### Segundo ensaio")
    grafico_temporal(db, prefixo, sufixo, arquivos[ib].name, f"tmp_gb_{chave}", estilo, modos_idx, None, eixo, fases)


def bloco_comparacao(rotulo, arquivos, prefixo, chave):
    condicoes = {"Todas as amostras": None, "Boost": "boo", "Alternador": "alt",
                 "Neutro": "neu", "Frenagem regenerativa": "fre"}
    t_est, t_kpi, t_modos, t_tmp, t_tend = st.tabs(
        ["Estatísticas", "KPIs & Δ%", "Modos", "Temporal", "Tendência por data"])

    with t_est:
        cond_nome = st.selectbox(f"Condição operacional — {rotulo}:", list(condicoes.keys()), key=f"comp_cond_{chave}")
        df = tabela_estatistica(arquivos, prefixo, condicoes[cond_nome])
        if df.empty:
            st.warning(f"Não existem dados suficientes para a comparação de {rotulo} na condição selecionada.")
        else:
            df = df.sort_values(["Variável", "Arquivo"]).reset_index(drop=True)
            st.caption(f"{df['Arquivo'].nunique()} arquivo(s) | {df['Variável'].nunique()} variável(is) | "
                       f"Condição: {cond_nome}")
            st.subheader(f"Resumo estatístico — {cond_nome}")
            st.dataframe(df.style.format({c: "{:.2f}" for c in ["Mínimo", "P25", "Mediana", "Média", "P75", "Máximo"]}),
                         use_container_width=True, hide_index=True)
            st.download_button("⬇️ Estatísticas (CSV)", csv_bytes(df.round(4)), f"estatisticas_{chave}.csv",
                               "text/csv", key=f"comp_dl_{chave}")
            st.divider()
            st.subheader("Comparação das distribuições")
            variaveis = sorted(df["Variável"].unique().tolist())
            var = st.selectbox("Variável para comparar:", variaveis, key=f"comp_var_{chave}",
                               format_func=lambda s: rotulo_var(s, False) if s in VARS else s)
            grafico_boxplot_arquivos(df[df["Variável"] == var].reset_index(drop=True),
                                     rotulo_var(var) if var in VARS else var, f"{rotulo} — {cond_nome}",
                                     f"comp_box_{chave}")
    with t_kpi:
        exibir_kpis_e_delta(arquivos, prefixo, chave)
    with t_modos:
        exibir_graficos_modos(arquivos, prefixo, chave)
    with t_tmp:
        exibir_comparacao_temporal(arquivos, prefixo, chave)
    with t_tend:
        exibir_tendencia(arquivos, prefixo, chave)


def renderizar_comparacao_arquivos():
    st.title("Comparação de Ensaios")
    st.caption(f"Compare até {MAX_ARQUIVOS_COMPARACAO} ensaios FTP e {MAX_ARQUIVOS_COMPARACAO} ensaios Highway.")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Arquivos FTP")
        ftp = st.file_uploader(f"Selecione até {MAX_ARQUIVOS_COMPARACAO} arquivos FTP (.mat)", type=["mat"],
                               accept_multiple_files=True, key="comparacao_upload_ftp")
    with c2:
        st.subheader("Arquivos Highway")
        hgw = st.file_uploader(f"Selecione até {MAX_ARQUIVOS_COMPARACAO} arquivos Highway (.mat)", type=["mat"],
                               accept_multiple_files=True, key="comparacao_upload_hgw")
    ftp, hgw = list(ftp or []), list(hgw or [])
    if len(ftp) > MAX_ARQUIVOS_COMPARACAO:
        st.warning(f"Limite de {MAX_ARQUIVOS_COMPARACAO} arquivos FTP. Somente os primeiros serão utilizados.")
        ftp = ftp[:MAX_ARQUIVOS_COMPARACAO]
    if len(hgw) > MAX_ARQUIVOS_COMPARACAO:
        st.warning(f"Limite de {MAX_ARQUIVOS_COMPARACAO} arquivos Highway. Somente os primeiros serão utilizados.")
        hgw = hgw[:MAX_ARQUIVOS_COMPARACAO]
    st.divider()

    if ftp:
        with st.expander("Comparação dos ensaios FTP", expanded=True):
            bloco_comparacao("FTP", ftp, "f", "ftp")
    if hgw:
        with st.expander("Comparação dos ensaios Highway", expanded=True):
            bloco_comparacao("Highway", hgw, "h", "highway")
    if not ftp and not hgw:
        st.info("Selecione pelo menos um arquivo FTP ou Highway para iniciar a comparação.")


# =======================================================================
# 13. APLICAÇÃO PRINCIPAL
# =======================================================================
def main_app():
    with st.sidebar:
        st.markdown("<h2 style='color:#ce4545; text-align:center;'>- LOBOS ELETRIFICADOS -</h2>",
                    unsafe_allow_html=True)
        pagina = st.radio("Navegação", ["📈 Telemetria", "📊 Estatística", "📉 Análise",
                                        "🧩 Eventos & KPIs", "🔗 Correlações", "⚖️ Comparação"])
        st.markdown("---")
        st.markdown("### 📂 Upload de Arquivos .mat")
        arquivo_1 = st.file_uploader("Arquivo FTP (.mat)", type=["mat"], key="file1")
        arquivo_2 = st.file_uploader("Arquivo Highway (.mat)", type=["mat"], key="file2")
        st.markdown("---")
        st.markdown("### 🎛️ Filtros e exibição")
        st.slider("Faixa de velocidade (km/h)", 0, 200, (0, 200), key="filtro_vel",
                  help="Aplicado às páginas Estatística, Correlações. O limite máximo de 200 significa sem limite superior.")
        st.toggle("Gráficos em tema escuro", key="tema_escuro")
        st.info(f"⏱️ **Passo de Amostragem:** fixo em `{DT_AMOSTRAGEM} s`")
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state["authenticated"] = False
            st.rerun()

    if pagina == "📈 Telemetria":
        st.title("Painel de Telemetria Multivariável")
        tab1, tab2 = st.tabs(["📁 Arquivo .MAT 1 (FTP)", "📁 Arquivo .MAT 2 (Highway)"])
        with tab1:
            if arquivo_1:
                painel_telemetria(arquivo_1, "f", "ITEMM FTP", "tel1")
            else:
                st.info("Envie o Arquivo 1 (.mat) na barra lateral para carregar a telemetria.")
        with tab2:
            if arquivo_2:
                painel_telemetria(arquivo_2, "h", "ITEMM HGW", "tel2")
            else:
                st.info("Envie o Arquivo 2 (.mat) na barra lateral para carregar a telemetria.")

    elif pagina == "📊 Estatística":
        st.title("Estatística de Condições Operacionais")
        st.markdown("Comparativo percentual de permanência em cada condição de operação.")
        col1, col2 = st.columns(2)
        for col, arq, pref, num in ((col1, arquivo_1, "f", 1), (col2, arquivo_2, "h", 2)):
            with col:
                st.subheader(f"📁 Arquivo {num}")
                if arq:
                    itens = contagem_condicoes(carregar_arquivo_mat(arq), pref)
                    if itens:
                        plotar_pizza_condicoes(itens, f"Condições — {arq.name}", f"grafico_pizza_arq{num}")
                    else:
                        st.warning(f"Nenhuma variável de condição foi identificada no Arquivo {num}.")
                else:
                    st.info(f"Faça o upload do Arquivo {num} na barra lateral.")
        st.divider()
        renderizar_analise_estatistica(arquivo_1, arquivo_2)

    elif pagina == "📉 Análise":
        pagina_analise(arquivo_1, arquivo_2)

    elif pagina == "🧩 Eventos & KPIs":
        pagina_eventos(arquivo_1, arquivo_2)

    elif pagina == "🔗 Correlações":
        pagina_correlacoes(arquivo_1, arquivo_2)

    elif pagina == "⚖️ Comparação":
        renderizar_comparacao_arquivos()


# =======================================================================
# 14. CONTROLE DE FLUXO
# =======================================================================
if __name__ == "__main__":
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if st.session_state["authenticated"]:
        main_app()
    else:
        check_login()
