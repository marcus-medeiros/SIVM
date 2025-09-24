import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from datetime import datetime
from streamlit_option_menu import option_menu
import io

# =======================================================================
# FUNÇÃO DA TELA DE LOGIN
# =======================================================================
def check_login():
    """Exibe a tela de login e retorna True se o login for bem-sucedido."""

    st.set_page_config(page_title="Login - SIVM", layout="centered")

    # Estilo CSS para a página de login
    st.markdown("""
    <style>
    .main {
        background-color: #f0f2f6;
    }
    .login-title {
        text-align: center;
        color: #ce4545;
        font-weight: bold;
        font-size: 2.5rem;
        text-shadow: 1px 1px #ddd;
        margin-bottom: 2rem;
    }
    /* Estiliza o botão de login */
    div.stButton > button:first-child {
        background-color: #ce4545;
        color: white;
        height: 3em;
        width: 100%;
        border-radius: 10px;
        border: none;
        font-size: 1.2rem;
        font-weight: bold;
        margin-top: 1rem;
    }
    div.stButton > button:hover {
        background-color: #a83838;
        color: white;
    }
    div.stButton > button:active {
        background-color: #902d2d;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

    # Layout da tela de login
    _, col2, _ = st.columns([1, 1.5, 1])

    with col2:
        # Adiciona a classe CSS ao container para aplicar o estilo
        
        st.markdown("<h1 class='login-title'>- SIVM -</h1>", unsafe_allow_html=True)
        
        username = st.text_input("👤 Usuário", placeholder="Digite 'admin'")
        password = st.text_input("🔑 Senha", type="password", placeholder="Digite 'admin'")
        
        if st.button("Entrar"):
            if username == 'admin' and password == 'admin':
                st.session_state['authenticated'] = True
                st.rerun()  # Recarrega o script para mostrar a aplicação principal
            else:
                st.error("Usuário ou senha inválidos.")
        
        st.markdown('</div>', unsafe_allow_html=True)

# =======================================================================
# FUNÇÃO DA APLICAÇÃO PRINCIPAL (SEU CÓDIGO)
# =======================================================================
def main_app():
    
    st.set_page_config(page_title="- SIVM -", layout="wide")

    # =======================================================================
    # INICIALIZAÇÃO DOS ESTADOS
    # =======================================================================
    if "limites_tensao" not in st.session_state:
        st.session_state["limites_tensao"] = (120.0, 140.0)

    # =======================================================================
    # GERAÇÃO DE DADOS SIMULADOS
    # =======================================================================
    @st.cache_data
    def gerar_dados_eletricos():
        n_pontos = 2 * 24 * 60
        fs = 60 * 32
        t = np.arange(n_pontos) / fs
        timestamps = pd.date_range(end=datetime.now(), periods=n_pontos, freq='T')

        def gerar_onda(amplitude, freq, n, ruido_amp=0.5, harm3=0.05, harm5=0.02):
            sinal_fundamental = amplitude * np.sin(2 * np.pi * freq * t[:n])
            sinal_3a = harm3 * amplitude * np.sin(2 * np.pi * (3 * freq) * t[:n])
            sinal_5a = harm5 * amplitude * np.sin(2 * np.pi * (5 * freq) * t[:n])
            ruido = np.random.normal(0, ruido_amp, n)
            return sinal_fundamental + sinal_3a + sinal_5a + ruido

        tensao_a = 127 + gerar_onda(10, 60, n_pontos)
        tensao_b = 127 + gerar_onda(10, 60, n_pontos, ruido_amp=1)
        tensao_c = 127 + gerar_onda(10, 60, n_pontos, ruido_amp=2)

        corrente_a = 10 + gerar_onda(2, 60, n_pontos, ruido_amp=0.2)
        corrente_b = 8.5 + gerar_onda(1.5, 60, n_pontos, ruido_amp=0.15)
        corrente_c = 11 + gerar_onda(2.5, 60, n_pontos, ruido_amp=0.25)

        fp = 0.92
        dados = {
            'Tensão Fase A': tensao_a,
            'Tensão Fase B': tensao_b,
            'Tensão Fase C': tensao_c,
            'Corrente A': corrente_a,
            'Corrente B': corrente_b,
            'Corrente C': corrente_c,
        }

        for fase in ['A', 'B', 'C']:
            dados[f'Potência Ativa {fase}'] = dados[f'Tensão Fase {fase}'] * dados[f'Corrente {fase}'] * fp

        return pd.DataFrame(dados, index=timestamps)

    df_original = gerar_dados_eletricos()

    # =======================================================================
    # VALORES FIXOS DAS MÁQUINAS
    # =======================================================================
    confianca_fix = {"A": 95.0, "B": 90.0, "C": 85.0}
    tempo_op_fix = {"A": 520, "B": 610, "C": 450}
    falhas_fix = {"A": 0, "B": 1, "C": 3}

    # =======================================================================
    # SIDEBAR
    # =======================================================================
    with st.sidebar:
        st.markdown("""
            <h1 style='color: #ce4545; font-size: 36px; text-align: center; 
                       text-shadow: 2px 2px #aaa; font-weight: bold; margin-bottom: 20px;'>
                - SIVM -
            </h1>
            """, unsafe_allow_html=True)
        
        escolha_pagina = option_menu(
            menu_title=None,
            options=["Página Inicial", "Histórico", "Configurações"],
            icons=["house", "clock-history", "gear"],
            default_index=0,
            styles={
                "container": {"padding": "5!important", "background-color": "#ffffff"},
                "icon": {"color": "#ce4545", "font-size": "20px"},
                "nav-link": {
                    "font-size": "16px",
                    "text-align": "left",
                    "margin": "0px",
                    "--hover-color": "#eee"
                },
                "nav-link-selected": {
                    "background-color": "#ce4545",
                    "color": "white",
                    "icon-color": "white"
                },
            }
        )

        min_limite, max_limite = st.session_state["limites_tensao"]

        def gerar_alarm_table(nome_maquina, tensao):
            df_alarme = tensao[(tensao < min_limite) | (tensao > max_limite)].to_frame(name="Tensão (V)")
            if df_alarme.empty:
                df_alarme = pd.DataFrame({"Tensão (V)": [], "Alarme": []})
            else:
                df_alarme["Alarme"] = df_alarme["Tensão (V)"].apply(
                    lambda x: "Acima do limite" if x > max_limite else "Abaixo do limite"
                )
            return df_alarme

        def indicador_alertas(df_alarme):
            n_alertas = len(df_alarme)
            if n_alertas == 0:
                return "🟢"
            elif n_alertas <= 20:
                return "🟠"
            else:
                return "🔴"

        tabela_a = gerar_alarm_table("A", df_original['Tensão Fase A'])
        tabela_b = gerar_alarm_table("B", df_original['Tensão Fase B'])
        tabela_c = gerar_alarm_table("C", df_original['Tensão Fase C'])

        st.markdown("###  --- Status das Máquinas")
        st.markdown(f" ->  **Máquina A:** {indicador_alertas(tabela_a)}")
        st.markdown(f" ->  **Máquina B:** {indicador_alertas(tabela_b)}")
        st.markdown(f" ->  **Máquina C:** {indicador_alertas(tabela_c)}")
        st.markdown("---")

    # =======================================================================
    # PÁGINA DE CONFIGURAÇÕES
    # =======================================================================
    if escolha_pagina == "Configurações":
        st.markdown("#### Configurações")
        senha = st.text_input("🔑 Digite a senha para alterar os limites:", type="password")
        if senha == "":
            st.info("Digite a senha para liberar a edição dos limites.")
        elif senha != "admin":
            st.error("❌ Senha incorreta!")
        else:
            st.success("✅ Acesso liberado. Agora você pode alterar os limites.")
            max_tensao = st.number_input(
                "Valor máximo da tensão (V)", 
                value=st.session_state["limites_tensao"][1], 
                step=1.0
            )
            min_tensao = st.number_input(
                "Valor mínimo da tensão (V)", 
                value=st.session_state["limites_tensao"][0], 
                step=1.0
            )
            if st.button("Salvar limites"):
                if min_tensao < max_tensao:
                    st.session_state["limites_tensao"] = (min_tensao, max_tensao)
                    st.success(f"✅ Limites salvos: {min_tensao} V - {max_tensao} V")
                else:
                    st.error(f"❌ O limite inferior ({min_tensao} V) é maior que o limite superior ({max_tensao} V).")

    # =======================================================================
    # PÁGINA HISTÓRICO
    # =======================================================================
    if escolha_pagina == "Histórico":
        st.markdown("#### Histórico de Alarmes")
        min_limite, max_limite = st.session_state["limites_tensao"]

        # Reutilizando a função já definida na sidebar
        tabela_a = gerar_alarm_table("A", df_original['Tensão Fase A'])
        tabela_b = gerar_alarm_table("B", df_original['Tensão Fase B'])
        tabela_c = gerar_alarm_table("C", df_original['Tensão Fase C'])

        tab_a, tab_b, tab_c = st.tabs(["Máquina A", "Máquina B", "Máquina C"])
        with tab_a:
            st.write("### Máquina A")
            st.dataframe(tabela_a)
        with tab_b:
            st.write("### Máquina B")
            st.dataframe(tabela_b)
        with tab_c:
            st.write("### Máquina C")
            st.dataframe(tabela_c)

        with io.BytesIO() as buffer:
            with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                tabela_a.to_excel(writer, sheet_name="Máquina A", index=True)
                tabela_b.to_excel(writer, sheet_name="Máquina B", index=True)
                tabela_c.to_excel(writer, sheet_name="Máquina C", index=True)
            buffer.seek(0)
            st.download_button(
                label="📥 Baixar Tabelas de Alarmes (.xlsx)",
                data=buffer,
                file_name="alarm_data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    # =======================================================================
    # PÁGINA INICIAL
    # =======================================================================
    if escolha_pagina == "Página Inicial":
        st.markdown("#### Página Inicial ")
        min_limite, max_limite = st.session_state["limites_tensao"]

        dados_a = df_original[['Tensão Fase A', 'Potência Ativa A']]
        dados_b = df_original[['Tensão Fase B', 'Potência Ativa B']]
        dados_c = df_original[['Tensão Fase C', 'Potência Ativa C']]

        media_conf = np.mean(list(confianca_fix.values()))
        tab1, tab2, tab3 = st.tabs(["Máquina A", "Máquina B", "Máquina C"])

        def exibir_maquina(nome_maquina, tensao, conf, tempo, falhas):
            col1, col2, col3 = st.columns(3)
            delta_conf = ((conf - media_conf) / media_conf) * 100
            col1.metric("Confiança do Equipamento", f"{conf:.1f} %", delta=f"{delta_conf:+.1f} %")
            
            media_tempo = np.mean(list(tempo_op_fix.values()))
            delta_tempo = ((tempo - media_tempo) / media_tempo) * 100
            col2.metric("Tempo de Operação", f"{tempo} h", delta=f"{delta_tempo:+.1f} %")

            media_falhas = np.mean(list(falhas_fix.values()))
            delta_falhas = ((falhas - media_falhas) / (media_falhas + 0.01)) * 100
            col3.metric("Falhas Detectadas", f"{falhas}", delta=f"{delta_falhas:+.1f} %", delta_color="inverse")

            col_rms, col_fft = st.columns(2)
            with col_rms:
                st.markdown("### RMS (Tensão)", help="RMS (Root Mean Square) é o valor eficaz da tensão ao longo do tempo.")
                df_tensao = pd.DataFrame({"timestamp": tensao.index, "tensao": tensao.values})
                y_min, y_max = tensao.min() - 5, tensao.max() + 5
                chart_rms = alt.Chart(df_tensao).mark_line(color="red", strokeWidth=2).encode(
                    x="timestamp:T",
                    y=alt.Y("tensao:Q", scale=alt.Scale(domain=[y_min, y_max]))
                )
                linha_min = alt.Chart(pd.DataFrame({"y": [min_limite]})).mark_rule(strokeDash=[4, 4], color="black", size=3).encode(y="y:Q")
                linha_max = alt.Chart(pd.DataFrame({"y": [max_limite]})).mark_rule(strokeDash=[4, 4], color="black", size=3).encode(y="y:Q")
                st.altair_chart(chart_rms + linha_min + linha_max, use_container_width=True)

            with col_fft:
                st.markdown("### FFT (Tensão)", help="FFT (Fast Fourier Transform) analisa as frequências presentes no sinal.")
                fft_vals = np.abs(np.fft.rfft(tensao.values))
                freq = np.fft.rfftfreq(len(tensao.values), d=1/1920)
                df_fft = pd.DataFrame({"freq": freq, "FFT": fft_vals})
                chart_fft = alt.Chart(df_fft).mark_line(color="red").encode(
                    x=alt.X("freq:Q", title="Frequência (Hz)"),
                    y=alt.Y("FFT:Q", title="Amplitude")
                )
                st.altair_chart(chart_fft, use_container_width=True)

        with tab1:
            exibir_maquina("Máquina A", dados_a['Tensão Fase A'], confianca_fix["A"], tempo_op_fix["A"], falhas_fix["A"])
        with tab2:
            exibir_maquina("Máquina B", dados_b['Tensão Fase B'], confianca_fix["B"], tempo_op_fix["B"], falhas_fix["B"])
        with tab3:
            exibir_maquina("Máquina C", dados_c['Tensão Fase C'], confianca_fix["C"], tempo_op_fix["C"], falhas_fix["C"])

        st.divider()

# =======================================================================
# CONTROLE DE FLUXO PRINCIPAL
# =======================================================================

# Inicializa o estado de autenticação se ainda não existir
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

# Verifica se o usuário está autenticado
if st.session_state['authenticated']:
    main_app()
else:
    check_login()