import streamlit as st
import pandas as pd
import numpy as np
import time
import matplotlib.pyplot as plt
from datetime import datetime
import matplotlib.dates as mdates

chart_data = pd.DataFrame(
        np.random.randn(20, 3),
        columns=['Fase A', 'Fase B', 'Fase C']
    )

# =======================================================================
# CONFIGURAÇÃO DA PÁGINA
# st.set_page_config() deve ser o primeiro comando Streamlit no script.
# =======================================================================
st.set_page_config(
    page_title="Técnicas de Medição",
    page_icon=":zap:",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =======================================================================
# BARRA LATERAL (SIDEBAR) PARA NAVEGAÇÃO
# =======================================================================
with st.sidebar:
    st.image("Logo_v2.png", width=100)
    
    escolha_pagina = st.radio(
        "Escolha uma opção:",
        [
            "Página Inicial",
            "GERAL",
            "Outros"
        ]
    )
    st.markdown("---")

# =======================================================================
# CONTEÚDO DAS PÁGINAS
# =======================================================================


# -----------------------------------------------------------------------
# PÁGINA INICIAL
# -----------------------------------------------------------------------
if escolha_pagina == "Página Inicial":
    st.title(":zap: Supervisório de Técnicas de Medição")
    st.markdown("""
    As despesas com energia elétrica nas atividades comerciais e industriais se apresentam como um dos maiores insumos
para o setor produtivo. Em diversos empreendimentos, não há um sistema que indique qual o consumo diário e quais
atividades consomem mais energia elétrica, ficando as empresas limitadas às análises das contas de energia elétrica.
                

A instalação de um Sistema de Monitoramento em tempo real pode auxiliar as empresas nos rastreios dos custos de
energia elétrica total ou parcial dos seus processos, auxiliando os empresários no cálculo do custo de energia elétrica
agregado a cada produto ou processo.
                

Um Sistema de Monitoramento de Energia Elétrica com supervisório funciona por meio da coleta e monitoração de
dados de consumo de energia elétrica em tempo real, com análise, processamento dos dados e apresentação dos
resultados numérica e graficamente, na forma de grandezas energéticas que caracterizam o uso da energia elétrica
das instalações.
                

Dentre as grandezas básicas monitoradas por um sistema deste tipo são:
- Demandas Ativa, Reativa e Aparente, armazenando os valores máximos ocorridos;
- Energias Ativa, Reativa e Aparente;
- Fator de Potência, armazenando sua natureza capacitiva ou indutiva bem como valores mínimos ocorridos;
- Tensões de linha e de fase; e
- Correntes
            
    """)
    # --- 1. Geração de Dados (sem alterações) ---
    @st.cache_data
    def gerar_dados_eletricos():
        n_pontos = 2 * 24 * 60
        timestamps = pd.date_range(end=datetime.now(), periods=n_pontos, freq='T')
        def gerar_serie(base, amp, n):
            tendencia = np.linspace(0, amp, n)
            ruido = np.random.normal(0, amp * 0.1, n)
            return base + tendencia + ruido
        dados = {
            'Tensão Fase A': gerar_serie(125, 3, n_pontos), 'Tensão Fase B': gerar_serie(126, 2, n_pontos), 'Tensão Fase C': gerar_serie(124, 4, n_pontos),
            'Tensão Linha AB': gerar_serie(218, 4, n_pontos), 'Tensão Linha BC': gerar_serie(219, 3, n_pontos), 'Tensão Linha CA': gerar_serie(217, 5, n_pontos),
            'Corrente A': gerar_serie(10, 2, n_pontos), 'Corrente B': gerar_serie(9, 1.5, n_pontos), 'Corrente C': gerar_serie(11, 2.5, n_pontos),
        }
        fp = 0.92
        for fase in ['A', 'B', 'C']:
            dados[f'Potência Ativa {fase}'] = dados[f'Tensão Fase {fase}'] * dados[f'Corrente {fase}'] * fp
            dados[f'Potência Reativa {fase}'] = dados[f'Tensão Fase {fase}'] * dados[f'Corrente {fase}'] * np.sin(np.arccos(fp))
            dados[f'Potência Aparente {fase}'] = dados[f'Tensão Fase {fase}'] * dados[f'Corrente {fase}']
        return pd.DataFrame(dados, index=timestamps)

    df_original = gerar_dados_eletricos()

    # ==============================================================================
    # 2. MENU DE CONTROLES NA BARRA LATERAL (SIDEBAR)
    # ==============================================================================
    # !!! ATENÇÃO: Todo este bloco de código deve estar DENTRO de um `with st.sidebar:` !!!
    # No seu código original, ele estava no corpo principal.
    st.header("⚙️ Controles do Dashboard")

    # --- Filtro de Período ---
    st.subheader("Período de Visualização")
    periodo_selecionado = st.selectbox(
        label="Selecione o período:",
        options=["15 Minutos", "1 Hora", "6 Horas", "24 Horas"],
        index=1
    )

    # --- Menu para Formato do Timestamp ---
    st.subheader("Formato do Eixo X (Tempo)")
    formatos_data = {
        "Dia/Mês Hora:Minuto": "%d/%m %H:%M",
        "Hora:Minuto:Segundo": "%H:%M:%S",
        "Dia da Semana (Abrev), Hora": "%a, %Hh",
        "Mês-Dia": "%m-%d",
    }
    
    #
    #formato_escolhido_label = st.selectbox(
    #    "Escolha o formato da data:",
    #    options=list(formatos_data.keys()),
    #    index=1
    #)

    
    formato_escolhido_str = formatos_data["Hora:Minuto:Segundo"]

    # --- Filtro de Fases Dinâmico ---
    st.subheader("Filtro de Fases")
    sufixos_disponiveis = sorted(list(set([col.split()[-1] for col in df_original.columns if len(col.split()[-1]) == 1])))
    sufixos_selecionados = []
    cols_filtro = st.columns(len(sufixos_disponiveis))
    for i, sufixo in enumerate(sufixos_disponiveis):
        with cols_filtro[i]:
            if st.checkbox(f'Fase {sufixo}', value=True, key=f'fase_{sufixo}'):
                sufixos_selecionados.append(sufixo)

    # ==============================================================================
    # 3. LÓGICA DE FILTRAGEM E PLOTAGEM
    # ==============================================================================

    # --- Filtragem por Período ---
    agora = pd.Timestamp.now()
    deltas = {
        "15 Minutos": pd.Timedelta(minutes=15),
        "1 Hora": pd.Timedelta(hours=1),
        "6 Horas": pd.Timedelta(hours=6),
        "24 Horas": pd.Timedelta(hours=24)
    }
    delta_selecionado = deltas[periodo_selecionado]
    inicio_periodo = agora - delta_selecionado
    df_filtrado_tempo = df_original[df_original.index >= inicio_periodo]

    st.markdown(f"Exibindo dados dos **{periodo_selecionado}**. Período: `{inicio_periodo.strftime('%d/%m %H:%M')}` a `{agora.strftime('%d/%m %H:%M')}`")

    if not sufixos_selecionados:
        st.warning("Selecione pelo menos uma fase na barra lateral.")
        st.stop()

    # --- Funções Helper ---
    def filtrar_colunas(todas_as_colunas, sufixos):
        return [col for col in todas_as_colunas if col.split()[-1] in sufixos]

    ### CORREÇÃO 2: ATUALIZAR A FUNÇÃO DE PLOTAGEM ###
    def plotar_matplotlib(df_data, titulo, y_label, date_format="%d/%m %H:%M", y_min=None, y_max=None, auto=False):
        fig, ax = plt.subplots(figsize=(10, 4))
        if df_data.empty:
            ax.text(0.5, 0.5, "Nenhum dado para exibir.", horizontalalignment='center', verticalalignment='center', transform=ax.transAxes)
            st.pyplot(fig)
            return
        
        for col in df_data.columns:
            ax.plot(df_data.index, df_data[col], label=col)
        
        formatter = mdates.DateFormatter(date_format)
        ax.xaxis.set_major_formatter(formatter)
        
        ax.set_title(titulo)
        ax.set_xlabel("Tempo")
        ax.set_ylabel(y_label)
        
        # A lógica agora verifica se o modo 'auto' NÃO está ativado para definir os limites
        if not auto and y_min is not None and y_max is not None:
            ax.set_ylim(y_min, y_max)
            
        ax.legend(loc='upper left', bbox_to_anchor=(1.02, 1))
        ax.grid(True, linestyle='--', alpha=0.7)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout(rect=[0, 0, 0.85, 1])
        st.pyplot(fig)

    # --- Seção de Tensões ---
    st.header("Tensões")
    tab_fase, tab_linha = st.tabs(["Tensão de Fase (V)", "Tensão de Linha (V)"])

    with tab_fase:
        cols = ['Tensão Fase A', 'Tensão Fase B', 'Tensão Fase C']
        colunas_para_plotar = filtrar_colunas(cols, sufixos_selecionados)
        if colunas_para_plotar:
            ### CORREÇÃO 3: PASSAR O FORMATO ESCOLHIDO PARA A FUNÇÃO ###
            plotar_matplotlib(
                df_filtrado_tempo[colunas_para_plotar], 
                "Tensões de Fase por Tempo", 
                "Tensão (V)",
                date_format=formato_escolhido_str # <--- Passando o formato aqui
            )

    # ... e assim por diante para os outros gráficos ...
    with tab_linha:
        cols = ['Tensão Linha AB', 'Tensão Linha BC', 'Tensão Linha CA']
        colunas_para_plotar = [c for c in cols if any(s in c for s in sufixos_selecionados)]
        if colunas_para_plotar:
            plotar_matplotlib(
                df_filtrado_tempo[colunas_para_plotar],
                "Tensões de Linha por Tempo",
                "Tensão (V)",
                date_format=formato_escolhido_str # <--- Passando o formato aqui
            )

    # (O mesmo deve ser feito para os gráficos de Corrente e Potência)
    st.divider()
    st.header("Corrente (A)")
    cols_corrente = ['Corrente A', 'Corrente B', 'Corrente C']
    colunas_para_plotar_corrente = filtrar_colunas(cols_corrente, sufixos_selecionados)
    if colunas_para_plotar_corrente:
        plotar_matplotlib(
            df_filtrado_tempo[colunas_para_plotar_corrente], 
            "Correntes por Tempo", 
            "Corrente (A)",
            date_format=formato_escolhido_str # <--- Passando o formato aqui
        )
    
    st.divider()

    # --- 5. Seção de Potências (com Colunas e Matplotlib) ---
    st.header("Potências")
    # ### CORREÇÃO DE LAYOUT: Mudei para 3 colunas para acomodar todos os gráficos ###
    col_ativa, col_reativa = st.columns(2)

    with col_ativa:
        st.subheader("Ativa (W)")
        cols_pot_ativa = ['Potência Ativa A', 'Potência Ativa B', 'Potência Ativa C']
        colunas_para_plotar = filtrar_colunas(cols_pot_ativa, sufixos_selecionados)
        if colunas_para_plotar:
            # ### CORREÇÃO 1: Usar o DataFrame filtrado por tempo ###
            df_para_plotar = df_filtrado_tempo[colunas_para_plotar]
            
            # ### CORREÇÃO 2: Passar o formato da data ###
            plotar_matplotlib(
                df_para_plotar, 
                "", 
                "Potência (W)", 
                auto=True, # Deixando o eixo Y automático para potências
                date_format=formato_escolhido_str
            )
        else:
            st.info("Nenhuma Potência Ativa selecionada.")

    with col_reativa:
        st.subheader("Reativa (VAr)")
        cols_pot_reativa = ['Potência Reativa A', 'Potência Reativa B', 'Potência Reativa C']
        colunas_para_plotar = filtrar_colunas(cols_pot_reativa, sufixos_selecionados)
        if colunas_para_plotar:
            # ### CORREÇÃO 1: Usar o DataFrame filtrado por tempo ###
            df_para_plotar = df_filtrado_tempo[colunas_para_plotar]
            
            # ### CORREÇÃO 2: Passar o formato da data ###
            plotar_matplotlib(
                df_para_plotar, 
                "", 
                "Potência (VAr)", 
                auto=True,
                date_format=formato_escolhido_str
            )
        else:
            st.info("Nenhuma Potência Reativa selecionada.")
            
    st.subheader("Aparente (VA)")
    cols_pot_aparente = ['Potência Aparente A', 'Potência Aparente B', 'Potência Aparente C']
    colunas_para_plotar = filtrar_colunas(cols_pot_aparente, sufixos_selecionados)
    if colunas_para_plotar:
        # ### CORREÇÃO 1: Usar o DataFrame filtrado por tempo ###
        df_para_plotar = df_filtrado_tempo[colunas_para_plotar]
        
        # ### CORREÇÃO 2: Passar o formato da data ###
        plotar_matplotlib(
            df_para_plotar, 
            "", 
            "Potência (VA)", 
            auto=True,
            date_format=formato_escolhido_str
        )
    else:
        st.info("Nenhuma Potência Aparente selecionada.")

# -----------------------------------------------------------------------
# GERAL
# -----------------------------------------------------------------------
elif escolha_pagina == "GERAL":
    st.header("🖥️ Geral")

    st.header("Análise das Tensões e Correntes")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Tensões")
        tab1, tab2 = st.tabs(["Tensão de fase", "Tensão de linha"])
        with tab1:
            st.line_chart(chart_data*1.41)
        with tab2:
            st.line_chart(chart_data)
        st.divider()

    with col2:
        st.subheader("Corrente")
        st.markdown("As correntes de fase e linha desse sistema de potência são iguais, portanto, não há necessário distinção.")
        st.line_chart(chart_data*0.1)
        st.divider()


    st.header("Análise das Potências")
    st.markdown("Analisando-se as potências, pode-se analisar-se seus valores atuais, estimativas de fator de potência, assim como seus máximos")

    st.header("Potências Máximas")

    pot_ativa_max_a = 10
    pot_ativa_max_b = 12
    pot_ativa_max_c = 15

    media_pw = (pot_ativa_max_a + pot_ativa_max_b + pot_ativa_max_c)/3

    tab1, tab2, tab3 = st.tabs(["Fase A", "Fase B", "Fase C"])
    with tab1:
            st.subheader("Fase A")
            col1, col2, col3 = st.columns(3)
            relacao_pw_a = pot_ativa_max_a - media_pw
            col1.metric("Potência Ativa", f"{pot_ativa_max_a:.2f} W", f"{relacao_pw_a:.2f} W | Média: {media_pw:.2f} W")
            col2.metric("Potência Reativa", "800 var", "-8%")
            col3.metric("Potência Aparente", "1500 VA", "12%", delta_color="inverse")
    with tab2:
            st.subheader("Fase B")
            col1, col2, col3 = st.columns(3)
            relacao_pw_a = pot_ativa_max_b - media_pw
            col1.metric("Potência Ativa", f"{pot_ativa_max_a:.2f} W", f"{relacao_pw_a:.2f} W | Média: {media_pw:.2f} W")
            col2.metric("Potência Reativa", "800 var", "-8%")
            col3.metric("Potência Aparente", "1500 VA", "12%", delta_color="inverse")
    with tab3:
            st.subheader("Fase C")
            col1, col2, col3 = st.columns(3)
            relacao_pw_a = pot_ativa_max_c - media_pw
            col1.metric("Potência Ativa", f"{pot_ativa_max_a:.2f} W", f"{relacao_pw_a:.2f} W | Média: {media_pw:.2f} W")
            col2.metric("Potência Reativa", "800 var", "-8%")
            col3.metric("Potência Aparente", "1500 VA", "12%", delta_color="inverse")
    st.divider()

    st.header("Fator de Potência")
    fp_a = 0.82
    fp_b = 0.83
    fp_c = 0.84

    media_fp = (fp_a + fp_b + fp_c)/3

    rel_fp_a = fp_a - media_fp
    rel_fp_b = fp_b - media_fp
    rel_fp_c = fp_c - media_fp


    col1, col2, col3 = st.columns(3)
    col1.metric("FP (A)", f"{fp_a:.2f}", f"{rel_fp_a:.2f}| Média: {media_fp:.2f}")
    col2.metric("FP (B)", f"{fp_b:.2f}", f"{rel_fp_b:.2f}| Média: {media_fp:.2f}")
    col3.metric("FP (C)", f"{fp_c:.2f}", f"{rel_fp_c:.2f}| Média: {media_fp:.2f}")
    st.divider()

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        st.subheader("POTÊNCIA ATIVA")
        st.line_chart(chart_data)
        st.divider()

    with col2:
        st.subheader("POTÊNCIA REATIVA")
        st.line_chart(chart_data)
        st.divider()

    with col3:
        st.subheader("POTÊNCIA APARENTE")
        st.line_chart(chart_data)
        st.divider()

# -----------------------------------------------------------------------
# ELEMENTOS DE TEXTO
# -----------------------------------------------------------------------
elif escolha_pagina == "Elementos de Texto":
    st.header("🔡 Elementos de Texto")
    st.markdown("Use estes comandos para exibir texto de forma estruturada.")

    st.subheader("`st.title` e `st.header`")
    st.title("Este é um título (st.title)")
    st.header("Este é um cabeçalho (st.header)")
    st.subheader("Este é um subcabeçalho (st.subheader)")
    st.code("""
st.title("Este é um título")
st.header("Este é um cabeçalho")
st.subheader("Este é um subcabeçalho")
    """)
    st.divider()

    st.subheader("`st.markdown`, `st.text` e `st.write`")
    st.markdown("O **Markdown** permite formatação: *itálico*, `código`, [links](https://streamlit.io), etc.")
    st.text("st.text exibe texto em fonte monoespaçada, sem formatação.")
    st.write("st.write é um comando 'mágico' que renderiza quase tudo!")
    st.write({"chave": "valor", "lista": [1, 2, 3]})
    st.code("""
st.markdown("O **Markdown** permite formatação.")
st.text("st.text exibe texto em fonte monoespaçada.")
st.write("st.write renderiza quase tudo!")
    """)
    st.divider()

    st.subheader("`st.code` e `st.latex`")
    st.code("import streamlit as st\nst.write('Olá, Mundo!')", language="python")
    st.latex(r'''
        a + ar + a r^2 + a r^3 + \cdots + a r^{n-1} =
        \sum_{k=0}^{n-1} ar^k =
        a \left(\frac{1-r^{n}}{1-r}\right)
    ''')
    st.code(r"""
st.code('st.write("Olá, Mundo!")', language='python')
st.latex(r'a + ar + a r^2 = \sum_{k=0}^{2} ar^k')
    """)

# -----------------------------------------------------------------------
# EXIBIÇÃO DE DADOS
# -----------------------------------------------------------------------
elif escolha_pagina == "Exibição de Dados":
    st.header("📊 Exibição de Dados")

    st.subheader("`st.dataframe`")
    st.markdown("Exibe um DataFrame interativo (ordenável, redimensionável).")
    st.dataframe(chart_data)
    st.code("st.dataframe(meu_dataframe)")
    st.divider()

    st.subheader("`st.table`")
    st.markdown("Exibe uma tabela estática.")
    st.table(chart_data.head())
    st.code("st.table(meu_dataframe.head())")
    st.divider()

    st.subheader("`st.metric`")
    st.markdown("Exibe uma métrica em destaque, ideal para dashboards.")
    col1, col2, col3 = st.columns(3)
    col1.metric("Temperatura", "25 °C", "1.2 °C")
    col2.metric("Umidade", "76%", "-8%")
    col3.metric("Vendas (Mês)", "R$ 150.3k", "12%", delta_color="inverse")
    st.code("""
col1, col2, col3 = st.columns(3)
col1.metric("Temperatura", "25 °C", "1.2 °C")
col2.metric("Umidade", "76%", "-8%")
col3.metric("Vendas (Mês)", "R$ 150.3k", "12%", delta_color="inverse")
    """)
    st.divider()

    st.subheader("`st.json`")
    st.markdown("Exibe um objeto JSON.")
    st.json({'nome': 'Streamlit', 'versao': '1.30.0', 'ativo': True})
    st.code("st.json({'nome': 'Streamlit', 'ativo': True})")


# -----------------------------------------------------------------------
# GRÁFICOS
# -----------------------------------------------------------------------
elif escolha_pagina == "Gráficos":
    st.header("📈 Gráficos")
    st.info("Todos os gráficos abaixo são gerados a partir do mesmo conjunto de dados aleatórios para facilitar a comparação.")

    st.subheader("`st.line_chart`")
    st.markdown("Ideal para visualizar dados ao longo do tempo ou de uma sequência contínua.")
    st.line_chart(chart_data)
    st.code("st.line_chart(dados)")
    st.divider()

    st.subheader("`st.area_chart`")
    st.markdown("Semelhante ao gráfico de linhas, mas preenche a área abaixo, útil para mostrar volumes cumulativos.")
    st.area_chart(chart_data)
    st.code("st.area_chart(dados)")
    st.divider()
    
    st.subheader("`st.bar_chart`")
    st.markdown("Excelente para comparar valores entre diferentes categorias.")
    st.bar_chart(chart_data)
    st.code("st.bar_chart(dados)")
    st.divider()

    st.subheader("`st.pyplot` (com Matplotlib) - CORRIGIDO")
    st.markdown("Use para total customização. Agora mostrando um gráfico de dispersão para comparar as colunas 'a' e 'b', com a cor baseada na coluna 'c'.")
    
    # Criando a figura e os eixos com Matplotlib
    fig, ax = plt.subplots(figsize=(8, 5))
    
    # Criando o gráfico de dispersão (scatter plot)
    scatter = ax.scatter(
        chart_data['a'], 
        chart_data['b'], 
        c=chart_data['c'], # Usa a coluna 'c' para definir a cor dos pontos
        cmap='viridis'     # Define um mapa de cores
    )
    
    # Adicionando rótulos, título e uma barra de cores
    ax.set_xlabel("Eixo A")
    ax.set_ylabel("Eixo B")
    ax.set_title("Gráfico de Dispersão Customizado com Matplotlib")
    ax.grid(True)
    fig.colorbar(scatter, ax=ax, label="Valor de C")
    
    # Exibindo o gráfico no Streamlit
    st.pyplot(fig)
    
    st.code("""
import matplotlib.pyplot as plt

# Criando a figura e os eixos
fig, ax = plt.subplots()

# Criando o gráfico de dispersão
scatter = ax.scatter(
    dados['a'], 
    dados['b'], 
    c=dados['c'], # Cor baseada na coluna 'c'
    cmap='viridis'
)

# Adicionando customizações
ax.set_xlabel("Eixo A")
ax.set_ylabel("Eixo B")
ax.set_title("Gráfico de Dispersão Customizado")
ax.grid(True)
fig.colorbar(scatter, ax=ax, label="Valor de C")

# Exibindo no Streamlit
st.pyplot(fig)
    """)
    st.divider()
    
    st.subheader("`st.plotly_chart`")
    st.markdown("Ótimo para gráficos interativos (zoom, pan, tooltips) com poucas linhas de código.")
    try:
        import plotly.express as px
        fig_plotly = px.scatter(
            chart_data, 
            x='a', 
            y='b', 
            color='c', 
            title="Gráfico de Dispersão Interativo com Plotly"
        )
        st.plotly_chart(fig_plotly, use_container_width=True)
    except ImportError:
        st.warning("A biblioteca Plotly não está instalada. Execute: pip install plotly")
    st.code("""
import plotly.express as px
fig = px.scatter(dados, x='a', y='b', color='c')
st.plotly_chart(fig, use_container_width=True)
    """)


# -----------------------------------------------------------------------
# WIDGETS INTERATIVOS
# -----------------------------------------------------------------------
elif escolha_pagina == "Widgets Interativos (Inputs)":
    st.header("👆 Widgets Interativos (Inputs)")

    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Seleção")
        st.checkbox("Marque-me")
        st.radio("Escolha uma opção", ["A", "B", "C"])
        st.selectbox("Selecione um item", ["Maçã", "Laranja", "Banana"])
        st.multiselect("Selecione múltiplos itens", ["Python", "Streamlit", "Pandas"], default=["Streamlit"])

    with col2:
        st.subheader("Entrada de Dados")
        st.text_input("Seu nome", placeholder="Digite aqui...")
        st.number_input("Sua idade", min_value=0, max_value=120, value=25)
        st.date_input("Data de nascimento")
        st.color_picker("Escolha uma cor", "#00f900")
    
    st.divider()
    
    st.subheader("Sliders e Botões")
    st.slider("Nível de satisfação", 1, 10, 8)
    st.select_slider("Selecione uma faixa", options=['Baixo', 'Médio', 'Alto'])
    
    if st.button("Clique em mim"):
        st.success("Botão clicado!")
        
    st.download_button(
        label="Baixar dados de exemplo",
        data=chart_data.to_csv(index=False).encode('utf-8'),
        file_name='dados_exemplo.csv',
        mime='text/csv',
    )
    
    st.divider()

    st.subheader("Inputs de Arquivo")
    st.file_uploader("Envie um arquivo")

    st.divider()

    st.subheader("`st.form`")
    st.markdown("Agrupe widgets em um formulário para submeter todos de uma vez.")
    with st.form("meu_formulario"):
        nome = st.text_input("Nome")
        email = st.text_input("Email")
        marcado = st.checkbox("Aceito os termos")
        
        # O botão de submissão do formulário
        submitted = st.form_submit_button("Enviar")
        if submitted:
            st.write("Formulário enviado:", "Nome:", nome, "Email:", email, "Aceito:", marcado)

# -----------------------------------------------------------------------
# LAYOUT E CONTÊINERES
# -----------------------------------------------------------------------
elif escolha_pagina == "Layout e Contêineres":
    st.header("🏗️ Layout e Contêineres")

    st.subheader("`st.columns`")
    st.markdown("Cria colunas para organizar o conteúdo lado a lado.")
    col1, col2, col3 = st.columns([2, 1, 1]) # Proporções 2:1:1
    with col1:
        st.info("Esta é a coluna 1 (mais larga).")
    with col2:
        st.info("Coluna 2.")
    with col3:
        st.info("Coluna 3.")
    st.code("""
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    st.info("Coluna larga.")
    """)
    st.divider()

    st.subheader("`st.tabs`")
    st.markdown("Cria abas para separar conteúdos.")
    tab1, tab2 = st.tabs(["Gráfico", "Tabela"])
    with tab1:
        st.line_chart(chart_data)
    with tab2:
        st.dataframe(chart_data)
    st.code("""
tab1, tab2 = st.tabs(["Aba 1", "Aba 2"])
with tab1:
    st.write("Conteúdo da Aba 1")
    """)
    st.divider()

    st.subheader("`st.expander`")
    st.markdown("Oculta conteúdo em uma seção expansível.")
    with st.expander("Clique para ver mais detalhes"):
        st.write("Este conteúdo estava oculto! É ótimo para informações adicionais.")
        st.image("https://static.streamlit.io/examples/cat.jpg")
    st.code("""
with st.expander("Clique para ver"):
    st.write("Conteúdo oculto...")
    """)
    st.divider()

    st.subheader("`st.container` e `st.empty`")
    st.markdown("`st.container` cria um bloco para agrupar elementos. `st.empty` cria um espaço reservado que pode ser preenchido ou alterado depois.")
    with st.container():
        st.write("Este é um contêiner.")
        st.bar_chart(np.random.randn(50, 3))

    placeholder = st.empty()
    if st.button("Preencher o espaço vazio"):
        placeholder.success("O espaço vazio foi preenchido com esta mensagem!")
    st.code("""
placeholder = st.empty()
if st.button("Preencher"):
    placeholder.success("Pronto!")
    """)

# -----------------------------------------------------------------------
# MÍDIA
# -----------------------------------------------------------------------
elif escolha_pagina == "Mídia":
    st.header("🖼️ Mídia")

    st.subheader("`st.image`")
    st.image("https://storage.googleapis.com/streamlit-public-media/gallery/cat.jpg",
             caption="Um gato fofo. Imagem de exemplo do Streamlit.", width=300)
    st.code("st.image(url, caption='Legenda', width=300)")
    st.divider()

    st.subheader("`st.audio`")
    st.audio("https://storage.googleapis.com/streamlit-public-media/gallery/B_T_V_2020-09-08.mp3")
    st.code("st.audio(url_do_audio)")
    st.divider()
    
    st.subheader("`st.video`")
    st.video("https://storage.googleapis.com/streamlit-public-media/gallery/cat-rolling.mp4")
    st.code("st.video(url_do_video)")
    
# -----------------------------------------------------------------------
# STATUS E PROGRESSO
# -----------------------------------------------------------------------
elif escolha_pagina == "Status e Progresso":
    st.header("⏳ Status e Progresso")

    st.subheader("Barras de Progresso e Spinners")
    if st.button("Iniciar processo demorado"):
        st.toast("Começando!")
        progress_bar = st.progress(0, text="Aguarde...")
        for i in range(100):
            time.sleep(0.01)
            progress_bar.progress(i + 1, text=f"Processando item {i+1}...")
        progress_bar.empty()
        st.success("Processo concluído!")

    with st.spinner('Esperando por algo...'):
        time.sleep(2)
    st.write("Algo aconteceu!")
    
    with st.status("Detalhes do processo...", expanded=True) as status:
        st.write("Procurando por arquivos...")
        time.sleep(1)
        st.write("Encontrado 10 arquivos.")
        time.sleep(1)
        st.write("Processo finalizado.")
        status.update(label="Download completo!", state="complete")

    st.subheader("Mensagens de Alerta")
    st.success("Esta é uma mensagem de sucesso.")
    st.info("Esta é uma mensagem informativa.")
    st.warning("Esta é uma mensagem de aviso.")
    st.error("Esta é uma mensagem de erro.")
    
    try:
        x = 1 / 0
    except Exception as e:
        st.exception(e)
        
    st.subheader("Animações divertidas")
    col1, col2 = st.columns(2)
    if col1.button("Mostrar balões 🎈"):
        st.balloons()
    if col2.button("Mostrar neve ❄️"):
        st.snow()


# -----------------------------------------------------------------------
# Outros
# -----------------------------------------------------------------------
if escolha_pagina == "Outros":

    st.subheader("Controles dos Eixos Y")
    # --- Controle para Tensão de Fase ---
    st.markdown("**Tensão de Fase (V)**")
    auto_tensao_fase = st.checkbox("Eixo Automático", key="auto_tf", value=False)
    col1_tf, col2_tf = st.columns(2)
    with col1_tf:
        y_min_tf = st.number_input("Mínimo", key="y_min_tf", value=115.0, step=1.0, format="%.1f", disabled=auto_tensao_fase)
    with col2_tf:
        y_max_tf = st.number_input("Máximo", key="y_max_tf", value=130.0, step=1.0, format="%.1f", disabled=auto_tensao_fase)

    # --- Controle para Tensão de Linha ---
    st.markdown("**Tensão de Linha (V)**")
    auto_tensao_linha = st.checkbox("Eixo Automático", key="auto_tl", value=False)
    col1_tl, col2_tl = st.columns(2)
    with col1_tl:
        y_min_tl = st.number_input("Mínimo", key="y_min_tl", value=210.0, step=1.0, format="%.1f", disabled=auto_tensao_linha)
    with col2_tl:
        y_max_tl = st.number_input("Máximo", key="y_max_tl", value=225.0, step=1.0, format="%.1f", disabled=auto_tensao_linha)

    # --- Controle para Corrente ---
    st.markdown("**Corrente (A)**")
    auto_corrente = st.checkbox("Eixo Automático", key="auto_corr", value=True) # Deixar automático por padrão
    col1_c, col2_c = st.columns(2)
    with col1_c:
        y_min_c = st.number_input("Mínimo", key="y_min_c", value=8.0, step=0.5, format="%.1f", disabled=auto_corrente)
    with col2_c:
        y_max_c = st.number_input("Máximo", key="y_max_c", value=15.0, step=0.5, format="%.1f", disabled=auto_corrente)