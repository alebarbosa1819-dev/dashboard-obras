"""
dashboard.py - Dashboard de Obras Celesc (Streamlit + Plotly)

Como rodar (no terminal do VS Code, dentro da pasta do projeto):
    streamlit run dashboard.py
"""
from datetime import datetime
from html import escape
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st
from plotly.subplots import make_subplots

import dados

st.set_page_config(
    page_title="Carteira de Obras - Celesc",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# PALETA (um lugar só: mude aqui e o dashboard inteiro acompanha)
# ---------------------------------------------------------------------------
COR_FUNDO = "#0a1426"
COR_CARTAO = "#0f1d33"
COR_BORDA = "#233a5a"
COR_TEXTO = "#e8eff9"
COR_TEXTO_SUAVE = "#b6c7dd"
COR_TEXTO_FRACO = "#8ea4c2"
COR_GRADE = "rgba(148, 170, 200, 0.13)"

AZUL = "#3ea6ff"
AZUL_CLARO = "#8fd0ff"
VERDE = "#34d399"
AMBAR = "#fbbf24"
LARANJA = "#fb923c"
VERMELHO = "#f87171"
ROXO = "#a78bfa"
CINZA = "#8da2bd"

# cores para equipes / obras (legíveis sobre fundo escuro)
PALETA = [
    "#3ea6ff", "#34d399", "#fbbf24", "#f472b6", "#a78bfa", "#fb923c",
    "#22d3ee", "#a3e635", "#f87171", "#60a5fa", "#2dd4bf", "#e879f9",
]

# cor de cada status no gráfico "Obras por status hoje"
COR_STATUS = {
    "CADASTRO": CINZA,
    "VIABILIZAÇÃO": AMBAR,
    "PROGRAMADA": AZUL,
    "PROG/PENDENCIA": LARANJA,
    "REPROGRAMAR": VERMELHO,
    "CONCLUIDA": "#2dd4bf",
    "MEDIÇÃO": ROXO,
    "FATURADA": VERDE,
}

FONTE = "Inter, 'Segoe UI', Arial, sans-serif"

# ---------------------------------------------------------------------------
# TEMA ÚNICO DOS GRÁFICOS (vale para todos, os atuais e os futuros)
# ---------------------------------------------------------------------------
_eixo = dict(
    gridcolor=COR_GRADE,
    linecolor=COR_BORDA,
    zeroline=False,
    color=COR_TEXTO_SUAVE,
    tickfont=dict(color=COR_TEXTO_SUAVE, size=12),
    title=dict(font=dict(color=COR_TEXTO_SUAVE, size=12)),
)

pio.templates["celesc_escuro"] = go.layout.Template(
    layout=dict(
        # fundos opacos: o gráfico fica escuro mesmo se o Streamlit (ex.: na nuvem) abrir no tema claro
        paper_bgcolor=COR_CARTAO,
        plot_bgcolor="#101e36",
        font=dict(family=FONTE, size=13, color=COR_TEXTO),
        colorway=PALETA,
        separators=",.",  # 1.234,56 no padrão brasileiro
        xaxis=dict(_eixo, showgrid=False),  # menos linhas de grade: só as horizontais
        yaxis=dict(_eixo, showgrid=True),
        legend=dict(
            font=dict(color=COR_TEXTO, size=12),
            bgcolor="rgba(0,0,0,0)",
            title=dict(font=dict(color=COR_TEXTO_SUAVE)),
        ),
        hoverlabel=dict(
            bgcolor="#162a47",
            bordercolor=COR_BORDA,
            font=dict(color="#ffffff", size=13),
        ),
        margin=dict(l=10, r=10, t=30, b=10),
    )
)
pio.templates.default = "celesc_escuro"


# Os dois gráficos da linha inferior usam a mesma altura (painéis alinhados)
ALTURA_INFERIOR = 460


def mostrar(fig):
    """Exibe os gráficos com largura responsiva."""
    st.plotly_chart(
        fig,
        theme=None,
        width="stretch",
        config={
            "responsive": True,
            "displaylogo": False,
        },
    )


# ---------------------------------------------------------------------------
# ÍCONES (SVG embutido: não depende da versão do Streamlit)
# ---------------------------------------------------------------------------
_ICONES = {
    "raio": '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
    "filtro": '<polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/>',
    "dados": '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14a9 3 0 0 0 18 0V5"/><path d="M3 12a9 3 0 0 0 18 0"/>',
    "alerta": '<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
    "relogio": '<circle cx="12" cy="12" r="9"/><polyline points="12 7 12 12 15 14"/>',
}


def icone(nome: str, tamanho: int = 16) -> str:
    return (
        f'<svg class="ico" width="{tamanho}" height="{tamanho}" viewBox="0 0 24 24" fill="none" '
        f'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        f'{_ICONES[nome]}</svg>'
    )


# ---------------------------------------------------------------------------
# IDENTIDADE VISUAL
# ---------------------------------------------------------------------------
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

/* Base */
html, body, .stApp, [data-testid="stSidebar"], button, input, textarea {{ font-family: {FONTE}; }}
.stApp {{ background: {COR_FUNDO}; color: {COR_TEXTO}; }}
[data-testid="stHeader"] {{ background: {COR_FUNDO}; }}
[data-testid="stToolbar"] * {{ color: {COR_TEXTO_SUAVE} !important; }}
footer {{ visibility: hidden; }}
.block-container {{ padding-top: 2.2rem; padding-bottom: 2.5rem; max-width: 1680px; }}

/* Textos (escala única) */
h1, h2, h3 {{ color: #f3f7ff !important; font-weight: 650 !important; letter-spacing: -0.01em; }}
h3 {{ font-size: 1.08rem !important; margin-bottom: .2rem !important; }}
p, label {{ color: {COR_TEXTO_SUAVE}; }}
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * {{
    color: {COR_TEXTO_FRACO} !important; font-size: .8rem !important;
}}

/* Topo da página */
.topo {{ display:flex; justify-content:space-between; align-items:flex-end; gap:16px;
         flex-wrap:wrap; margin-bottom: 1.1rem; }}
.topo-t {{ font-size: 1.85rem; font-weight: 700; color:#f3f7ff; letter-spacing:-0.02em; line-height:1.15; }}
.topo-s {{ font-size: .92rem; color:{COR_TEXTO_FRACO}; margin-top:4px; }}
.pill {{ display:inline-flex; align-items:center; gap:8px; background:{COR_CARTAO};
         border:1px solid {COR_BORDA}; color:{COR_TEXTO_SUAVE}; border-radius:999px;
         padding:7px 14px; font-size:.82rem; }}
.pill .ico {{ color:{AZUL}; }}
.ico {{ vertical-align:-3px; flex-shrink:0; }}

/* Cartões de indicadores */
.kpi-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:14px; margin:4px 0 14px; }}
.kpi {{ background:linear-gradient(150deg,#15294a,{COR_CARTAO}); border:1px solid {COR_BORDA};
        border-top:3px solid var(--acc); border-radius:14px; padding:16px 18px 14px; }}
.kpi-l {{ font-size:.82rem; font-weight:500; color:#9fb4d0; }}
.kpi-v {{ font-size:clamp(1.65rem,2.3vw,2.25rem); font-weight:700; color:#ffffff; line-height:1.12;
          margin:6px 0 4px; font-variant-numeric:tabular-nums; white-space:nowrap; }}
.kpi-s {{ font-size:.78rem; color:{COR_TEXTO_FRACO}; }}

/* Alertas */
.sec-t {{ font-size:.82rem; font-weight:600; color:{COR_TEXTO_FRACO}; margin:6px 0 8px; }}
.alerta-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(250px,1fr)); gap:14px; margin-bottom:16px; }}
.alerta {{ display:flex; gap:14px; align-items:center; background:{COR_CARTAO}; border:1px solid {COR_BORDA};
           border-left:4px solid var(--acc); border-radius:12px; padding:13px 16px; }}
.alerta-n {{ font-size:1.7rem; font-weight:700; color:var(--acc); min-width:2.2ch; font-variant-numeric:tabular-nums; }}
.alerta-t {{ font-size:.9rem; font-weight:600; color:{COR_TEXTO}; }}
.alerta-d {{ font-size:.76rem; color:{COR_TEXTO_FRACO}; margin-top:2px; }}

/* Cartões que envolvem cada gráfico */
[data-testid="stVerticalBlockBorderWrapper"] {{
    background:{COR_CARTAO}; border:1px solid {COR_BORDA} !important; border-radius:14px; padding:8px 12px;
}}

/* Abas */
button[data-baseweb="tab"] {{ color:{COR_TEXTO_SUAVE}; font-weight:600; }}
button[data-baseweb="tab"][aria-selected="true"] {{ color:{AZUL} !important; }}
[data-baseweb="tab-highlight"] {{ background-color:{AZUL} !important; }}
[data-baseweb="tab-border"] {{ background-color:#233a5a !important; }}

/* Barra lateral */
[data-testid="stSidebar"] {{
    background:linear-gradient(180deg,#0f2040 0%,#09132a 100%); border-right:1px solid #1f3454;
}}
[data-testid="stSidebar"] * {{ color:{COR_TEXTO}; }}
.marca {{ display:flex; align-items:center; gap:12px; padding:4px 0 14px; border-bottom:1px solid #1f3454; margin-bottom:14px; }}
.marca-i {{ width:38px; height:38px; border-radius:10px; background:linear-gradient(145deg,#1d6fbf,#3ea6ff);
            display:flex; align-items:center; justify-content:center; color:#fff; }}
.marca-t {{ font-size:1.02rem; font-weight:700; line-height:1.15; }}
.marca-s {{ font-size:.76rem; color:{COR_TEXTO_FRACO} !important; }}
.side-t {{ display:flex; align-items:center; gap:8px; font-size:.82rem; font-weight:600;
           color:{COR_TEXTO_SUAVE} !important; margin:18px 0 8px; }}
.side-t .ico {{ color:{AZUL}; }}
.side-i {{ font-size:.8rem; color:{COR_TEXTO_FRACO} !important; line-height:1.55; }}
.side-i b {{ color:{COR_TEXTO_SUAVE}; font-weight:600; }}

/* Botões */
.stButton > button {{
    width:100%; background:#1479c9; color:#fff; border:1px solid #3299e8; border-radius:9px;
    font-weight:600; transition:.2s ease;
}}
.stButton > button:hover {{ background:#2095e8; border-color:#72caff; color:#fff; }}

/* Divisórias, alertas nativos e tabelas */
hr {{ border-color:#233a5a; }}
[data-testid="stAlert"] {{ border-radius:10px; }}
[data-testid="stDataFrame"] {{ border:1px solid {COR_BORDA}; border-radius:10px; overflow:hidden; }}

/* Agenda semanal */
.agenda-wrap {{ overflow-x:auto; border:1px solid {COR_BORDA}; border-radius:10px; }}
.agenda {{ width:100%; border-collapse:collapse; table-layout:fixed; }}
.agenda th {{ background:#13243f; color:{COR_TEXTO_SUAVE}; padding:10px 12px; text-align:left;
              font-size:.82rem; font-weight:600; border-bottom:1px solid {COR_BORDA}; }}
.agenda th span {{ color:{COR_TEXTO_FRACO}; font-weight:500; margin-left:4px; }}
.agenda th.hoje {{ color:{AZUL}; box-shadow:inset 0 -3px 0 {AZUL}; }}
.agenda th.eq, .agenda td.eq {{ width:130px; position:sticky; left:0; z-index:2; }}
.agenda th.eq {{ background:#13243f; }}
.agenda td.eq {{ background:{COR_CARTAO}; border-right:1px solid {COR_BORDA}; }}
.agenda .semana {{ border-left:2px solid #2d4a73 !important; }}
.agenda td {{ vertical-align:top; padding:8px; border-bottom:1px solid #1a2e4d; border-left:1px solid #1a2e4d; }}
.agenda tr:last-child td {{ border-bottom:none; }}
.agenda td.eq {{ border-left:none; font-weight:700; color:{COR_TEXTO}; font-size:.88rem; }}
.agenda .dot {{ display:inline-block; width:10px; height:10px; border-radius:3px; margin-right:8px; }}
.chip {{ background:#13264a; border-left:4px solid var(--c); border-radius:6px; padding:6px 9px; margin-bottom:6px; }}
.chip-o {{ color:{COR_TEXTO}; font-weight:600; font-size:.8rem; line-height:1.25; }}
.chip-a {{ color:{COR_TEXTO_FRACO}; font-size:.72rem; margin-top:2px; }}
.vazio {{ color:#3d5578; }}

/* Telas estreitas */
@media (max-width: 900px) {{
    .block-container {{ padding-left:1rem; padding-right:1rem; }}
    .topo-t {{ font-size:1.5rem; }}
}}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Funções auxiliares
# ---------------------------------------------------------------------------
def brl(valor: float) -> str:
    """1234567.8 -> 'R$ 1.234.568'"""
    return "R$ " + f"{valor:,.0f}".replace(",", ".")


def inteiro(n) -> str:
    return f"{int(n):,}".replace(",", ".")


def agora() -> datetime:
    """Hora de Brasília (mesmo se o servidor estiver em outro fuso)."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/Sao_Paulo"))
    except Exception:
        return datetime.now()


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
    return obras, prog, agora()


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


def achar_coluna(df: pd.DataFrame, palavras):
    for c in df.columns:
        if any(p in str(c).upper() for p in palavras):
            return c
    return None


# ---- regras dos alertas -----------------------------------------------------
def sem_movimentacao(df: pd.DataFrame, hoje: pd.Timestamp, dias: int) -> pd.DataFrame:
    """Obras em aberto cuja última data registrada (recebimento, 1ª programação
    ou programação final) é mais antiga que `dias`. Data futura = não está parada."""
    a = df[~df["CONCLUIDA"]].copy()
    ref = a[["DATA RECEBIMENTO", "1º PROGRAMAÇÃO", "PROGRAMAÇÃO FINAL"]].max(axis=1)
    a["ÚLTIMA DATA"] = ref
    a["DIAS PARADA"] = (hoje - ref).dt.days
    a = a[a["DIAS PARADA"] > dias].copy()
    a["DIAS PARADA"] = a["DIAS PARADA"].astype("int64")
    cols = ["N. OBRA", "DESCRIÇÃO PROJETO", "FISCAL CELESC", "STATUS", "ÚLTIMA DATA", "DIAS PARADA"]
    cols = [c for c in cols if c in a.columns]
    return a[cols].sort_values("DIAS PARADA", ascending=False).reset_index(drop=True)


def acima_orcamento(df: pd.DataFrame) -> pd.DataFrame:
    x = df[(df["VALOR ORÇADO"] > 0) & (df["VALOR FATURADO"] > df["VALOR ORÇADO"] + 1)].copy()
    x["EXCEDENTE"] = x["VALOR FATURADO"] - x["VALOR ORÇADO"]
    cols = ["N. OBRA", "DESCRIÇÃO PROJETO", "FISCAL CELESC", "STATUS", "VALOR ORÇADO", "VALOR FATURADO", "EXCEDENTE"]
    cols = [c for c in cols if c in x.columns]
    return x[cols].sort_values("EXCEDENTE", ascending=False).reset_index(drop=True)


def datas_futuras(df: pd.DataFrame, hoje: pd.Timestamp) -> pd.DataFrame:
    x = df[df["DATA RECEBIMENTO"] > hoje].copy()
    cols = ["N. OBRA", "DESCRIÇÃO PROJETO", "STATUS", "DATA RECEBIMENTO"]
    cols = [c for c in cols if c in x.columns]
    return x[cols].reset_index(drop=True)


def tabela(df: pd.DataFrame, vazio: str):
    """Tabela com datas e valores já no formato brasileiro."""
    if df.empty:
        st.success(vazio)
        return
    t = df.copy()
    for c in t.columns:
        if pd.api.types.is_datetime64_any_dtype(t[c]):
            t[c] = t[c].dt.strftime("%d/%m/%Y")
    for c in ("VALOR ORÇADO", "VALOR FATURADO", "EXCEDENTE"):
        if c in t.columns:
            t[c] = t[c].map(brl)
    st.dataframe(t, hide_index=True)


def kpi(rotulo, valor, sub, cor) -> str:
    return (
        f'<div class="kpi" style="--acc:{cor}"><div class="kpi-l">{rotulo}</div>'
        f'<div class="kpi-v">{valor}</div><div class="kpi-s">{sub}</div></div>'
    )


def alerta(titulo, n, dica, cor) -> str:
    if n == 0:
        cor, dica = VERDE, "Nenhuma ocorrência"
    return (
        f'<div class="alerta" style="--acc:{cor}"><div class="alerta-n">{inteiro(n)}</div>'
        f'<div><div class="alerta-t">{titulo}</div><div class="alerta-d">{dica}</div></div></div>'
    )


# ---------------------------------------------------------------------------
# Barra lateral - identificação e atualização
# ---------------------------------------------------------------------------
st.sidebar.markdown(
    f'<div class="marca"><div class="marca-i">{icone("raio", 20)}</div>'
    '<div><div class="marca-t">Gestão de Obras</div><div class="marca-s">Carteira Celesc</div></div></div>',
    unsafe_allow_html=True,
)

if st.sidebar.button("Atualizar dados"):
    st.cache_data.clear()
    st.session_state["_pedido_atualizacao"] = True
    st.rerun()

try:
    obras, prog, atualizado_em = ler_planilha_google()
except Exception as e:
    st.session_state.pop("_pedido_atualizacao", None)
    st.error("Não foi possível ler a Planilha Google.")
    st.warning(
        "Confira se a planilha continua publicada na web e se a aba de obras é a mesma do link usado no projeto."
    )
    st.exception(e)
    st.stop()

if st.session_state.pop("_pedido_atualizacao", False):
    st.toast(f"Dados atualizados às {atualizado_em:%H:%M:%S}", icon="✅")

hoje = pd.Timestamp(agora().date())

# ---------------------------------------------------------------------------
# Barra lateral - filtros globais (valem para a aba "Evolução da carteira")
# ---------------------------------------------------------------------------
COL_REGIONAL = achar_coluna(obras, ("REGIONAL", "REGIÃO", "REGIAO"))

_rec = obras["DATA RECEBIMENTO"].dropna()
dmin = _rec.min().date() if not _rec.empty else hoje.date()
dmax = _rec.max().date() if not _rec.empty else hoje.date()


def limpar_filtros():
    for k in ("flt_resp", "flt_status", "flt_regional"):
        st.session_state[k] = []
    st.session_state["flt_periodo"] = (dmin, dmax)


st.sidebar.markdown(f'<div class="side-t">{icone("filtro")}Filtros</div>', unsafe_allow_html=True)

periodo_sel = st.sidebar.date_input(
    "Período de recebimento", value=(dmin, dmax), format="DD/MM/YYYY", key="flt_periodo"
)

if "FISCAL CELESC" in obras.columns:
    resp_serie = obras["FISCAL CELESC"].fillna("Não informado").astype(str).str.strip()
else:
    resp_serie = pd.Series("Não informado", index=obras.index)
resp_sel = st.sidebar.multiselect(
    "Responsável (fiscal)", sorted(resp_serie.unique()), key="flt_resp", placeholder="Todos"
)

_ordem = {s: i for i, s in enumerate(dados.ORDEM_STATUS)}
status_opcoes = sorted(obras["STATUS"].unique(), key=lambda s: (_ordem.get(s, 99), s))
status_sel = st.sidebar.multiselect("Status da obra", status_opcoes, key="flt_status", placeholder="Todos")

regional_sel = []
if COL_REGIONAL:
    reg_serie = obras[COL_REGIONAL].fillna("Não informado").astype(str).str.strip()
    regional_sel = st.sidebar.multiselect(
        "Regional", sorted(reg_serie.unique()), key="flt_regional", placeholder="Todas"
    )

st.sidebar.button("Limpar filtros", on_click=limpar_filtros, key="btn_limpar")

st.sidebar.markdown(f'<div class="side-t">{icone("alerta")}Alertas</div>', unsafe_allow_html=True)
dias_parada = st.sidebar.slider(
    "Dias sem movimentação para alertar", min_value=7, max_value=120, value=30, step=1, key="flt_dias"
)

# ---- aplica os filtros -------------------------------------------------------
mascara = pd.Series(True, index=obras.index)
filtros_ativos = 0

if isinstance(periodo_sel, (tuple, list)) and len(periodo_sel) == 2:
    ini, fim = pd.Timestamp(periodo_sel[0]), pd.Timestamp(periodo_sel[1]) + pd.Timedelta(days=1)
    rec = obras["DATA RECEBIMENTO"]
    mascara &= rec.isna() | ((rec >= ini) & (rec < fim))
    if (periodo_sel[0], periodo_sel[1]) != (dmin, dmax):
        filtros_ativos += 1
if resp_sel:
    mascara &= resp_serie.isin(resp_sel)
    filtros_ativos += 1
if status_sel:
    mascara &= obras["STATUS"].isin(status_sel)
    filtros_ativos += 1
if regional_sel:
    mascara &= reg_serie.isin(regional_sel)
    filtros_ativos += 1

obras_f = obras[mascara].copy()

# ---------------------------------------------------------------------------
# Cabeçalho
# ---------------------------------------------------------------------------
st.markdown(
    '<div class="topo"><div><div class="topo-t">Dashboard de Obras - Celesc</div>'
    '<div class="topo-s">Acompanhamento gerencial da carteira e da programação das equipes</div></div>'
    f'<div class="pill">{icone("relogio")}Referência {hoje:%d/%m/%Y} &nbsp;·&nbsp; atualizado às {atualizado_em:%H:%M}</div></div>',
    unsafe_allow_html=True,
)

aba1, aba2 = st.tabs(["Evolução da carteira", "Programação por equipe"])


# ===========================================================================
# ABA 1 - EVOLUÇÃO DA CARTEIRA
# ===========================================================================
def aba_carteira(f: pd.DataFrame):
    if f.empty:
        st.warning("Nenhuma obra encontrada com os filtros selecionados. Use “Limpar filtros” na barra lateral.")
        return

    abertas = f[~f["CONCLUIDA"]]
    concluidas = f[f["CONCLUIDA"]]
    atrasadas = dados.obras_atrasadas(f, hoje)
    parados = sem_movimentacao(f, hoje, dias_parada)
    acima = acima_orcamento(f)
    futuras = datas_futuras(f, hoje)

    orc_total = float(f["VALOR ORÇADO"].sum())
    fat_total = float(f["VALOR FATURADO"].sum())
    pct_fat = fat_total / orc_total * 100 if orc_total > 0 else 0.0
    n = len(f)

    # --- indicadores -----------------------------------------------------------
    st.markdown(
        '<div class="kpi-grid">'
        + kpi("Total de obras", inteiro(n),
              "com filtros aplicados" if filtros_ativos else "carteira completa", AZUL)
        + kpi("Em andamento", inteiro(len(abertas)),
              f"{brl(abertas['VALOR ORÇADO'].sum())} orçados em aberto", AMBAR)
        + kpi("Concluídas", inteiro(len(concluidas)),
              f"{len(concluidas) / n * 100:.0f}% do total", VERDE)
        + kpi("Atrasadas", inteiro(len(atrasadas)),
              "em aberto com data limite vencida", VERMELHO)
        + kpi("Valor total orçado", brl(orc_total), "soma das obras filtradas", AZUL_CLARO)
        + kpi("Total faturado", brl(fat_total), f"{pct_fat:.1f}% do valor orçado", VERDE)
        + '</div>',
        unsafe_allow_html=True,
    )

    # --- alertas ---------------------------------------------------------------
    st.markdown(
        '<div class="sec-t">Pontos de atenção</div><div class="alerta-grid">'
        + alerta("Prazo vencido", len(atrasadas), "obras em aberto após a data limite", VERMELHO)
        + alerta("Sem movimentação", len(parados), f"em aberto há mais de {dias_parada} dias sem data nova", AMBAR)
        + alerta("Acima do orçamento", len(acima), "faturado maior que o orçado", LARANJA)
        + alerta("Datas a conferir", len(futuras), "recebimento lançado com data futura", ROXO)
        + '</div>',
        unsafe_allow_html=True,
    )

    # --- evolução mensal -----------------------------------------------------
    with st.container(border=True):
        st.subheader("Evolução mensal: obras recebidas x concluídas")
        metrica = st.radio(
            "Medir por", ["Quantidade de obras", "Valor orçado (R$)"], horizontal=True, key="metrica_carteira"
        )
        try:
            ev = dados.evolucao_mensal(f, hoje)
        except Exception:
            ev = None

        if ev is None or ev.empty:
            st.info("Sem datas suficientes para montar a evolução mensal com os filtros atuais.")
        else:
            if metrica == "Quantidade de obras":
                col_ent, col_con, col_aberto, rotulo = "entradas", "concluidas", "em_aberto", "Obras"
            else:
                col_ent, col_con, col_aberto, rotulo = "valor_entradas", "valor_concluidas", "valor_em_aberto", "R$"

            # meses muito à frente (ex.: data digitada errada) não esticam o gráfico
            limite = (hoje + pd.DateOffset(months=2)).to_period("M").to_timestamp()
            fora = int((f["DATA RECEBIMENTO"] > limite + pd.offsets.MonthEnd(0)).sum())
            ev_p = ev[ev["mes"] <= limite]

            # os dois eixos Y usam a mesma escala: grade alinhada e leitura direta
            # folga de 25% acima do maior valor: a linha amarela e os rótulos nunca encostam no topo
            topo = float(ev_p[[col_ent, col_con, col_aberto]].max().max()) * 1.25 or 1.0
            base = min(0.0, float(ev_p[col_aberto].min()) * 1.1)

            def rotulos(serie):
                if metrica != "Quantidade de obras":
                    return None
                return [f"{v:.0f}" if v > 0 else "" for v in serie]

            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_bar(
                x=ev_p["mes"], y=ev_p[col_ent], name="Recebidas", marker_color=AZUL, secondary_y=False,
                text=rotulos(ev_p[col_ent]), textposition="outside", cliponaxis=False,
                textfont=dict(size=10, color=COR_TEXTO_SUAVE),
            )
            fig.add_bar(
                x=ev_p["mes"], y=ev_p[col_con], name="Concluídas", marker_color=VERDE, secondary_y=False,
                text=rotulos(ev_p[col_con]), textposition="outside", cliponaxis=False,
                textfont=dict(size=10, color=COR_TEXTO_SUAVE),
            )
            fig.add_scatter(
                x=ev_p["mes"], y=ev_p[col_aberto], name="Carteira em aberto (acumulado)",
                mode="lines+markers", secondary_y=True,
                line=dict(color=AMBAR, width=3), marker=dict(size=7, color=AMBAR),
                cliponaxis=False,
            )
            fig.update_layout(
                barmode="group", bargap=0.28, height=480,
                margin=dict(l=70, r=70, t=80, b=70),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
                hovermode="x unified",
            )
            fig.update_xaxes(
                tickformat="%m/%Y", dtick="M1", tickangle=-45, automargin=True,
                range=[ev_p["mes"].min() - pd.Timedelta(days=16), ev_p["mes"].max() + pd.Timedelta(days=16)],
            )
            fig.update_yaxes(
                title_text=f"Por mês ({rotulo})", range=[base, topo], automargin=True,
                tickformat=",.0f", hoverformat=",.0f", secondary_y=False,
            )
            fig.update_yaxes(
                title_text=f"Em aberto ({rotulo})", range=[base, topo], automargin=True,
                tickformat=",.0f", hoverformat=",.0f", showgrid=False, secondary_y=True,
            )
            mostrar(fig)
            nota = (
                "Recebida = mês da DATA RECEBIMENTO. Concluída = mês da PROGRAMAÇÃO FINAL das obras "
                "com status CONCLUIDA, MEDIÇÃO ou FATURADA. A linha mostra a carteira em aberto acumulada."
            )
            if fora:
                nota += f" {fora} obra(s) com data de recebimento muito à frente ficaram fora do gráfico (veja “Datas a conferir”)."
            st.caption(nota)

    # --- status atual e ciclos ----------------------------------------------
    col_a, col_b = st.columns(2)

    with col_a:
        with st.container(border=True):
            st.subheader("Obras por status hoje")
            rs = dados.resumo_status(f)
            figs = px.bar(
                rs, x="obras", y="STATUS", orientation="h", text="obras",
                color="STATUS", color_discrete_map=COR_STATUS,
                labels={"obras": "Obras", "STATUS": "Status", "valor_orcado": "Valor orçado (R$)"},
                hover_data={"valor_orcado": ":,.0f", "STATUS": False},
            )
            figs.update_traces(textposition="outside", cliponaxis=False, textfont=dict(color=COR_TEXTO, size=13))
            figs.update_yaxes(
                autorange="reversed", title=None, automargin=True,
                tickfont=dict(color=COR_TEXTO, size=12),
            )
            # folga à direita para o número fora da barra não ser cortado
            maximo = float(rs["obras"].max()) if not rs.empty else 1.0
            figs.update_xaxes(title="Obras", showgrid=True, automargin=True, range=[0, maximo * 1.15])
            figs.update_layout(
                height=ALTURA_INFERIOR,
                margin=dict(l=30, r=50, t=30, b=60),  # automargin aumenta a esquerda se precisar
                showlegend=False,
                bargap=0.25,
            )
            mostrar(figs)

    with col_b:
        with st.container(border=True):
            st.subheader("Orçado x faturado por ciclo de medição")
            rc = dados.resumo_ciclo(f)
            if rc.empty:
                st.info("Nenhum ciclo de medição encontrado com os filtros atuais.")
            else:
                rc = rc.copy()
                rc["pct"] = rc["valor_faturado"] / rc["valor_orcado"].where(rc["valor_orcado"] > 0) * 100
                figc = make_subplots(specs=[[{"secondary_y": True}]])
                figc.add_bar(x=rc["ciclo"], y=rc["valor_orcado"], name="Orçado", marker_color=AZUL, secondary_y=False)
                figc.add_bar(x=rc["ciclo"], y=rc["valor_faturado"], name="Faturado", marker_color=VERDE, secondary_y=False)
                figc.add_scatter(
                    x=rc["ciclo"], y=rc["pct"], name="% faturado", mode="lines+markers+text",
                    text=[f"{p:.0f}%" if pd.notna(p) else "" for p in rc["pct"]],
                    textposition="top center", textfont=dict(color=AMBAR, size=11),
                    line=dict(color=AMBAR, width=2), marker=dict(size=6, color=AMBAR),
                    hovertemplate="%{y:.1f}%<extra>% faturado</extra>", secondary_y=True,
                )
                pico = float(rc["pct"].max()) if rc["pct"].notna().any() else 100.0

                # ajuste dos rótulos do eixo conforme a quantidade de ciclos
                n_ciclos = len(rc)
                if n_ciclos <= 8:
                    angulo, passo = 0, 1       # poucos ciclos: texto reto
                elif n_ciclos <= 20:
                    angulo, passo = -45, 1     # rotaciona
                else:
                    angulo, passo = -45, 2     # muitos ciclos: mostra um mês sim, outro não
                # rótulos de % alternados quando há muitos pontos (o hover mostra todos)
                passo_pct = 1 if n_ciclos <= 12 else 2
                figc.data[2].text = [
                    f"{p:.0f}%" if (pd.notna(p) and i % passo_pct == 0) else ""
                    for i, p in enumerate(rc["pct"])
                ]
                figc.data[2].cliponaxis = False

                figc.update_layout(
                    height=ALTURA_INFERIOR, barmode="group", bargap=0.25,
                    margin=dict(l=70, r=70, t=80, b=70),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
                    hovermode="x unified",
                )
                # sem título no eixo X (era ele que se sobrepunha aos meses); o caption explica
                figc.update_xaxes(
                    title=None, type="category", tickangle=angulo, automargin=True,
                    tickmode="array",
                    tickvals=list(rc["ciclo"][::passo]), ticktext=list(rc["ciclo"][::passo]),
                    tickfont=dict(color=COR_TEXTO_SUAVE, size=11),
                )
                figc.update_yaxes(
                    title_text="Valor (R$)", tickformat=",.0f", hoverformat=",.0f",
                    automargin=True, secondary_y=False,
                )
                figc.update_yaxes(
                    title_text="% faturado", ticksuffix="%", range=[0, max(120.0, pico * 1.2)],
                    showgrid=False, automargin=True, secondary_y=True,
                )
                mostrar(figc)
                st.caption(
                    f"No total, o faturado representa {pct_fat:.1f}% do valor orçado. "
                    "Eixo horizontal: ciclo (mês/ano). A linha mostra o % faturado de cada ciclo."
                )

    # --- detalhamento dos alertas ---------------------------------------------
    with st.container(border=True):
        st.subheader("Detalhamento dos alertas")
        t1, t2, t3, t4 = st.tabs([
            f"Prazo vencido ({len(atrasadas)})",
            f"Sem movimentação ({len(parados)})",
            f"Acima do orçamento ({len(acima)})",
            f"Datas a conferir ({len(futuras)})",
        ])
        with t1:
            tabela(atrasadas, "Nenhuma obra em aberto com a data limite vencida.")
        with t2:
            st.caption(
                "Obras em aberto cuja data mais recente registrada (recebimento, 1ª programação ou "
                f"programação final) tem mais de {dias_parada} dias. Ajuste o limite na barra lateral."
            )
            tabela(parados, "Nenhuma obra em aberto parada além do limite.")
        with t3:
            tabela(acima, "Nenhuma obra com faturamento acima do orçado.")
        with t4:
            tabela(futuras, "Nenhuma data de recebimento no futuro.")


with aba1:
    aba_carteira(obras_f)

# ===========================================================================
# ABA 2 - PROGRAMAÇÃO POR EQUIPE
# ===========================================================================
with aba2:
    dias_all = dados.dias_execucao(prog)

    f1, f2, f3 = st.columns([1, 1, 2])
    equipes_all = sorted(dias_all["EQUIPE"].unique())
    equipes = f1.multiselect("Equipes", equipes_all, default=equipes_all)

    pmin, pmax = dias_all["DATA"].min().date(), dias_all["DATA"].max().date()
    periodo = f2.date_input("Período", value=(pmin, pmax), min_value=pmin, max_value=pmax, format="DD/MM/YYYY")

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

    st.markdown(
        '<div class="kpi-grid">'
        + kpi("Obras programadas", inteiro(d["OBRA"].nunique()), "no período selecionado", AZUL)
        + kpi("Dias de execução", inteiro(len(d)), "somando obra x equipe", AMBAR)
        + kpi("Equipes", inteiro(d["EQUIPE"].nunique()), "com obra programada", VERDE)
        + '</div>',
        unsafe_allow_html=True,
    )

    cores = {eq: PALETA[i % len(PALETA)] for i, eq in enumerate(equipes_all)}

    # --- agenda (mostra todos os dias do período filtrado; rola para o lado) ---
    d = d.copy()
    d["DATA"] = d["DATA"].dt.normalize()

    with st.container(border=True):
        st.subheader("Agenda das equipes")

        todos = pd.date_range(pd.Timestamp(periodo[0]), pd.Timestamp(periodo[1]), freq="D")
        tem_fds = (d["DATA"].dt.weekday >= 5).any()  # sáb/dom só aparecem se houver obra
        dias_agenda = [x for x in todos if tem_fds or x.weekday() < 5]
        nomes = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]

        cab = '<th class="eq">Equipe</th>'
        for k, dia in enumerate(dias_agenda):
            cls = []
            if dia == hoje:
                cls.append("hoje")
            if dia.weekday() == 0 and k > 0:
                cls.append("semana")
            cab += f'<th class="{" ".join(cls)}">{nomes[dia.weekday()]}<span>{dia:%d/%m}</span></th>'

        linhas = ""
        for eq in equipes:
            cor = cores.get(eq, AZUL)
            celulas = ""
            for k, dia in enumerate(dias_agenda):
                cls = ' class="semana"' if (dia.weekday() == 0 and k > 0) else ""
                itens = d[(d["EQUIPE"] == eq) & (d["DATA"] == dia)]
                if itens.empty:
                    celulas += f'<td{cls}><span class="vazio">—</span></td>'
                    continue
                chips = ""
                for _, r in itens.iterrows():
                    partes = []
                    if pd.notna(r["ATIVIDADE"]) and str(r["ATIVIDADE"]).strip():
                        partes.append(escape(str(r["ATIVIDADE"]).strip()[:60]))
                    if r["PERIODOS"] == 1:
                        partes.append("meio período")
                    chips += (
                        f'<div class="chip" style="--c:{cor}"><div class="chip-o">{escape(str(r["OBRA"]))}</div>'
                        f'<div class="chip-a">{" · ".join(partes)}</div></div>'
                    )
                celulas += f"<td{cls}>{chips}</td>"
            linhas += (
                f'<tr><td class="eq"><span class="dot" style="background:{cor}"></span>{escape(str(eq))}</td>'
                f'{celulas}</tr>'
            )

        largura = 130 + 200 * len(dias_agenda)
        st.markdown(
            f'<div class="agenda-wrap"><table class="agenda" style="min-width:{largura}px"><thead><tr>{cab}</tr></thead>'
            f'<tbody>{linhas}</tbody></table></div>',
            unsafe_allow_html=True,
        )
        st.caption(
            "Mostra todos os dias do filtro “Período” acima. Arraste a barra de rolagem para o lado (ou deslize "
            "no celular) para ver os outros dias. A coluna da equipe fica fixa e o dia de hoje aparece em azul."
        )

    resumo = dados.resumo_obra_equipe(d)

    # --- tabela --------------------------------------------------------------
    with st.container(border=True):
        st.subheader("Resumo por obra e equipe")
        tab = resumo.copy()
        tab["inicio"] = tab["inicio"].dt.strftime("%d/%m/%Y")
        tab["fim"] = tab["fim"].dt.strftime("%d/%m/%Y")
        tab.columns = ["Obra", "Equipe", "Dias de execução", "Primeiro dia", "Último dia"]
        st.dataframe(tab, hide_index=True)
