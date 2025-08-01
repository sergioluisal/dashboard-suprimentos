import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
import io

# Configuração da página
st.set_page_config(
    page_title="Acompanhamento de Suprimentos",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Colunas desejadas para exportação
COLUNAS_DESEJADAS = [
    'NumeroPedido',
    'DataPedido',
    'ModeloProduto',
    'TipoProduto',
    'QuantidadeProduto',
    'OrdemServico',
    'NumeroSerie',
    'ApelidoDoEquipamento',
    'StatusAtual',
    'PrevisaoEntrega',
    'Entregue'
]

# Função para carregar dados com tratamento de erros e upload
@st.cache_data
def load_data(uploaded_file):
    if uploaded_file is None:
        return pd.DataFrame()

    try:
        file_extension = uploaded_file.name.split(".")[-1].lower()
        if file_extension == "csv":
            # Tentativa de carregar com diferentes encodings
            encodings = ["utf-8", "latin-1", "iso-8859-1", "cp1252"]
            df = None
            for encoding in encodings:
                try:
                    df = pd.read_csv(uploaded_file, encoding=encoding, sep=";")
                    break
                except:
                    uploaded_file.seek(0) # Reset file pointer for next attempt
                    continue
            if df is None:
                raise Exception("Não foi possível decodificar o arquivo CSV com os encodings tentados.")
        elif file_extension in ["xls", "xlsx"]:
            df = pd.read_excel(uploaded_file)
        else:
            st.error("Formato de arquivo não suportado. Por favor, faça upload de um arquivo CSV ou Excel.")
            return pd.DataFrame()

        # Tratamento de dados
        if "DataPedido" in df.columns:
            df["DataPedido"] = pd.to_datetime(df["DataPedido"], errors="coerce", dayfirst=True)
        if "PrevisaoEntrega" in df.columns:
            df["PrevisaoEntrega"] = pd.to_datetime(df["PrevisaoEntrega"], errors="coerce", dayfirst=True)

        # CORREÇÃO: Tratamento específico para QuantidadeProduto
        if "QuantidadeProduto" in df.columns:
            # Converter para numérico, forçando erros para NaN
            df["QuantidadeProduto"] = pd.to_numeric(df["QuantidadeProduto"], errors="coerce")
            # Preencher NaN com 0
            df["QuantidadeProduto"] = df["QuantidadeProduto"].fillna(0)
        
        # Preencher outros valores nulos com "Não informado"
        df_text_cols = df.select_dtypes(include=['object']).columns
        df[df_text_cols] = df[df_text_cols].fillna("Não informado")

        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()

# Função para calcular percentual com tratamento de divisão por zero
def safe_percentage(numerator, denominator):
    if denominator == 0 or pd.isna(denominator) or pd.isna(numerator):
        return 0
    return (numerator / denominator) * 100

# Função para calcular métricas com tratamento de erros
def calculate_metrics(df):
    if df.empty:
        return {
            "total_pedidos": 0,
            "pedidos_entregues": 0,
            "quantidade_total": 0,
            "pedidos_pendentes": 0,
            "taxa_entrega": 0
        }

    total_pedidos = len(df)

    # Verificar se a coluna "Entregue" existe
    if "Entregue" in df.columns:
        # Converte para datetime e ignora erros
        df["Entregue"] = pd.to_datetime(df["Entregue"], errors="coerce", dayfirst=True)
        pedidos_entregues = df["Entregue"].notna().sum()
    else:
        pedidos_entregues = 0

    # CORREÇÃO: Verificar se a coluna "QuantidadeProduto" existe e calcular corretamente
    if "QuantidadeProduto" in df.columns:
        # Garantir que os valores são numéricos
        quantidade_numerica = pd.to_numeric(df["QuantidadeProduto"], errors="coerce").fillna(0)
        quantidade_total = quantidade_numerica.sum()
    else:
        quantidade_total = 0

    pedidos_pendentes = total_pedidos - pedidos_entregues
    taxa_entrega = safe_percentage(pedidos_entregues, total_pedidos)

    return {
        "total_pedidos": total_pedidos,
        "pedidos_entregues": pedidos_entregues,
        "quantidade_total": int(quantidade_total),
        "pedidos_pendentes": pedidos_pendentes,
        "taxa_entrega": taxa_entrega
    }

# Função para criar gráfico de barras com tratamento de dados vazios
def create_bar_chart(df, x_col, title, color_sequence=None):
    if df.empty or x_col not in df.columns:
        fig = go.Figure()
        fig.add_annotation(
            text="Dados não disponíveis",
            xref="paper", yref="paper",
            x=0.5, y=0.5, xanchor='center', yanchor='middle',
            showarrow=False, font=dict(size=16)
        )
        fig.update_layout(title=title, height=400)
        return fig

    # Contar valores e tratar dados vazios
    counts = df[x_col].value_counts().head(10)

    if counts.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="Nenhum dado encontrado",
            xref="paper", yref="paper",
            x=0.5, y=0.5, xanchor='center', yanchor='middle',
            showarrow=False, font=dict(size=16)
        )
        fig.update_layout(title=title, height=400)
        return fig

    fig = px.bar(
        x=counts.index,
        y=counts.values,
        title=title,
        labels={'x': x_col, 'y': 'Quantidade'},
        color_discrete_sequence=color_sequence or px.colors.qualitative.Set3
    )

    fig.update_layout(
        xaxis_title=x_col,
        yaxis_title="Quantidade",
        height=400,
        showlegend=False
    )

    return fig

# Função para criar gráfico de pizza com tratamento de dados vazios
def create_pie_chart(df, col, title):
    if df.empty or col not in df.columns:
        fig = go.Figure()
        fig.add_annotation(
            text="Dados não disponíveis",
            xref="paper", yref="paper",
            x=0.5, y=0.5, xanchor='center', yanchor='middle',
            showarrow=False, font=dict(size=16)
        )
        fig.update_layout(title=title, height=400)
        return fig

    # Contar valores e tratar dados vazios
    counts = df[col].value_counts()

    if counts.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="Nenhum dado encontrado",
            xref="paper", yref="paper",
            x=0.5, y=0.5, xanchor='center', yanchor='middle',
            showarrow=False, font=dict(size=16)
        )
        fig.update_layout(title=title, height=400)
        return fig

    fig = px.pie(
        values=counts.values,
        names=counts.index,
        title=title,
        color_discrete_sequence=px.colors.qualitative.Set3
    )

    fig.update_layout(height=400)
    return fig

# Função para criar gráfico de linha temporal com tratamento de dados vazios
def create_timeline_chart(df, date_col, title):
    if df.empty or date_col not in df.columns:
        fig = go.Figure()
        fig.add_annotation(
            text="Dados não disponíveis",
            xref="paper", yref="paper",
            x=0.5, y=0.5, xanchor='center', yanchor='middle',
            showarrow=False, font=dict(size=16)
        )
        fig.update_layout(title=title, height=400)
        return fig

    # Filtrar dados válidos
    df_valid = df[df[date_col].notna()].copy()

    if df_valid.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="Nenhuma data válida encontrada",
            xref="paper", yref="paper",
            x=0.5, y=0.5, xanchor='center', yanchor='middle',
            showarrow=False, font=dict(size=16)
        )
        fig.update_layout(title=title, height=400)
        return fig

    # Agrupar por mês
    df_valid["Mes"] = df_valid[date_col].dt.to_period('M')
    monthly_counts = df_valid.groupby("Mes").size().reset_index(name="Quantidade")
    monthly_counts["Mes"] = monthly_counts["Mes"].astype(str)

    if monthly_counts.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="Nenhum dado mensal encontrado",
            xref="paper", yref="paper",
            x=0.5, y=0.5, xanchor='center', yanchor='middle',
            showarrow=False, font=dict(size=16)
        )
        fig.update_layout(title=title, height=400)
        return fig

    fig = px.line(
        monthly_counts,
        x="Mes",
        y="Quantidade",
        title=title,
        markers=True
    )

    fig.update_layout(
        xaxis_title="Mês",
        yaxis_title="Quantidade",
        height=400
    )

    return fig

# Função para criar mapa com tratamento de dados vazios
def create_map(df, location_col, title):
    if df.empty or location_col not in df.columns:
        fig = go.Figure()
        fig.add_annotation(
            text="Dados geográficos não disponíveis",
            xref="paper", yref="paper",
            x=0.5, y=0.5, xanchor='center', yanchor='middle',
            showarrow=False, font=dict(size=16)
        )
        fig.update_layout(title=title, height=500)
        return fig

    # Contar por localização
    location_counts = df[location_col].value_counts().reset_index()
    location_counts.columns = [location_col, "Quantidade"]

    if location_counts.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="Nenhum dado de localização encontrado",
            xref="paper", yref="paper",
            x=0.5, y=0.5, xanchor='center', yanchor='middle',
            showarrow=False, font=dict(size=16)
        )
        fig.update_layout(title=title, height=500)
        return fig

    # Criar mapa coroplético do Brasil
    fig = px.choropleth(
        location_counts,
        locations=location_col,
        color="Quantidade",
        locationmode="geojson-id",
        title=title,
        color_continuous_scale="Blues",
        labels={'Quantidade': 'Número de Pedidos'}
    )

    fig.update_geos(
        projection_type="natural earth",
        showlakes=True,
        lakecolor='rgb(255, 255, 255)'
    )

    fig.update_layout(height=500)
    return fig

# Interface principal
st.markdown("---")

uploaded_file = st.file_uploader("Faça upload do seu arquivo CSV ou Excel", type=["csv", "xls", "xlsx"])

st.markdown("""
    <h1 style='text-align: center; color: white; font-size: 48px;'>📊 Acompanhamento de Suprimentos</h1>
    <hr style='border: 1px solid #444;'>
""", unsafe_allow_html=True)

df = load_data(uploaded_file)

if df.empty:
    st.info("Por favor, faça upload de um arquivo para começar.")
    st.stop()

# CORREÇÃO: Melhorar a sidebar para filtros com tratamento de valores únicos
st.sidebar.header("🔍 Filtros")

# Filtros dinâmicos baseados nas colunas disponíveis
available_columns = df.columns.tolist()

# CORREÇÃO: Filtro por Estado (se disponível) com tratamento de valores únicos
if "EstadoEntrega" in available_columns:
    # Remover valores nulos e "Não informado" da lista de opções, mas manter no dataframe
    estados_unicos = df["EstadoEntrega"].dropna().unique()
    estados_unicos = [estado for estado in estados_unicos if estado != "Não informado"]
    estados = ["Todos"] + sorted(estados_unicos)
    estado_selecionado = st.sidebar.selectbox("Estado:", estados)
    if estado_selecionado != "Todos":
        df = df[df["EstadoEntrega"] == estado_selecionado]

# CORREÇÃO: Filtro por Status (se disponível) com tratamento de valores únicos
if "StatusAtual" in available_columns:
    status_unicos = df["StatusAtual"].dropna().unique()
    status_unicos = [status for status in status_unicos if status != "Não informado"]
    status_options = ["Todos"] + sorted(status_unicos)
    status_selecionado = st.sidebar.selectbox("Status:", status_options)
    if status_selecionado != "Todos":
        df = df[df["StatusAtual"] == status_selecionado]

# CORREÇÃO: Filtro por Tipo de Produto (se disponível) com melhor tratamento
if "TipoProduto" in available_columns:
    # Remover valores nulos e "Não informado" da lista de opções
    tipos_unicos = df["TipoProduto"].dropna().unique()
    tipos_unicos = [tipo for tipo in tipos_unicos if tipo != "Não informado"]
    
    if len(tipos_unicos) > 0:
        tipos = ["Todos"] + sorted(tipos_unicos)
        tipo_selecionado = st.sidebar.selectbox("Tipo de Produto:", tipos)
        if tipo_selecionado != "Todos":
            df = df[df["TipoProduto"] == tipo_selecionado]
    else:
        st.sidebar.info("Nenhum tipo de produto válido encontrado")

# Filtro por Período de Pedido (se disponível)
if "DataPedido" in available_columns:
    # Garante que a coluna está no formato datetime
    df["DataPedido"] = pd.to_datetime(df["DataPedido"], errors='coerce')
    
    # Filtrar apenas datas válidas para definir o intervalo
    datas_validas = df["DataPedido"].dropna()
    
    if len(datas_validas) > 0:
        # Define o intervalo de datas com base nos dados disponíveis
        data_min = datas_validas.min().date()
        data_max = datas_validas.max().date()

        # Widget de seleção de intervalo de datas
        data_inicial, data_final = st.sidebar.date_input(
            "Período de Pedido:",
            value=(data_min, data_max),
            min_value=data_min,
            max_value=data_max
        )

        # Aplica o filtro ao DataFrame
        df = df[(df["DataPedido"].dt.date >= data_inicial) & (df["DataPedido"].dt.date <= data_final)]

# Calcular métricas
metrics = calculate_metrics(df)

# Exibir métricas principais
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total de Pedidos", metrics["total_pedidos"])

with col2:
    st.metric("Pedidos Entregues", metrics["pedidos_entregues"])

with col3:
    # CORREÇÃO: Exibir quantidade total corretamente formatada
    st.metric("Quantidade Total", f"{metrics['quantidade_total']:,}".replace(",", "."))

with col4:
    st.metric("Taxa de Entrega", f"{metrics['taxa_entrega']:.1f}%")

st.markdown("---")

# Gráficos principais
col1, col2 = st.columns(2)

with col1:
    if "EstadoEntrega" in available_columns:  
        fig_estados = create_bar_chart(df, "EstadoEntrega", "Top 10 Pedidos por Estados")
        st.plotly_chart(fig_estados, use_container_width=True)        
    else:
        st.info("Coluna 'EstadoEntrega' não encontrada nos dados")

with col2:
    if "StatusAtual" in available_columns:
        fig_status = create_pie_chart(df, "StatusAtual", "Status")
        st.plotly_chart(fig_status, use_container_width=True)
    else:
        st.info("Coluna 'StatusAtual' não encontrada nos dados")

# Segunda linha de gráficos
col1, col2 = st.columns(2)

with col1:
    if "DataPedido" in available_columns:
        fig_timeline = create_timeline_chart(df, "DataPedido", "Evolução Temporal dos Pedidos")
        st.plotly_chart(fig_timeline, use_container_width=True)
    else:
        st.info("Coluna 'DataPedido' não encontrada nos dados")

with col2:
    if "TipoProduto" in available_columns:
        fig_produtos = create_bar_chart(df, "TipoProduto", "Top 10 Produto por Tipo")
        st.plotly_chart(fig_produtos, use_container_width=True)
    else:
        st.info("Coluna 'TipoProduto' não encontrada nos dados")

# Mapa (se dados geográficos disponíveis)
if "Uf" in available_columns:
    st.markdown("### 🗺️ Distribuição Geográfica")
    fig_map = create_map(df, "Uf", "Distribuição de Pedidos por Estado")
    st.plotly_chart(fig_map, use_container_width=True)

# Terceira linha de gráficos
col1, col2 = st.columns(2)

with col1:
    if "Entregue" in df.columns:
       df["TemData"] = df["Entregue"].notna() & (df["Entregue"] != "")
    else:
       df["TemData"] = False

    if "TemData" in df.columns:
       contagem = df["TemData"].value_counts().rename({True: "Entregues", False: "Não Entregues"}).reset_index()
       contagem.columns = ["Status", "Quantidade"]
    
       fig = px.pie(
        contagem,
        names="Status",
        values="Quantidade",
        title="Pedidos Entregues e Não Entregues",
        hole=0.4  # Se quiser estilo "donut", senão remova
       )
       st.plotly_chart(fig, use_container_width=True)
    else:
       st.info("Coluna 'TemData' não encontrada.")

with col2:
    if "ModeloProduto" in available_columns:
        fig_modelos = create_bar_chart(df, "ModeloProduto", "Top 10 Produtos por Modelo")
        st.plotly_chart(fig_modelos, use_container_width=True)
    else:
        st.info("Coluna 'ModeloProduto' não encontrada nos dados")

# Tabela de dados
#st.markdown("### 📋 Dados Detalhados")
#st.dataframe(df, use_container_width=True)

# Verifica se todas as colunas estão presentes
colunas_faltando = [col for col in COLUNAS_DESEJADAS if col not in df.columns]
if colunas_faltando:
    st.error(f"As seguintes colunas estão ausentes: {colunas_faltando}")
else:
    df_filtrado = df[COLUNAS_DESEJADAS]
    
    st.success("Colunas filtradas com sucesso!")
    st.subheader("✅ Dados filtrados:")
    st.dataframe(df_filtrado, use_container_width=True)

# Download dos dados filtrados
if not df.empty:
    st.markdown("### 📥 Exportar Dados")

    # Filtrar colunas para exportação
    df_export = df.copy()
    cols_to_export = [col for col in COLUNAS_DESEJADAS if col in df_export.columns]
    df_export = df_export[cols_to_export]

    # Botão de download CSV
    csv = df_export.to_csv(index=False, sep=";")
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name=f"acompanhamento_filtrado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )

    # Botão de download Excel
    excel_buffer = io.BytesIO()
    df_export.to_excel(excel_buffer, index=False, engine="openpyxl")
    excel_buffer.seek(0)
    st.download_button(
        label="Download Excel",
        data=excel_buffer,
        file_name=f"acompanhamento_filtrado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# Informações sobre as colunas disponíveis
with st.expander("ℹ️ Informações sobre os dados"):
    st.write("**Colunas disponíveis no dataset:**")
    for col in available_columns:
        st.write(f"- {col}")

    st.write(f"**Total de registros:** {len(df)}")
    
    # CORREÇÃO: Mostrar informações sobre a quantidade
    if "QuantidadeProduto" in available_columns:
        quantidade_info = df["QuantidadeProduto"].describe()
        st.write("**Estatísticas da Quantidade de Produtos:**")
        st.write(quantidade_info)









