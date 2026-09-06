import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import extra_streamlit_components as stx

# ==========================================
# CONFIGURAÇÃO DA PÁGINA (Sempre o 1º comando)
# ==========================================
st.set_page_config(page_title="Minhas Finanças", page_icon="💰", layout="wide")

# ==========================================
# GERENCIADOR DE COOKIES (Lembrar Senha)
# ==========================================
@st.cache_resource
def get_manager():
    return stx.CookieManager()

cookie_manager = get_manager()

# ==========================================
# SISTEMA DE LOGIN (TELA DE BLOQUEIO)
# ==========================================
def verificar_login():
    # 1. Tenta ler o cookie do navegador (o carimbo de 30 dias)
    cookie_logado = cookie_manager.get(cookie="logado")
    
    if cookie_logado == "sim":
        st.session_state["logado"] = True
    elif "logado" not in st.session_state:
        st.session_state["logado"] = False

    if not st.session_state["logado"]:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.title("🔒 Acesso Restrito")
            st.write("Faça login uma vez. Seu celular vai lembrar da senha por 30 dias.")
            
            with st.form("form_login"):
                email = st.text_input("E-mail")
                senha = st.text_input("Senha", type="password")
                entrar = st.form_submit_button("Entrar", use_container_width=True)
                
                if entrar:
                    if "usuarios" in st.secrets:
                        if email in st.secrets["usuarios"] and str(st.secrets["usuarios"][email]) == senha:
                            st.session_state["logado"] = True
                            # 2. Cria o cookie no navegador valendo por 30 dias!
                            cookie_manager.set("logado", "sim", expires_at=datetime.now() + timedelta(days=30))
                            st.rerun()
                        else:
                            st.error("❌ E-mail ou senha incorretos.")
                    else:
                        st.error("⚠️ Lista de usuários não configurada.")
        st.stop() 

# Aciona a tranca antes de continuar
verificar_login()


# ==========================================
# CONEXÃO COM O GOOGLE SHEETS E DADOS
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=5) # Atualiza os dados a cada 5 segundos
def carregar_lancamentos():
    df = conn.read(worksheet="Lancamentos")
    df = df.dropna(how="all")
    
    colunas_obrigatorias = ["Data", "Tipo", "Categoria", "Descricao", "Valor"]
    if not set(colunas_obrigatorias).issubset(df.columns):
        return pd.DataFrame(columns=colunas_obrigatorias)
        
    return df

def salvar_lancamento(tipo, categoria, descricao, valor):
    df_atual = carregar_lancamentos()
    nova_linha = pd.DataFrame([{
        "Data": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "Tipo": tipo,
        "Categoria": categoria,
        "Descricao": descricao,
        "Valor": valor
    }])
    df_novo = pd.concat([df_atual, nova_linha], ignore_index=True)
    conn.update(worksheet="Lancamentos", data=df_novo)
    st.cache_data.clear()


# ==========================================
# PÁGINA 1: DASHBOARD (INÍCIO)
# ==========================================
def pagina_dashboard():
    st.header("🏠 Dashboard Financeiro")
    
    df = carregar_lancamentos()
    
    if df.empty:
        st.info("Você ainda não possui lançamentos. Vá em '➕ Novo Lançamento' na barra lateral para começar!")
        return
    
    df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce").fillna(0)
    
    receitas = df[df["Tipo"] == "Receita"]["Valor"].sum()
    despesas = df[df["Tipo"] == "Despesa"]["Valor"].sum()
    saldo = receitas - despesas
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Receitas", f"R$ {receitas:,.2f}")
    col2.metric("Despesas", f"R$ {despesas:,.2f}")
    col3.metric("Saldo Atual", f"R$ {saldo:,.2f}")
    
    st.divider()
    
    col_graf1, col_graf2 = st.columns(2)
    
    with col_graf1:
        df_despesas = df[df["Tipo"] == "Despesa"]
        if not df_despesas.empty:
            gastos_por_categoria = df_despesas.groupby("Categoria")["Valor"].sum().reset_index()
            fig_pizza = px.pie(gastos_por_categoria, values="Valor", names="Categoria", title="📊 Despesas por Categoria", hole=0.4)
            st.plotly_chart(fig_pizza, use_container_width=True)
        else:
            st.write("Sem despesas para o gráfico de categorias.")
            
    with col_graf2:
        if not df_despesas.empty:
            df_linha = df_despesas.copy()
            df_linha["Data_Apenas_Dia"] = pd.to_datetime(df_linha["Data"], dayfirst=True, errors="coerce").dt.date
            
            gastos_dia = df_linha.groupby("Data_Apenas_Dia")["Valor"].sum().reset_index()
            gastos_dia = gastos_dia.sort_values("Data_Apenas_Dia")
            gastos_dia["Gasto Acumulado"] = gastos_dia["Valor"].cumsum()
            
            fig_linha = px.line(
                gastos_dia, 
                x="Data_Apenas_Dia", 
                y="Gasto Acumulado", 
                title="📈 Crescimento das Despesas (Acumulado)",
                markers=True,
                text="Gasto Acumulado"
            )
            fig_linha.update_traces(textposition="top center", texttemplate="R$ %{text:,.2f}")
            fig_linha.update_layout(yaxis_title="Valor Acumulado (R$)", xaxis_title="Dia", xaxis=dict(tickformat="%d/%m/%Y"))
            st.plotly_chart(fig_linha, use_container_width=True)
        else:
            st.write("Sem despesas para o gráfico diário.")

    st.divider()
    st.subheader("📋 Últimos Lançamentos")
    st.dataframe(df.iloc[::-1], use_container_width=True, hide_index=True)


# ==========================================
# PÁGINA 2: NOVO LANÇAMENTO
# ==========================================
def pagina_novo():
    st.header("➕ Novo Lançamento")
    
    with st.form("form_novo"):
        tipo = st.selectbox("Tipo de Movimentação", ["Despesa", "Receita"])
        categoria = st.selectbox("Categoria", ["Alimentação", "Moradia", "Transporte", "Lazer", "Saúde", "Salário", "Serviços", "Outros"])
        descricao = st.text_input("Descrição (Ex: Conta de Luz, Mercado, etc)")
        valor = st.number_input("Valor (R$)", min_value=0.01, format="%.2f")
        
        salvar = st.form_submit_button("Salvar Lançamento", use_container_width=True)
        
        if salvar:
            if descricao == "":
                st.error("⚠️ Por favor, digite uma descrição para o lançamento!")
            else:
                salvar_lancamento(tipo, categoria, descricao, valor)
                st.success("✅ Lançamento salvo com sucesso!")


# ==========================================
# MENU LATERAL (SIDEBAR)
# ==========================================
st.sidebar.title("Navegação")
menu = st.sidebar.radio("Ir para:", ["🏠 Início", "➕ Novo Lançamento"])

if menu == "🏠 Início":
    pagina_dashboard()
elif menu == "➕ Novo Lançamento":
    pagina_novo()

# Botão de Logout destrói o cookie e a sessão
st.sidebar.divider()
if st.sidebar.button("🚪 Sair da Conta", use_container_width=True):
    cookie_manager.delete("logado") # Apaga o carimbo do navegador
    st.session_state["logado"] = False
    st.rerun()
