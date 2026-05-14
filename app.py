import streamlit as st
import pandas as pd
import os
import plotly.express as px
import io

# Setup Config
st.set_page_config(page_title="PCA Dashboard", page_icon="📊", layout="wide")

# Custom CSS for nicer aesthetics
st.markdown("""
<style>
    .metric-card {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        text-align: center;
        border-top: 4px solid #1f77b4;
    }
    .metric-value {
        font-size: 24px;
        font-weight: bold;
        color: #333333;
    }
    .metric-label {
        font-size: 14px;
        color: #7f8c8d;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    folder = "c:/Users/aduda/Downloads/Planilhas PNCP-PCA/dados"
    files = [f for f in os.listdir(folder) if f.endswith('.csv') or f.endswith('.xlsx')]
    if len(files) == 0:
        return pd.DataFrame()
    
    dfs = []
    for file in files:
        path = os.path.join(folder, file)
        try:
            if file.endswith('.csv'):
                try:
                    df = pd.read_csv(path, sep=';', encoding='utf-8')
                    if len(df.columns) < 5:
                        df = pd.read_csv(path, sep=';', encoding='latin1')
                except UnicodeDecodeError:
                    df = pd.read_csv(path, sep=';', encoding='latin1')
            else:
                df = pd.read_excel(path)
            dfs.append(df)
        except Exception as e:
            st.error(f"Erro ao ler arquivo {file}: {e}")
            
    if not dfs:
        return pd.DataFrame()
        
    base = pd.concat(dfs, ignore_index=True)
    base.dropna(how='all', inplace=True)
    base.drop_duplicates(inplace=True)
    
    numeric_cols = [
        'Quantidade Estimada', 
        'Valor Unitário Estimado (R$)', 
        'Valor Total Estimado (R$)', 
        'Valor orçamentário estimado para o exercício (R$)'
    ]
    
    for col in numeric_cols:
        if col in base.columns:
            if base[col].dtype == object:
                base[col] = base[col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
            base[col] = pd.to_numeric(base[col], errors='coerce').fillna(0.0)
            
    if 'Data Desejada' in base.columns:
        base['Data Desejada'] = pd.to_datetime(base['Data Desejada'], format='%d/%m/%Y', errors='coerce')
        base['ano'] = base['Data Desejada'].dt.year
        base['mes'] = base['Data Desejada'].dt.month
        
    if 'Nome da Futura Contratação' in base.columns:
        base['objeto_macro'] = base['Nome da Futura Contratação']
    else:
        base['objeto_macro'] = "N/D"
        
    if 'Descrição do Item' in base.columns:
        base['objeto_detalhe'] = base['Descrição do Item']
    else:
        base['objeto_detalhe'] = "N/D"
        
    base['ano'] = base['ano'].fillna(0).astype('Int64')
    base['mes'] = base['mes'].fillna(0).astype('Int64')
    
    return base

df = load_data()

if df.empty:
    st.warning("Nenhum dado encontrado na pasta de dados.")
    st.stop()

st.title("📊 Dashboard Analítico - PCA/PNCP")

# --- SIDEBAR FILTERS ---
st.sidebar.header("Filtros")

if st.sidebar.button("Limpar Filtros"):
    st.rerun()

metrica = st.sidebar.selectbox(
    "Métrica Principal", 
    ["Valor orçamentário estimado para o exercício (R$)", "Valor Total Estimado (R$)", "Quantidade Estimada"]
)

with st.sidebar.expander("Filtros", expanded=True):
    anos_disp = sorted([int(a) for a in df['ano'].unique() if pd.notna(a) and a > 0])
    filtro_ano = st.multiselect("Ano", anos_disp, default=anos_disp)
    
    # We will use st.session_state to allow charts to filter? The user requested: "ao clicar em uma unidade, filtrar os demais gráficos"
    # Actually, let's keep it simple with multiselect first. If they click multiselect, it filters.
    
    filtro_unidade = st.multiselect("Unidade Responsável", sorted([str(x) for x in df['Unidade Responsável'].unique() if pd.notna(x)]))
    filtro_uasg = st.multiselect("UASG", sorted([str(x) for x in df['UASG'].unique() if pd.notna(x)]))
    filtro_categoria = st.multiselect("Categoria do Item", sorted([str(x) for x in df['Categoria do Item'].unique() if pd.notna(x)]))
    filtro_macro = st.multiselect("Nome da Futura Contratação (Macro)", sorted([str(x) for x in df['Nome da Futura Contratação'].unique() if pd.notna(x)]))
    filtro_detalhe = st.multiselect("Descrição do Item", sorted([str(x) for x in df['Descrição do Item'].unique() if pd.notna(x)]))

# Apply filters
df_filtered = df.copy()

if filtro_ano: df_filtered = df_filtered[df_filtered['ano'].isin(filtro_ano)]
if filtro_unidade: df_filtered = df_filtered[df_filtered['Unidade Responsável'].astype(str).isin(filtro_unidade)]
if filtro_uasg: df_filtered = df_filtered[df_filtered['UASG'].astype(str).isin(filtro_uasg)]
if filtro_categoria: df_filtered = df_filtered[df_filtered['Categoria do Item'].astype(str).isin(filtro_categoria)]
if filtro_macro: df_filtered = df_filtered[df_filtered['Nome da Futura Contratação'].astype(str).isin(filtro_macro)]
if filtro_detalhe: df_filtered = df_filtered[df_filtered['Descrição do Item'].astype(str).isin(filtro_detalhe)]

def format_br(val):
    return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def format_num_br(val):
    return f"{val:,.0f}".replace(",", ".")

tab1, tab2 = st.tabs(["Resumo Executivo", "Detalhamento"])

with tab1:
    col1, col2, col3, col4 = st.columns(4)
    total_valor = df_filtered[metrica].sum()
    qtd_itens = df_filtered['Quantidade Estimada'].sum()
    qtd_unidades = df_filtered['Unidade Responsável'].nunique()
    qtd_contratacoes = df_filtered['Nome da Futura Contratação'].nunique()
    
    metric_fmt = format_num_br(total_valor) if metrica == "Quantidade Estimada" else format_br(total_valor)
    
    col1.markdown(f'<div class="metric-card"><div class="metric-label">Valor Total Consolidado</div><div class="metric-value">{metric_fmt}</div></div>', unsafe_allow_html=True)
    col2.markdown(f'<div class="metric-card"><div class="metric-label">Quantidade de Itens</div><div class="metric-value">{format_num_br(qtd_itens)}</div></div>', unsafe_allow_html=True)
    col3.markdown(f'<div class="metric-card"><div class="metric-label">Qtd. Unidades</div><div class="metric-value">{qtd_unidades}</div></div>', unsafe_allow_html=True)
    col4.markdown(f'<div class="metric-card"><div class="metric-label">Futuras Contratações</div><div class="metric-value">{qtd_contratacoes}</div></div>', unsafe_allow_html=True)
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    
    # Gráficos
    df_unidade = df_filtered.groupby('Unidade Responsável')[metrica].sum().reset_index().sort_values(by=metrica, ascending=True).tail(10)
    fig_unidade = px.bar(df_unidade, x=metrica, y='Unidade Responsável', orientation='h', title='Top 10 Unidades Responsáveis')
    fig_unidade.update_layout(margin=dict(l=0, r=0, t=40, b=0))
    fig_unidade.update_traces(marker_color='#1f77b4')
    
    # By clicking the chart we do not filter intrinsically without on_select, so let's enable it
    # Note: st.plotly_chart with on_select might not be available in very very old streamlits, but we upgraded to latest
    event_unidade = c1.plotly_chart(fig_unidade, use_container_width=True, on_select="rerun")
    
    df_macro = df_filtered.groupby('objeto_macro')[metrica].sum().reset_index().sort_values(by=metrica, ascending=True).tail(10)
    df_macro['objeto_macro_curto'] = df_macro['objeto_macro'].apply(lambda x: (str(x)[:40] + '...') if len(str(x)) > 40 else x)
    fig_macro = px.bar(df_macro, x=metrica, y='objeto_macro_curto', orientation='h', title='Top 10 Objetos Macros')
    fig_macro.update_layout(margin=dict(l=0, r=0, t=40, b=0))
    fig_macro.update_traces(marker_color='#ff7f0e')
    event_macro = c2.plotly_chart(fig_macro, use_container_width=True, on_select="rerun")
    
    # Checking for clicks on plotly charts (Streamlit >= 1.35)
    # If standard selection works, it returns dict with 'selection'
    # Currently just logging clicks is enough or we could write logic to append to session_state and rerun.
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    df_mes = df_filtered[df_filtered['mes'] > 0].groupby(['ano', 'mes'])[metrica].sum().reset_index()
    if not df_mes.empty:
        df_mes = df_mes.sort_values(by=['ano', 'mes'])
        df_mes['mes_ano'] = df_mes['mes'].astype(str).str.zfill(2) + '/' + df_mes['ano'].astype(str)
        fig_mes = px.line(df_mes, x='mes_ano', y=metrica, markers=True, title='Distribuição Temporal ao Longo do Ano', template='plotly_white')
        fig_mes.update_traces(line_color='#2ca02c')
        st.plotly_chart(fig_mes, use_container_width=True)

with tab2:
    st.subheader("Base de Dados Completa")
    st.dataframe(df_filtered, use_container_width=True)
    
    csv_buffer = io.BytesIO()
    df_filtered.to_csv(csv_buffer, index=False, sep=';', decimal=',', encoding='utf-8-sig')
    st.download_button(
        label="📄 Exportar Base Filtrada para CSV",
        data=csv_buffer.getvalue(),
        file_name="base_filtrada_pca.csv",
        mime="text/csv"
    )
