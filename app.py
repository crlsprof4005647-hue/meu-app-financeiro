import os
import json
import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import date, datetime, timedelta
from streamlit_gsheets import GSheetsConnection
import extra_streamlit_components as stx

# ==========================================
# CONFIGURAÇÕES DA PÁGINA
# ==========================================
st.set_page_config(
    page_title="Painel Financeiro",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ==========================================
# CSS ESTILO "BANCO PREMIUM" (Harmonia 60-30-10)
# ==========================================
st.markdown(
    r"""
    <style>
    /* 1. FUNDO GERAL (Cinza muito claro para descansar a vista e focar nas cores) */
    .stApp {
        background-color: #F7F9F7; 
    }
    
    /* 2. TEXTOS PADRÃO (Preto 10% para contraste perfeito no fundo claro) */
    .stApp, p, span, label, div {
        color: #111111;
    }
    
    /* 3. TÍTULOS (Verde 60%) */
    h1, h2, h3, h4 {
        color: #0A5C2B !important; 
        font-family: 'Inter', sans-serif !important;
        font-weight: 800 !important;
    }
    
    /* ========================================== */
    /* 4. CARTÕES DE SALDO (A ÂNCORA VERDE 60%)   */
    /* ========================================== */
    [data-testid="stMetric"] {
        background-color: #0A5C2B !important; 
        border-radius: 12px;
        padding: 20px 24px;
        border: none !important;
        box-shadow: 0 4px 10px rgba(10, 92, 43, 0.2);
    }
    /* Letras dentro do cartão Verde -> BRANCO para contraste perfeito */
    [data-testid="stMetricLabel"] p {
        color: #FFFFFF !important; 
        font-size: 1rem !important;
        font-weight: 600;
        text-transform: uppercase;
        opacity: 0.9;
    }
    /* Valores em dinheiro dentro do cartão Verde -> AMARELO 30% */
    [data-testid="stMetricValue"] div {
        color: #FFD600 !important; 
        font-size: 2.2rem !important;
        font-weight: 800 !important;
    }
    
    /* ========================================== */
    /* 5. MENU DE NAVEGAÇÃO                       */
    /* ========================================== */
    div[role="radiogroup"] {
        background-color: #FFFFFF;
        padding: 6px;
        border-radius: 12px;
        border: 2px solid #0A5C2B;
    }
    /* Fundo Verde quando selecionado */
    div[role="radiogroup"] > label[data-checked="true"] {
        background-color: #0A5C2B !important;
        border-radius: 8px;
    }
    /* Letra Amarela quando selecionado */
    div[role="radiogroup"] > label[data-checked="true"] p {
        color: #FFD600 !important; 
        font-weight: 800;
    }
    /* Letra Verde quando NÃO selecionado */
    div[role="radiogroup"] > label[data-checked="false"] p {
        color: #0A5C2B !important;
        font-weight: 600;
    }
    
    /* ========================================== */
    /* 6. BOTÕES DE AÇÃO (AMARELO 30% + PRETO 10%)*/
    /* ========================================== */
    .stButton > button {
        background-color: #FFD600 !important; 
        color: #111111 !important; 
        border: 2px solid #111111 !important; 
        border-radius: 8px !important;
        padding: 0.6rem 1.2rem !important;
        font-weight: 800 !important;
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        background-color: #E5C100 !important;
        box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.15) !important;
    }
    /* Garante que o texto dentro do botão seja sempre preto */
    .stButton > button p, .stButton > button span {
        color: #111111 !important;
    }
    
    /* 7. FORMULÁRIOS E CAIXAS DE DIGITAÇÃO */
    .stTextInput input,
    .stNumberInput input,
    .stDateInput input,
    .stSelectbox div[data-baseweb="select"] {
        background-color: #FFFFFF !important;
        color: #111111 !important;
        border: 1px solid #0A5C2B !important;
        border-radius: 6px !important;
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
            st.title("Acesso Restrito")
            st.write("Insira suas credenciais bancárias.")
            
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
                            st.error("Credenciais inválidas.")
                    else:
                        st.error("Configuração de sistema ausente.")
        st.stop() 

verificar_login()

# ==========================================
# CONEXÃO COM O GOOGLE SHEETS
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
    st.title("Visão Geral")
    st.write("Acompanhamento e performance financeira.")

    df = carregar_lancamentos()

    if df.empty:
        st.info("Nenhuma movimentação registrada.")
        return

    df["data_dt"] = pd.to_datetime(df["data"], errors="coerce")
    df["mes"] = df["data_dt"].dt.to_period("M").astype(str)

    meses = sorted(df["mes"].dropna().unique(), reverse=True)
    if not meses:
        return

    mes_selecionado = st.selectbox("Selecione o período", meses)
    dados_mes = df[df["mes"] == mes_selecionado].copy()

    entradas = dados_mes.loc[dados_mes["tipo"] == "Entrada", "valor"].sum()
    despesas = dados_mes.loc[dados_mes["tipo"] == "Despesa", "valor"].sum()
    pagas = dados_mes.loc[(dados_mes["tipo"] == "Despesa") & (dados_mes["status"] == "Pago"), "valor"].sum()
    pendentes = dados_mes.loc[(dados_mes["tipo"] == "Despesa") & (dados_mes["status"] == "Pendente"), "valor"].sum()
    saldo = entradas - despesas

    st.subheader("Resumo do Período")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Saldo do Mês", moeda(saldo))
    with col2:
        st.metric("Total de Entradas", moeda(entradas))

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total de Despesas", moeda(despesas))
    with col2:
        st.metric("Contas a Pagar (Pendentes)", moeda(pendentes))

    st.divider()

    st.subheader("Análise de Gastos por Categoria")
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
        st.plotly_chart(grafico, width="stretch")
    else:
        st.info("Sem registro de despesas para o período.")

    st.subheader("Crescimento de Despesas (Acumulado)")
    
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
        # Linha verde com bolinhas amarelas
        fig_linha.update_traces(textposition="top left", texttemplate="R$ %{text:,.2f}", line_color="#0A5C2B", marker_color="#FFD600")
        fig_linha.update_layout(yaxis_title="Acumulado (R$)", xaxis_title="Dias do Mês", xaxis=dict(tickformat="%d/%m/%Y"))
        st.plotly_chart(fig_linha, width="stretch")


def pagina_novo_lancamento():
    st.title("Novo Registro")

    with st.form("form_lancamento"):
        data_lancamento = st.date_input("Data da Transação", value=date.today())
        tipo = st.selectbox("Tipo", ["Despesa", "Entrada"])
        descricao = st.text_input("Descrição", placeholder="Ex.: Mensalidade, Fornecedor...")
        categoria = st.selectbox(
            "Categoria",
            ["Salário", "Moradia", "Alimentação", "Transporte", "Contas", "Lazer", "Saúde", "Educação", "Cartão", "Investimentos", "Outros"]
        )
        conta = st.selectbox("Conta", ["Conta corrente", "Poupança", "Dinheiro", "Cartão"])
        valor = st.number_input("Valor (R$)", min_value=0.01, value=0.01, step=10.00, format="%.2f")

        if tipo == "Despesa":
            vencimento = st.date_input("Data de Vencimento", value=date.today())
        else:
            vencimento = None

        observacao = st.text_area("Observações Adicionais")
        salvar = st.form_submit_button("Registrar Movimentação", use_container_width=True)

    if salvar:
        if not descricao.strip():
            st.error("Informe a descrição da transação.")
        elif valor <= 0:
            st.error("O valor deve ser superior a zero.")
        else:
            adicionar_lancamento(data_lancamento, tipo, descricao.strip(), categoria, conta, valor, vencimento, observacao)
            st.success("Transação registrada com sucesso.")


def pagina_pagamentos():
    st.title("Contas a Pagar")
    st.write("Gerenciamento de obrigações pendentes.")

    df = carregar_lancamentos()
    if df.empty:
        st.success("Nenhuma obrigação pendente no momento.")
        return

    pendentes = df[(df["tipo"] == "Despesa") & (df["status"] == "Pendente")].copy()

    if pendentes.empty:
        st.success("Nenhuma obrigação pendente no momento.")
        return

    st.write(f"**{len(pendentes)}** registro(s) aguardando liquidação.")

    for _, linha in pendentes.iterrows():
        with st.container(border=True):
            st.write(f"### {linha['descricao']}")
            st.caption(f"{linha['categoria']} | Vencimento: {linha['vencimento'] if pd.notna(linha['vencimento']) and str(linha['vencimento']).strip() != '' else 'Não informado'}")
            st.write(f"Valor: **{moeda(linha['valor'])}**")

            if st.button("Liquidar (Marcar como Pago)", key=f"pagar_{linha['id']}", use_container_width=True):
                marcar_como_paga(int(linha["id"]))
                st.rerun()


def pagina_lancamentos():
    st.title("Extrato Geral")
    st.write("Histórico completo de transações.")

    df = carregar_lancamentos()

    if df.empty:
        st.info("Nenhuma transação localizada.")
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

    st.subheader("Gerenciar Transação Específica")
    id_alterar = st.number_input("Informe o ID da transação", min_value=1, step=1)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Definir como Liquidado", use_container_width=True):
            if int(id_alterar) in df["id"].values:
                marcar_como_paga(int(id_alterar))
                st.rerun()
            else:
                st.error("ID não localizado.")
    with col2:
        if st.button("Retornar para Pendente", use_container_width=True):
            if int(id_alterar) in df["id"].values:
                marcar_como_pendente(int(id_alterar))
                st.rerun()
            else:
                st.error("ID não localizado.")

    confirmar = st.checkbox("Estou ciente que a exclusão é irreversível")
    if st.button("Excluir Registro", disabled=not confirmar, use_container_width=True):
        if int(id_alterar) in df["id"].values:
            excluir_lancamento(int(id_alterar))
            st.rerun()
        else:
            st.error("ID não localizado.")


def pagina_relatorios():
    st.title("Relatórios Consolidados")

    df = carregar_lancamentos()
    if df.empty:
        st.info("Dados insuficientes para geração de relatórios.")
        return

    df["data_dt"] = pd.to_datetime(df["data"], errors="coerce")
    df["mes"] = df["data_dt"].dt.to_period("M").astype(str)
    
    evolucao = df.groupby(["mes", "tipo"], as_index=False)["valor"].sum()
    if not evolucao.empty:
        grafico = px.line(
            evolucao,
            x="mes",
            y="valor",
            color="tipo",
            markers=True,
            title="Evolução Mensal (Receitas x Despesas)",
            color_discrete_sequence=["#0A5C2B", "#FFD600"]
        )
        st.plotly_chart(grafico, use_container_width=True)

    st.subheader("Fechamento Mensal")
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
st.title("Painel Financeiro")

pagina = st.radio(
    "Navegação",
    ["Visão Geral", "Novo Registro", "Contas a Pagar", "Extrato", "Relatórios"],
    horizontal=True,
    label_visibility="collapsed",
)

st.divider()

if pagina == "Visão Geral":
    pagina_dashboard()
elif pagina == "Novo Registro":
    pagina_novo_lancamento()
elif pagina == "Contas a Pagar":
    pagina_pagamentos()
elif pagina == "Extrato":
    pagina_lancamentos()
elif pagina == "Relatórios":
    pagina_relatorios()

with st.sidebar:
    st.caption("Configurações do Sistema")
    if st.button("Encerrar Sessão", use_container_width=True):
        cookie_manager.delete("logado")
        st.session_state["logado"] = False
        st.rerun()
