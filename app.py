import os
import json
import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import date
from streamlit_gsheets import GSheetsConnection

# ==========================================
# CONFIGURAÇÃO DE ACESSO AO GOOGLE SHEETS
# ==========================================
# ⚠️ Substitua abaixo pelo link da sua planilha
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/148fsQSkFCtMiMcZVz-KxSuwBdMkpRH8ds1HQuBfiW-s/edit?usp=sharing"

# MÁGICA: O Python lê o JSON e fabrica um secrets.toml perfeito sozinho!
if os.path.exists("credenciais.json"):
    os.makedirs(".streamlit", exist_ok=True)

    with open("credenciais.json", "r", encoding="utf-8") as f:
        c = json.load(f)

    # Limpa a chave para evitar os erros do Windows/OneDrive
    chave_segura = c["private_key"].replace("\r", "").replace("\n", "\\n")

    # Monta a estrutura exata que o Streamlit exige
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
    # Salva o arquivo oculto automaticamente
    with open(".streamlit/secrets.toml", "w", encoding="utf-8") as f:
        f.write(toml_content)

# Agora a conexão inicia perfeitamente sem conflitos de palavras!
conn = st.connection("gsheets", type=GSheetsConnection)

# ==========================================
# CONFIGURAÇÕES DA PÁGINA E CSS
# ==========================================
st.set_page_config(
    page_title="Minhas Finanças",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    r"""
    <style>
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        padding-left: 1rem;
        padding-right: 1rem;
        max-width: 1200px;
    }
    h1 { font-size: 2rem !important; font-weight: 700 !important; }
    h2 { font-size: 1.5rem !important; }
    h3 { font-size: 1.2rem !important; }
    .stButton > button {
        min-height: 45px;
        border-radius: 10px;
        font-weight: 600;
    }
    .stTextInput input,
    .stNumberInput input,
    .stDateInput input,
    .stTextArea textarea {
        border-radius: 8px;
    }
    [data-testid="stMetric"] {
        border: 1px solid rgba(128,128,128,0.25);
        border-radius: 12px;
        padding: 15px;
    }
    @media (max-width: 768px) {
        .block-container {
            padding-left: 0.7rem;
            padding-right: 0.7rem;
            padding-top: 1rem;
        }
        h1 { font-size: 1.6rem !important; }
        h2 { font-size: 1.3rem !important; }
        h3 { font-size: 1.1rem !important; }
        [data-testid="stMetric"] { padding: 10px; }
        [data-testid="stMetricValue"] {
            font-size: 1.25rem !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==========================================
# FUNÇÕES DE BANCO DE DADOS (AGORA NO SHEETS)
# ==========================================
def carregar_lancamentos():
    df = conn.read(spreadsheet=URL_PLANILHA, worksheet="Lancamentos", ttl=0)
    df = df.dropna(how="all")

    if not df.empty and "id" in df.columns:
        df["id"] = pd.to_numeric(df["id"], errors="coerce").fillna(0).astype(int)
        df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0.0)
        df = df.sort_values(by=["data", "id"], ascending=[False, False])
    else:
        df = pd.DataFrame(
            columns=[
                "id",
                "data",
                "tipo",
                "descricao",
                "categoria",
                "conta",
                "valor",
                "vencimento",
                "data_pagamento",
                "status",
                "observacao",
            ]
        )
    return df


def salvar_no_sheets(df):
    conn.update(spreadsheet=URL_PLANILHA, worksheet="Lancamentos", data=df)


def adicionar_lancamento(
    data_lancamento, tipo, descricao, categoria, conta, valor, vencimento, observacao
):
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
        [
            {
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
            }
        ]
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
    st.title("🏠 Dashboard")
    st.write("Visão geral das suas finanças.")

    df = carregar_lancamentos()

    if df.empty:
        st.info("Você ainda não possui lançamentos.")
        return

    df["data_dt"] = pd.to_datetime(df["data"], errors="coerce")
    df["mes"] = df["data_dt"].dt.to_period("M").astype(str)

    meses = sorted(df["mes"].dropna().unique(), reverse=True)
    if not meses:
        return

    mes_selecionado = st.selectbox("📅 Selecione o mês", meses)
    dados_mes = df[df["mes"] == mes_selecionado].copy()

    entradas = dados_mes.loc[dados_mes["tipo"] == "Entrada", "valor"].sum()
    despesas = dados_mes.loc[dados_mes["tipo"] == "Despesa", "valor"].sum()
    pagas = dados_mes.loc[
        (dados_mes["tipo"] == "Despesa") & (dados_mes["status"] == "Pago"), "valor"
    ].sum()
    pendentes = dados_mes.loc[
        (dados_mes["tipo"] == "Despesa") & (dados_mes["status"] == "Pendente"), "valor"
    ].sum()
    saldo = entradas - despesas

    st.subheader("💰 Resumo financeiro")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("💰 Saldo do mês", moeda(saldo))
    with col2:
        st.metric("📥 Entradas", moeda(entradas))

    col1, col2 = st.columns(2)
    with col1:
        st.metric("📤 Despesas", moeda(despesas))
    with col2:
        st.metric("⏳ Pendentes", moeda(pendentes))

    st.divider()

    st.subheader("💳 Situação dos pagamentos")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("✅ Pagas", moeda(pagas))
    with col2:
        st.metric("⏳ A pagar", moeda(pendentes))

    st.divider()

    st.subheader("📊 Gastos por categoria")
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
            title="Distribuição dos gastos",
        )
        st.plotly_chart(grafico, width="stretch")
    else:
        st.info("Não existem despesas neste mês.")

    st.subheader("📊 Entradas x Despesas")
    resumo = dados_mes.groupby("tipo", as_index=False)["valor"].sum()
    if not resumo.empty:
        grafico = px.bar(
            resumo, x="tipo", y="valor", text_auto=".2f", title="Comparação do mês"
        )
        st.plotly_chart(grafico, width="stretch")

    st.subheader("📈 Evolução financeira")
    mensal = df.groupby(["mes", "tipo"], as_index=False)["valor"].sum()
    if not mensal.empty:
        grafico = px.line(
            mensal,
            x="mes",
            y="valor",
            color="tipo",
            markers=True,
            title="Entradas e despesas ao longo dos meses",
        )
        st.plotly_chart(grafico, width="stretch")


def pagina_novo_lancamento():
    st.title("➕ Novo lançamento")
    st.write("Cadastre uma entrada ou uma despesa.")

    with st.form("form_lancamento"):
        data_lancamento = st.date_input("📅 Data", value=date.today())
        tipo = st.selectbox("Tipo", ["Despesa", "Entrada"])
        descricao = st.text_input(
            "📝 Descrição", placeholder="Ex.: Mercado, salário, aluguel..."
        )
        categoria = st.selectbox(
            "📂 Categoria",
            [
                "Salário",
                "Moradia",
                "Alimentação",
                "Transporte",
                "Contas",
                "Lazer",
                "Saúde",
                "Educação",
                "Cartão",
                "Investimentos",
                "Outros",
            ],
        )
        conta = st.selectbox(
            "🏦 Conta", ["Conta corrente", "Poupança", "Dinheiro", "Cartão"]
        )
        valor = st.number_input(
            "💵 Valor", min_value=0.01, value=0.01, step=10.00, format="%.2f"
        )

        if tipo == "Despesa":
            vencimento = st.date_input("📅 Vencimento", value=date.today())
        else:
            vencimento = None

        observacao = st.text_area("🗒️ Observação")
        salvar = st.form_submit_button("💾 SALVAR LANÇAMENTO", width="stretch")

    if salvar:
        if not descricao.strip():
            st.error("❌ Informe uma descrição.")
        elif valor <= 0:
            st.error("❌ Informe um valor maior que zero.")
        else:
            adicionar_lancamento(
                data_lancamento,
                tipo,
                descricao.strip(),
                categoria,
                conta,
                valor,
                vencimento,
                observacao,
            )
            st.success("✅ Lançamento salvo com sucesso!")


def pagina_pagamentos():
    st.title("⏳ Pagamentos")
    st.write("Despesas que ainda precisam ser pagas.")

    df = carregar_lancamentos()
    if df.empty:
        st.success("🎉 Não existem pagamentos pendentes!")
        return

    pendentes = df[(df["tipo"] == "Despesa") & (df["status"] == "Pendente")].copy()

    if pendentes.empty:
        st.success("🎉 Não existem pagamentos pendentes!")
        return

    st.write(f"Você possui **{len(pendentes)} pagamento(s)** pendente(s).")

    for _, linha in pendentes.iterrows():
        with st.container(border=True):
            st.write(f"### {linha['descricao']}")
            st.caption(f"📂 {linha['categoria']}")
            st.write(
                f"📅 Vencimento: **{linha['vencimento'] if pd.notna(linha['vencimento']) and str(linha['vencimento']).strip() != '' else '-'}**"
            )
            st.write(f"💰 Valor: **{moeda(linha['valor'])}**")

            if st.button(
                "✅ MARCAR COMO PAGA", key=f"pagar_{linha['id']}", width="stretch"
            ):
                marcar_como_paga(int(linha["id"]))
                st.rerun()


def pagina_lancamentos():
    st.title("📋 Lançamentos")

    df = carregar_lancamentos()

    if df.empty:
        st.info("Nenhum lançamento cadastrado.")
        return

    st.subheader("🔎 Filtros")
    filtro_tipo = st.selectbox("Tipo", ["Todos", "Entrada", "Despesa"])
    filtro_status = st.selectbox("Status", ["Todos", "Pago", "Pendente", "Recebido"])
    categorias = ["Todas"] + sorted(df["categoria"].dropna().unique().tolist())
    filtro_categoria = st.selectbox("Categoria", categorias)

    dados = df.copy()

    if filtro_tipo != "Todos":
        dados = dados[dados["tipo"] == filtro_tipo]
    if filtro_status != "Todos":
        dados = dados[dados["status"] == filtro_status]
    if filtro_categoria != "Todas":
        dados = dados[dados["categoria"] == filtro_categoria]

    st.dataframe(dados, width="stretch", hide_index=True)

    st.divider()

    st.subheader("✏️ Alterar lançamento")
    id_alterar = st.number_input("ID do lançamento", min_value=1, step=1)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Marcar como pago", width="stretch"):
            if int(id_alterar) in df["id"].values:
                marcar_como_paga(int(id_alterar))
                st.rerun()
            else:
                st.error("ID não encontrado.")
    with col2:
        if st.button("⏳ Marcar como pendente", width="stretch"):
            if int(id_alterar) in df["id"].values:
                marcar_como_pendente(int(id_alterar))
                st.rerun()
            else:
                st.error("ID não encontrado.")

    confirmar = st.checkbox("Confirmar exclusão")
    if st.button("🗑️ EXCLUIR", disabled=not confirmar, width="stretch"):
        if int(id_alterar) in df["id"].values:
            excluir_lancamento(int(id_alterar))
            st.rerun()
        else:
            st.error("ID não encontrado.")


def pagina_relatorios():
    st.title("📊 Relatórios")

    df = carregar_lancamentos()
    if df.empty:
        st.info("Não existem dados para gerar relatórios.")
        return

    df["data_dt"] = pd.to_datetime(df["data"], errors="coerce")
    df["mes"] = df["data_dt"].dt.to_period("M").astype(str)

    st.subheader("💸 Gastos por categoria")
    gastos = df[df["tipo"] == "Despesa"]

    if not gastos.empty:
        categoria = (
            gastos.groupby("categoria", as_index=False)["valor"]
            .sum()
            .sort_values("valor", ascending=False)
        )
        grafico = px.bar(
            categoria,
            x="categoria",
            y="valor",
            text_auto=".2f",
            title="Total gasto por categoria",
        )
        st.plotly_chart(grafico, width="stretch")

    st.subheader("📈 Evolução mensal")
    evolucao = df.groupby(["mes", "tipo"], as_index=False)["valor"].sum()
    if not evolucao.empty:
        grafico = px.line(
            evolucao,
            x="mes",
            y="valor",
            color="tipo",
            markers=True,
            title="Evolução mensal",
        )
        st.plotly_chart(grafico, width="stretch")

    st.subheader("📅 Resumo mensal")
    resumo = df.pivot_table(
        index="mes", columns="tipo", values="valor", aggfunc="sum", fill_value=0
    ).reset_index()
    if "Entrada" not in resumo.columns:
        resumo["Entrada"] = 0
    if "Despesa" not in resumo.columns:
        resumo["Despesa"] = 0

    resumo["Saldo"] = resumo["Entrada"] - resumo["Despesa"]
    st.dataframe(resumo, width="stretch", hide_index=True)


# ==========================================
# MENUS E ROTAS (PÁGINA PRINCIPAL)
# ==========================================
st.title("💰 Minhas Finanças")
st.caption("Seu controle financeiro pessoal")

pagina = st.radio(
    "Navegação",
    ["🏠 Início", "➕ Novo", "⏳ Pagamentos", "📋 Lançamentos", "📊 Relatórios"],
    horizontal=True,
    label_visibility="collapsed",
)

st.divider()

if pagina == "🏠 Início":
    pagina_dashboard()
elif pagina == "➕ Novo":
    pagina_novo_lancamento()
elif pagina == "⏳ Pagamentos":
    pagina_pagamentos()
elif pagina == "📋 Lançamentos":
    pagina_lancamentos()
elif pagina == "📊 Relatórios":
    pagina_relatorios()
