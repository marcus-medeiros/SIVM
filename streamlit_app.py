import streamlit as st

# Configuração da página
st.set_page_config(
    page_title="Login - SIVM",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Estilo da tela de login
st.markdown(
    """
    <style>
    .stApp {
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

    div.stButton > button {
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
    </style>
    """,
    unsafe_allow_html=True
)

# Centralização do formulário
_, coluna_login, _ = st.columns([1, 1.5, 1])

with coluna_login:
    st.markdown(
        "<h1 class='login-title'>- SIVM -</h1>",
        unsafe_allow_html=True
    )

    usuario = st.text_input(
        "Usuário",
        placeholder="Digite seu usuário"
    )

    senha = st.text_input(
        "Senha",
        type="password",
        placeholder="Digite sua senha"
    )

    if st.button("Entrar", use_container_width=True):
        if usuario == "admin" and senha == "admin":
            st.session_state["authenticated"] = True
            st.success("Login realizado com sucesso!")
        else:
            st.session_state["authenticated"] = False
            st.error("Usuário ou senha inválidos.")
