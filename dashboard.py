"""
dashboard.py - Dashboard de Obras Celesc (Streamlit + Plotly)

Como rodar (no terminal do VS Code, dentro da pasta do projeto):
    streamlit run dashboard.py
"""
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

import dados

st.set_page_config(page_title="Carteira de Obras - Celesc", layout="wide")


# ---------------------------------------------------------------------------
# Funções auxiliares
# ---------------------------------------------------------------------------
def brl(valor: float) -> str:
    """1234567.8 -> 'R$ 1.234.568'"""
    return "R$ " + f"{valor:,.0f}".replace(",", ".")


PLANILHA_ID = "1SjEP6ks6BC5BtRjiw8n13oHhunHbgCCYdXyS1jWYyBQ"
# GID da aba BASE DE DADOS OBRAS FLN (vem do link da sua planilha).
GID_OBRAS = "1420860611"


@st.cache_data(ttl=30, show_spinner="Atualizando dados da Planilha Google...")
def ler_planilha_google():
    # Usamos o GID da aba de obras para não correr o risco de o Google
    # interpretar errado o nome da aba. A programação continua pelo nome da aba.
    url_obras = (
        f"https://docs.google.com/spreadsheets/d/{PLANILHA_ID}/export?"
        f"format=csv&gid={GID_OBRAS}"
    )
    url_programacao = (
        f"https://docs.google.com/spreadsheets/d/{PLANILHA_ID}/gviz/tq?"
        "tqx=out:csv&sheet=PROGRAMA%C3%87%C3%83O"
    )
    obras = dados.carregar_obras_google(url_obras)
    prog = dados.carregar_programacao_google(url_programacao)
    return obras, prog


try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=30_000, key="dashboard_refresh")
except ImportError:
    pass


def achar_planilha_padrao():
    """Procura na pasta do projeto uma planilha chamada CONTROLE...OBRAS...xlsx"""
    pasta = Path(__file__).parent
    achados = sorted(pasta.glob("CONTROLE*OBRAS*.xlsx"))
    return achados[0] if achados else None


# ---------------------------------------------------------------------------
# Barra lateral
# ---------------------------------------------------------------------------
st.sidebar.header("Planilha Google")
st.sidebar.caption("Fonte: Planilha Google publicada na web")
if st.sidebar.button("🔄 Atualizar agora"):
    st.cache_data.clear()
    st.rerun()
st.sidebar.caption("Atualização automática a cada 30 segundos.")

try:
    obras, prog = ler_planilha_google()
except Exception as e:
    st.error("Não foi possível ler a Planilha Google.")
    st.warning(
        "Confira se a planilha continua publicada na web e se a aba de obras é a mesma do link usado no projeto."
    )
    st.exception(e)
    st.stop()

hoje = pd.Timestamp.today().normalize()

st.title("Dashboard de Obras - Celesc")
st.caption(f"Dados da planilha | Referência: {hoje:%d/%m/%Y}")

aba1, aba2 = st.tabs(["Evolução da carteira", "Programação por equipe"])

# ===========================================================================
# ABA 1 - EVOLUÇÃO DA CARTEIRA
# ===========================================================================
with aba1:
    abertas = obras[~obras["CONCLUIDA"]]
    atrasadas = dados.obras_atrasadas(obras, hoje)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Obras na carteira (total)", len(obras))
    c2.metric("Em aberto", len(abertas), help="Status diferente de CONCLUIDA, MEDIÇÃO e FATURADA")
    c3.metric("Valor orçado em aberto", brl(abertas["VALOR ORÇADO"].sum()))
    c4.metric("Total faturado", brl(obras["VALOR FATURADO"].sum()))
    c5.metric("Fora do prazo", len(atrasadas), help="Em aberto e com DATA LIMITE já vencida")

    st.divider()

    # --- evolução mensal -----------------------------------------------------
    st.subheader("Evolução mensal: obras recebidas x concluídas")
    metrica = st.radio(
        "Medir por", ["Quantidade de obras", "Valor orçado (R$)"], horizontal=True, key="metrica_carteira"
    )
    ev = dados.evolucao_mensal(obras, hoje)

    if metrica == "Quantidade de obras":
        col_ent, col_con, col_aberto, rotulo = "entradas", "concluidas", "em_aberto", "Obras"
    else:
        col_ent, col_con, col_aberto, rotulo = "valor_entradas", "valor_concluidas", "valor_em_aberto", "R$"

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_bar(x=ev["mes"], y=ev[col_ent], name="Recebidas", secondary_y=False)
    fig.add_bar(x=ev["mes"], y=ev[col_con], name="Concluídas", secondary_y=False)
    fig.add_scatter(
        x=ev["mes"], y=ev[col_aberto], name="Carteira em aberto (acumulado)",
        mode="lines+markers", secondary_y=True,
    )
    fig.update_layout(barmode="group", height=420, legend=dict(orientation="h", y=1.12))
    fig.update_xaxes(tickformat="%m/%Y", dtick="M1")
    fig.update_yaxes(title_text=f"Por mês ({rotulo})", secondary_y=False)
    fig.update_yaxes(title_text=f"Em aberto ({rotulo})", secondary_y=True)
    st.plotly_chart(fig)
    st.caption(
        "Recebida = mês da DATA RECEBIMENTO. Concluída = mês da PROGRAMAÇÃO FINAL das obras "
        "com status CONCLUIDA, MEDIÇÃO ou FATURADA."
    )

    # --- status atual e ciclos ----------------------------------------------
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Obras por status hoje")
        rs = dados.resumo_status(obras)
        figs = px.bar(
            rs, x="obras", y="STATUS", orientation="h", text="obras",
            hover_data={"valor_orcado": ":,.0f"},
        )
        figs.update_yaxes(autorange="reversed", title=None)
        figs.update_xaxes(title="Obras")
        figs.update_layout(height=380)
        st.plotly_chart(figs)

    with col_b:
        st.subheader("Orçado x faturado por ciclo de medição")
        rc = dados.resumo_ciclo(obras)
        longo = rc.melt(
            id_vars="ciclo", value_vars=["valor_orcado", "valor_faturado"],
            var_name="tipo", value_name="valor",
        )
        longo["tipo"] = longo["tipo"].map({"valor_orcado": "Orçado", "valor_faturado": "Faturado"})
        figc = px.bar(longo, x="ciclo", y="valor", color="tipo", barmode="group")
        figc.update_xaxes(title="Ciclo (mês/ano)", type="category")
        figc.update_yaxes(title="R$")
        figc.update_layout(height=380, legend_title_text="")
        st.plotly_chart(figc)

    # --- obras fora do prazo -------------------------------------------------
    st.subheader("Obras em aberto com prazo vencido")
    if atrasadas.empty:
        st.success("Nenhuma obra em aberto com a data limite vencida.")
    else:
        t = atrasadas.copy()
        t["DATA LIMITE"] = t["DATA LIMITE"].dt.strftime("%d/%m/%Y")
        t["VALOR ORÇADO"] = t["VALOR ORÇADO"].map(brl)
        st.dataframe(t, hide_index=True)

# ===========================================================================
# ABA 2 - PROGRAMAÇÃO POR EQUIPE
# ===========================================================================
with aba2:
    dias_all = dados.dias_execucao(prog)

    f1, f2, f3 = st.columns([1, 1, 2])
    equipes_all = sorted(dias_all["EQUIPE"].unique())
    equipes = f1.multiselect("Equipes", equipes_all, default=equipes_all)

    dmin, dmax = dias_all["DATA"].min().date(), dias_all["DATA"].max().date()
    periodo = f2.date_input("Período", value=(dmin, dmax), min_value=dmin, max_value=dmax, format="DD/MM/YYYY")

    obras_all = sorted(dias_all["OBRA"].unique())
    obras_sel = f3.multiselect("Obras (vazio = todas)", obras_all)

    if not (isinstance(periodo, (tuple, list)) and len(periodo) == 2):
        st.info("Selecione a data inicial e a data final do período.")
        st.stop()

    d = dias_all[
        dias_all["EQUIPE"].isin(equipes)
        & (dias_all["DATA"].dt.date >= periodo[0])
        & (dias_all["DATA"].dt.date <= periodo[1])
    ]
    if obras_sel:
        d = d[d["OBRA"].isin(obras_sel)]

    if d.empty:
        st.warning("Nenhuma execução programada com esses filtros.")
        st.stop()

    k1, k2, k3 = st.columns(3)
    k1.metric("Obras programadas", d["OBRA"].nunique())
    k2.metric("Dias de execução (obra x equipe)", len(d))
    k3.metric("Equipes", d["EQUIPE"].nunique())

    cores = dict(zip(equipes_all, px.colors.qualitative.Set2 + px.colors.qualitative.Set1))

    # --- Gantt ---------------------------------------------------------------
    st.subheader("Cronograma de execução")
    modo = st.radio(
        "Visualização",
        ["Uma linha por obra (cor = equipe)", "Uma linha por equipe (cor = obra)"],
        horizontal=True,
    )

    if modo.startswith("Uma linha por obra"):
        ordem = d.groupby("OBRA")["DATA"].min().sort_values().index.tolist()
        fig = px.timeline(
            d, x_start="DATA", x_end="FIM", y="OBRA", color="EQUIPE",
            color_discrete_map=cores, category_orders={"OBRA": ordem},
            hover_data={"ATIVIDADE": True, "PERIODOS": True, "FIM": False},
        )
        fig.update_layout(height=max(420, 22 * len(ordem) + 150))
    else:
        fig = px.timeline(
            d, x_start="DATA", x_end="FIM", y="EQUIPE", color="OBRA",
            category_orders={"EQUIPE": equipes_all},
            hover_data={"ATIVIDADE": True, "PERIODOS": True, "FIM": False},
        )
        fig.update_layout(height=420, showlegend=False)

    fig.update_yaxes(autorange="reversed", title=None)
    fig.update_xaxes(title=None)
    st.plotly_chart(fig)
    st.caption("Cada barra é um dia com a equipe programada na obra. Passe o mouse para ver a atividade.")

    # --- dias por obra e ocupação semanal -------------------------------------
    resumo = dados.resumo_obra_equipe(d)
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Dias de execução por obra")
        total_obra = resumo.groupby("OBRA")["dias"].sum().sort_values(ascending=False)
        top = total_obra.head(20).index
        figb = px.bar(
            resumo[resumo["OBRA"].isin(top)], x="dias", y="OBRA", color="EQUIPE",
            orientation="h", color_discrete_map=cores,
            category_orders={"OBRA": list(top)},
        )
        figb.update_yaxes(autorange="reversed", title=None)
        figb.update_xaxes(title="Dias")
        figb.update_layout(height=520)
        st.plotly_chart(figb)
        if len(total_obra) > 20:
            st.caption(f"Mostrando as 20 obras com mais dias (de {len(total_obra)}).")

    with col_b:
        st.subheader("Ocupação semanal por equipe")
        occ = dados.ocupacao_semanal(d)
        figh = px.imshow(
            occ, text_auto=True, aspect="auto", color_continuous_scale="Blues",
            labels=dict(x="Semana (início)", y="Equipe", color="Dias"),
        )
        figh.update_layout(height=520)
        st.plotly_chart(figh)
        st.caption("Número de dias na semana em que a equipe tinha obra programada.")

    # --- tabela --------------------------------------------------------------
    st.subheader("Resumo por obra e equipe")
    tab = resumo.copy()
    tab["inicio"] = tab["inicio"].dt.strftime("%d/%m/%Y")
    tab["fim"] = tab["fim"].dt.strftime("%d/%m/%Y")
    tab.columns = ["Obra", "Equipe", "Dias de execução", "Primeiro dia", "Último dia"]
    st.dataframe(tab, hide_index=True)
