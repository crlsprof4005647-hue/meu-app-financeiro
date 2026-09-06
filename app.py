import os
import json
import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import date, datetime, timedelta
from streamlit_gsheets import GSheetsConnection
import extra_streamlit_components as stx

# ==========================================
# CONFIGURAÇÕES DA PÁGINA E CSS (Sempre o 1º comando)
# ==========================================
st.set_page_config(
    page_title="Minhas Finanças",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    r"""
    <style>
    /* 1. FUNDO GERAL CLARO (Bloqueia preenchimentos pretos do Dark Mode) */
    .stApp, .main, [data-testid="stHeader"] {
        background-color: #F8F9FA !important; 
    }
    
    /* 2. TEXTOS DE LEITURA (PRETO) E CONTORNOS */
    .stApp p, .stApp span, .stApp label, .stApp div, .stApp li {
        color: #111111;
    }
    
    /* 3. TÍTULOS (VERDE) */
    h1, h2, h3, h4 {
        color: #0A5C2B !important; 
        font-family: 'Inter', sans-serif !important;
        font-weight: 800 !important;
    }
    
    /* ========================================== */
    /* 4. CARTÕES DE SALDO (FUNDO VERDE -> LETRA BRANCA) */
    /* ========================================== */
    [data-testid="stMetric"] {
        background-color: #0A5C2B !important; 
        border-radius: 10px;
        padding: 20px;
        border: none !important;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
    }
    /* Letras dentro do fundo verde OBRIGATORIAMENTE brancas */
    [data-testid="stMetricLabel"] p, [data-testid="stMetricLabel"] div, [data-testid="stMetricLabel"] span,
    [data-testid="stMetricValue"] p, [data-testid="stMetricValue"] div, [data-testid="stMetricValue"] span {
        color: #FFFFFF !important; 
    }
    [data-testid="stMetricLabel"] p {
        font-size: 0.9rem !important;
        font-weight: 600;
        text-transform: uppercase;
        opacity: 0.95;
    }
    [data-testid="stMetricValue"] div {
        font-size: 2.2rem !important;
        font-weight: 800 !important;
    }
    
    /* ========================================== */
    /* 5. MENU DE NAVEGAÇÃO                       */
    /* ========================================== */
    div[role="radiogroup"] {
        background-color: #FFFFFF !important;
        padding: 5px;
        border-radius: 10px;
        border: 1px solid #0A5C2B !important;
    }
    /* Aba NÃO selecionada (Fundo Branco -> Letra Verde) */
    div[role="radiogroup"] > label[data-checked="false"] p {
        color: #0A5C2B !important;
        font-weight: 600;
    }
    /* Aba SELECIONADA (Fundo Verde -> Letra Branca) */
    div[role="radiogroup"] > label[data-checked="true"] {
        background-color: #0A5C2B !important;
        border-radius: 6px;
    }
    div[role="radiogroup"] > label[data-checked="true"] p {
        color: #FFFFFF !important; 
        font-weight: 700;
    }
    
    /* ========================================== */
    /* 6. BOTÕES DE AÇÃO E FORMULÁRIOS            */
    /* ========================================== */
    /* Botões: Amarelo com texto e borda Preto */
    .stButton > button {
        background-color: #FFD600 !important; 
        border: 1px solid #111111 !important; 
        border-radius: 8px !important;
        padding: 0.6rem 1.2rem !important;
        font-weight: 800 !important;
    }
    .stButton > button:hover {
        background-color: #E5C100 !important;
    }
    .stButton > button p, .stButton > button span {
        color: #111111 !important; 
    }
    
    /* Campos de digitação e caixas (Fundo Branco, borda Verde, texto Preto) */
    .stTextInput input,
    .stNumberInput input,
    .stDateInput input,
    .stTextArea textarea,
    .stSelectbox div[data-baseweb="select"],
    [data-testid="stForm"] {
        background-color: #FFFFFF !important;
        color: #111111 !important;
        border: 1px solid #0A5C2B !important;
        border-radius: 6px !important;
    }
    
    /* Força Tabelas a terem fundo claro */
    [data-testid="stDataFrame"] {
        background-color: #FFFFFF !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==========================================
# SISTEMA DE LOGIN (Cookies de 30 dias)
# ==========================================
cookie_manager = stx.CookieManager(key="meu_gerenciador_cookies")

def verificar_login():
    cookie_logado = cookie_manager.get(cookie="logado")
    
    if cookie_logado == "sim":
        st.session_state["logado"] = True
    elif "logado" not in st.session_state:
        st.session_state["logado"] = False

    if not st.session_state["logado"]:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.title("⚿ Acesso Restrito")
            st.write("Insira suas credenciais. O sistema manterá a sessão por 30 dias.")
            
            with st.form("form_login"):
                email = st.text_input("E-mail corporativo")
                senha = st.text_input("Senha de acesso", type="password")
                entrar = st.form_submit_button("Autenticar", use_container_width=True)
                
                if entrar:
                    if "usuarios" in st.secrets:
                        if email in st.secrets["usuarios"] and str(st.secrets["usuarios"][email]) == senha:
                            st.session_state["logado"] = True
                            cookie_manager.set("logado", "sim", expires_at=datetime.now() + timedelta(days=30))
                            st.rerun()
                        else:
                            st.error("✕ E-mail ou senha incorretos.")
                    else:
                        st.error("⚠ Lista de usuários não configurada nos Secrets.")
        st.stop() 

verificar_login()

# ==========================================
# CONFIGURAÇÃO DE ACESSO AO GOOGLE SHEETS
# ==========================================
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/148fsQSkFCtMiMcZVz-KxSuwBdMkpRH8ds1HQuBfiW-s/edit?usp=sharing"

if os.path.exists("credenciais.json"):
    os.makedirs(".streamlit", exist_ok=True)
    with open("credenciais.json", "r", encoding="utf-8") as f:
        c = json.load(f)
    chave_segura = c["private_key"].replace("\r", "").replace("\n", "\\n")
    toml_content = f"""[connections.gsheets]
type = "{c.get('type', 'service_account')}"
project_id = "{c['project_id']}"
private_key_id = "{c['private_key_id']}"
private_key = "{chave_segura}"
client_email = "{c['client_email']}"
client_id = "{c['client_id']}"
auth_uri = "{c['auth_uri']}"
token_uri = "{c['token_uri']}"
auth_provider_x509_cert_url = "{c['auth_provider_x509_cert_url']}"
client_x509_cert_url = "{c['client_x509_cert_url']}"
"""
    with open(".streamlit/secrets.toml", "w", encoding="utf-8") as f:
        f.write(toml_content)

conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_lancamentos():
    df = conn.read(spreadsheet=URL_PLANILHA, worksheet="Lancamentos", ttl=0)
    df = df.dropna(how="all")

    if not df.empty and "id" in df.columns:
        df["id"] = pd.to_numeric(df["id"], errors="coerce").fillna(0).astype(int)
        df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0.0)
        df = df.sort_values(by=["data", "id"], ascending=[False, False])
    else:
        df = pd.DataFrame(
            columns=["id", "data", "tipo", "descricao", "categoria", "conta", "valor", "vencimento", "data_pagamento", "status", "observacao"]
        )
    return df

def salvar_no_sheets(df):
    conn.update(spreadsheet=URL_PLANILHA, worksheet="Lancamentos", data=df)

def adicionar_lancamento(data_lancamento, tipo, descricao, categoria, conta, valor, vencimento, observacao):
    df = carregar_lancamentos()
    novo_id = 1 if df.empty else df["id"].max() + 1

    if tipo == "Entrada":
        status = "Recebido"
        data_pagamento = str(data_lancamento)
        vencimento_str = ""
    else:
        status = "Pendente"
        data_pagamento = ""
        vencimento_str = str(vencimento) if vencimento else ""

    nova_linha = pd.DataFrame(
        [{
            "id": novo_id,
            "data": str(data_lancamento),
            "tipo": tipo,
            "descricao": descricao,
            "categoria": categoria,
            "conta": conta,
            "valor": float(valor),
            "vencimento": vencimento_str,
            "data_pagamento": data_pagamento,
            "status": status,
            "observacao": observacao if observacao else "",
        }]
    )

    df = pd.concat([df, nova_linha], ignore_index=True)
    salvar_no_sheets(df)

def marcar_como_paga(id_lancamento):
    df = carregar_lancamentos()
    df.loc[df["id"] == id_lancamento, "status"] = "Pago"
    df.loc[df["id"] == id_lancamento, "data_pagamento"] = str(date.today())
    salvar_no_sheets(df)

def marcar_como_pendente(id_lancamento):
    df = carregar_lancamentos()
    df.loc[df["id"] == id_lancamento, "status"] = "Pendente"
    df.loc[df["id"] == id_lancamento, "data_pagamento"] = ""
    salvar_no_sheets(df)

def excluir_lancamento(id_lancamento):
    df = carregar_lancamentos()
    df = df[df["id"] != id_lancamento]
    salvar_no_sheets(df)

def moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ==========================================
# PÁGINAS DO APLICATIVO
# ==========================================
def pagina_dashboard():
    st.title("⌂ Visão Geral")
    st.write("Acompanhamento das suas finanças.")

    df = carregar_lancamentos()

    if df.empty:
        st.info("Nenhum registro localizado.")
        return

    df["data_dt"] = pd.to_datetime(df["data"], errors="coerce")
    df["mes"] = df["data_dt"].dt.to_period("M").astype(str)

    meses = sorted(df["mes"].dropna().unique(), reverse=True)
    if not meses:
        return

    mes_selecionado = st.selectbox("◫ Selecione o mês", meses)
    dados_mes = df[df["mes"] == mes_selecionado].copy()

    entradas = dados_mes.loc[dados_mes["tipo"] == "Entrada", "valor"].sum()
    despesas = dados_mes.loc[dados_mes["tipo"] == "Despesa", "valor"].sum()
    pagas = dados_mes.loc[(dados_mes["tipo"] == "Despesa") & (dados_mes["status"] == "Pago"), "valor"].sum()
    pendentes = dados_mes.loc[(dados_mes["tipo"] == "Despesa") & (dados_mes["status"] == "Pendente"), "valor"].sum()
    saldo = entradas - despesas

    st.subheader("＄ Resumo Financeiro")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Saldo do Mês", moeda(saldo))
    with col2:
        st.metric("Entradas", moeda(entradas))

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Despesas", moeda(despesas))
    with col2:
        st.metric("Pendentes", moeda(pendentes))

    st.divider()

    st.subheader("◷ Situação dos Pagamentos")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Pagas", moeda(pagas))
    with col2:
        st.metric("A Pagar", moeda(pendentes))

    st.divider()

    st.subheader("◱ Gastos por Categoria")
    gastos = dados_mes[dados_mes["tipo"] == "Despesa"]

    if not gastos.empty:
        gastos_categoria = (
            gastos.groupby("categoria", as_index=False)["valor"]
            .sum()
            .sort_values("valor", ascending=False)
        )
        grafico = px.pie(
            gastos_categoria,
            names="categoria",
            values="valor",
            hole=0.45,
            color_discrete_sequence=["#0A5C2B", "#FFD600", "#111111", "#4CAF50", "#FFEB3B"]
        )
        grafico.update_layout(paper_bgcolor="#F8F9FA", plot_bgcolor="#F8F9FA", font_color="#111111")
        st.plotly_chart(grafico, width="stretch")
    else:
        st.info("Não existem despesas neste mês.")

    st.subheader("∿ Crescimento das Despesas")
    
    if not gastos.empty:
        df_linha = gastos.copy()
        df_linha["data_limpa"] = pd.to_datetime(df_linha["data"], errors="coerce").dt.date
        
        gastos_dia = df_linha.groupby("data_limpa")["valor"].sum().reset_index()
        gastos_dia = gastos_dia.sort_values("data_limpa")
        gastos_dia["Gasto Acumulado"] = gastos_dia["valor"].cumsum()
        
        fig_linha = px.line(
            gastos_dia, 
            x="data_limpa", 
            y="Gasto Acumulado", 
            markers=True,
            text="Gasto Acumulado"
        )
        fig_linha.update_traces(textposition="top left", texttemplate="R$ %{text:,.2f}", line_color="#0A5C2B", marker_color="#FFD600")
        fig_linha.update_layout(paper_bgcolor="#F8F9FA", plot_bgcolor="#F8F9FA", font_color="#111111", yaxis_title="Acumulado (R$)", xaxis_title="Dias do Mês", xaxis=dict(tickformat="%d/%m/%Y"))
        st.plotly_chart(fig_linha, width="stretch")
    else:
        st.info("Nenhuma despesa para exibir no gráfico.")


def pagina_novo_lancamento():
    st.title("＋ Novo Lançamento")

    with st.form("form_lancamento"):
        data_lancamento = st.date_input("◫ Data", value=date.today())
        tipo = st.selectbox("Tipo", ["Despesa", "Entrada"])
        descricao = st.text_input("✎ Descrição", placeholder="Ex.: Mercado, salário, aluguel...")
        categoria = st.selectbox(
            "◪ Categoria",
            ["Salário", "Moradia", "Alimentação", "Transporte", "Contas", "Lazer", "Saúde", "Educação", "Cartão", "Investimentos", "Outros"]
        )
        conta = st.selectbox("⛀ Conta", ["Conta corrente", "Poupança", "Dinheiro", "Cartão"])
        valor = st.number_input("＄ Valor", min_value=0.01, value=0.01, step=10.00, format="%.2f")

        if tipo == "Despesa":
            vencimento = st.date_input("◷ Vencimento", value=date.today())
        else:
            vencimento = None

        observacao = st.text_area("📄 Observação")
        salvar = st.form_submit_button("✓ SALVAR REGISTRO", use_container_width=True)

    if salvar:
        if not descricao.strip():
            st.error("✕ Informe uma descrição.")
        elif valor <= 0:
            st.error("✕ Informe um valor maior que zero.")
        else:
            adicionar_lancamento(data_lancamento, tipo, descricao.strip(), categoria, conta, valor, vencimento, observacao)
            st.success("✓ Lançamento salvo com sucesso!")


def pagina_pagamentos():
    st.title("◷ Pagamentos")

    df = carregar_lancamentos()
    if df.empty:
        st.success("✓ Não existem pagamentos pendentes.")
        return

    pendentes = df[(df["tipo"] == "Despesa") & (df["status"] == "Pendente")].copy()

    if pendentes.empty:
        st.success("✓ Não existem pagamentos pendentes.")
        return

    st.write(f"**{len(pendentes)}** registro(s) aguardando pagamento.")

    for _, linha in pendentes.iterrows():
        with st.container(border=True):
            st.write(f"### {linha['descricao']}")
            st.caption(f"◪ {linha['categoria']} | Vencimento: {linha['vencimento'] if pd.notna(linha['vencimento']) and str(linha['vencimento']).strip() != '' else '-'}")
            st.write(f"Valor: **{moeda(linha['valor'])}**")

            if st.button("✓ MARCAR COMO PAGO", key=f"pagar_{linha['id']}", use_container_width=True):
                marcar_como_paga(int(linha["id"]))
                st.rerun()


def pagina_lancamentos():
    st.title("≡ Extrato Geral")

    df = carregar_lancamentos()

    if df.empty:
        st.info("Nenhum registro localizado.")
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        filtro_tipo = st.selectbox("Tipo", ["Todos", "Entrada", "Despesa"])
    with col2:
        filtro_status = st.selectbox("Status", ["Todos", "Pago", "Pendente", "Recebido"])
    with col3:
        categorias = ["Todas"] + sorted(df["categoria"].dropna().unique().tolist())
        filtro_categoria = st.selectbox("Categoria", categorias)

    dados = df.copy()

    if filtro_tipo != "Todos":
        dados = dados[dados["tipo"] == filtro_tipo]
    if filtro_status != "Todos":
        dados = dados[dados["status"] == filtro_status]
    if filtro_categoria != "Todas":
        dados = dados[dados["categoria"] == filtro_categoria]

    st.dataframe(dados, use_container_width=True, hide_index=True)
    st.divider()

    st.subheader("✎ Gerenciar Registro")
    id_alterar = st.number_input("ID do lançamento", min_value=1, step=1)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✓ Marcar Liquidado", use_container_width=True):
            if int(id_alterar) in df["id"].values:
                marcar_como_paga(int(id_alterar))
                st.rerun()
            else:
                st.error("✕ ID não localizado.")
    with col2:
        if st.button("◷ Retornar Pendente", use_container_width=True):
            if int(id_alterar) in df["id"].values:
                marcar_como_pendente(int(id_alterar))
                st.rerun()
            else:
                st.error("✕ ID não localizado.")

    confirmar = st.checkbox("Confirmar exclusão permanente")
    if st.button("✕ EXCLUIR REGISTRO", disabled=not confirmar, use_container_width=True):
        if int(id_alterar) in df["id"].values:
            excluir_lancamento(int(id_alterar))
            st.rerun()
        else:
            st.error("✕ ID não localizado.")


def pagina_relatorios():
    st.title("◱ Relatórios")

    df = carregar_lancamentos()
    if df.empty:
        st.info("Dados insuficientes para gerar relatórios.")
        return

    df["data_dt"] = pd.to_datetime(df["data"], errors="coerce")
    df["mes"] = df["data_dt"].dt.to_period("M").astype(str)

    st.subheader("∿ Evolução Mensal")
    evolucao = df.groupby(["mes", "tipo"], as_index=False)["valor"].sum()
    if not evolucao.empty:
        grafico = px.line(
            evolucao,
            x="mes",
            y="valor",
            color="tipo",
            markers=True,
            color_discrete_sequence=["#0A5C2B", "#FFD600"]
        )
        grafico.update_layout(paper_bgcolor="#F8F9FA", plot_bgcolor="#F8F9FA", font_color="#111111")
        st.plotly_chart(grafico, use_container_width=True)

    st.subheader("◫ Fechamento Mensal")
    resumo = df.pivot_table(
        index="mes", columns="tipo", values="valor", aggfunc="sum", fill_value=0
    ).reset_index()
    
    if "Entrada" not in resumo.columns:
        resumo["Entrada"] = 0
    if "Despesa" not in resumo.columns:
        resumo["Despesa"] = 0

    resumo["Saldo Final"] = resumo["Entrada"] - resumo["Despesa"]
    st.dataframe(resumo, use_container_width=True, hide_index=True)


# ==========================================
# MENUS E ROTAS (PÁGINA PRINCIPAL)
# ==========================================
st.title("◈ Painel Financeiro")

pagina = st.radio(
    "Navegação",
    ["⌂ Início", "＋ Novo", "◷ Pendentes", "≡ Extrato", "◱ Relatórios"],
    horizontal=True,
    label_visibility="collapsed",
)

st.divider()

if pagina == "⌂ Início":
    pagina_dashboard()
elif pagina == "＋ Novo":
    pagina_novo_lancamento()
elif pagina == "◷ Pendentes":
    pagina_pagamentos()
elif pagina == "≡ Extrato":
    pagina_lancamentos()
elif pagina == "◱ Relatórios":
    pagina_relatorios()

with st.sidebar:
    st.caption("Sistema")
    if st.button("⎋ Encerrar Sessão", use_container_width=True):
        cookie_manager.delete("logado")
        st.session_state["logado"] = False
        st.rerun()
