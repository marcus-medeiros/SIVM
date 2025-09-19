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
    page_title="SIVM",
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
            "Historico",
            "Configurações"
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
    st.header("🖥️ Geral")

    # --- Seleciona colunas de cada fase ---
    dados_a = df_original[['Tensão Fase A', 'Corrente A', 'Potência Ativa A', 'Potência Reativa A', 'Potência Aparente A']]
    dados_b = df_original[['Tensão Fase B', 'Corrente B', 'Potência Ativa B', 'Potência Reativa B', 'Potência Aparente B']]
    dados_c = df_original[['Tensão Fase C', 'Corrente C', 'Potência Ativa C', 'Potência Reativa C', 'Potência Aparente C']]

    pot_ativa_max_a = dados_a['Potência Ativa A'].max()
    pot_ativa_max_b = dados_b['Potência Ativa B'].max()
    pot_ativa_max_c = dados_c['Potência Ativa C'].max()
    media_pw = (pot_ativa_max_a + pot_ativa_max_b + pot_ativa_max_c) / 3

    st.header("Análise das Tensões e Correntes")
    tab1, tab2, tab3 = st.tabs(["Máquina A", "Máquina B", "Máquina C"])

    # ---------------------------
    # MÁQUINA A
    # ---------------------------
    with tab1:
        st.subheader("Máquina A")

        col_rms, col_fft = st.columns(2)
        with col_rms:
            st.write("### RMS")
            st.line_chart(dados_a[['Tensão Fase A', 'Corrente A']])
        with col_fft:
            st.write("### FFT")
            st.line_chart(np.abs(np.fft.rfft(dados_a['Tensão Fase A'])))

        col1, col2, col3 = st.columns(3)
        relacao_pw_a = pot_ativa_max_a - media_pw
        col1.metric("Potência Ativa", f"{pot_ativa_max_a:.2f} W", f"{relacao_pw_a:.2f} W | Média: {media_pw:.2f} W")
        col2.metric("Potência Reativa", f"{dados_a['Potência Reativa A'].mean():.2f} var", "-8%")
        col3.metric("Potência Aparente", f"{dados_a['Potência Aparente A'].mean():.2f} VA", "12%", delta_color="inverse")

    # ---------------------------
    # MÁQUINA B
    # ---------------------------
    with tab2:
        st.subheader("Máquina B")

        col_rms, col_fft = st.columns(2)
        with col_rms:
            st.write("### RMS")
            st.line_chart(dados_b[['Tensão Fase B', 'Corrente B']])
        with col_fft:
            st.write("### FFT")
            st.line_chart(np.abs(np.fft.rfft(dados_b['Tensão Fase B'])))

        col1, col2, col3 = st.columns(3)
        relacao_pw_b = pot_ativa_max_b - media_pw
        col1.metric("Potência Ativa", f"{pot_ativa_max_b:.2f} W", f"{relacao_pw_b:.2f} W | Média: {media_pw:.2f} W")
        col2.metric("Potência Reativa", f"{dados_b['Potência Reativa B'].mean():.2f} var", "+2%")
        col3.metric("Potência Aparente", f"{dados_b['Potência Aparente B'].mean():.2f} VA", "-5%", delta_color="inverse")

    # ---------------------------
    # MÁQUINA C
    # ---------------------------
    with tab3:
        st.subheader("Máquina C")

        col_rms, col_fft = st.columns(2)
        with col_rms:
            st.write("### RMS")
            st.line_chart(dados_c[['Tensão Fase C', 'Corrente C']])
        with col_fft:
            st.write("### FFT")
            st.line_chart(np.abs(np.fft.rfft(dados_c['Tensão Fase C'])))

        col1, col2, col3 = st.columns(3)
        relacao_pw_c = pot_ativa_max_c - media_pw
        col1.metric("Potência Ativa", f"{pot_ativa_max_c:.2f} W", f"{relacao_pw_c:.2f} W | Média: {media_pw:.2f} W")
        col2.metric("Potência Reativa", f"{dados_c['Potência Reativa C'].mean():.2f} var", "+5%")
        col3.metric("Potência Aparente", f"{dados_c['Potência Aparente C'].mean():.2f} VA", "+15%", delta_color="inverse")

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