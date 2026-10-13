"""
dados.py - leitura e preparação dos dados da planilha CONTROLE DE OBRAS CELESC.

Aqui não tem nada de tela: só funções que leem o Excel e devolvem tabelas
(DataFrames) prontas para o dashboard.py desenhar.
"""
from io import BytesIO

import pandas as pd

# ---------------------------------------------------------------------------
# CONFIGURAÇÃO - se mudarem o nome de uma aba na planilha, ajuste aqui
# ---------------------------------------------------------------------------
ABA_OBRAS = "BASE DE DADOS OBRAS FLN"
ABA_PROGRAMACAO = "PROGRAMAÇÃO"

# Status que contam como obra "concluída" (saiu da carteira em aberto)
STATUS_CONCLUIDOS = ["CONCLUIDA", "MEDIÇÃO", "FATURADA"]

# Ordem em que os status aparecem nos gráficos (do início ao fim do processo)
ORDEM_STATUS = [
    "VIABILIZAÇÃO",
    "PROGRAMADA",
    "PROG/PENDENCIA",
    "REPROGRAMAR",
    "CONCLUIDA",
    "MEDIÇÃO",
    "FATURADA",
]


def _abrir(origem):
    """Aceita caminho de arquivo ou bytes (upload do Streamlit)."""
    return BytesIO(origem) if isinstance(origem, (bytes, bytearray)) else origem


def _sem_colunas_vazias(df: pd.DataFrame) -> pd.DataFrame:
    return df.loc[:, ~df.columns.astype(str).str.startswith("Unnamed")]


# ---------------------------------------------------------------------------
# LEITURA DA PLANILHA GOOGLE
# ---------------------------------------------------------------------------
def _ler_csv_google(url: str) -> pd.DataFrame:
    """Lê CSV do Google Sheets preservando os valores como texto."""
    df = pd.read_csv(url, dtype=str, keep_default_na=False)
    df.columns = [str(c).replace("\ufeff", "").strip() for c in df.columns]
    return df.replace({"": pd.NA})


def _numero(valor):
    """Converte números brasileiros (1.234,56) e números normais."""
    if pd.isna(valor):
        return pd.NA
    s = str(valor).strip().replace("R$", "").replace("\xa0", "").strip()
    if not s:
        return pd.NA
    # formato brasileiro com vírgula decimal
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    else:
        # Se houver vários pontos ou um ponto seguido de 3 dígitos,
        # trate-o como separador de milhar.
        partes = s.split(".")
        if len(partes) > 1 and all(len(x) == 3 for x in partes[1:]):
            s = "".join(partes)
    return pd.to_numeric(s, errors="coerce")


def _limpar_n_obra(serie):
    s = serie.astype(str).str.strip()
    n = pd.to_numeric(s.str.replace(".", "", regex=False).str.replace(",", ".", regex=False), errors="coerce")
    return n


# ---------------------------------------------------------------------------
# CARTEIRA DE OBRAS
# ---------------------------------------------------------------------------
def carregar_obras(origem) -> pd.DataFrame:
    df = pd.read_excel(_abrir(origem), sheet_name=ABA_OBRAS)
    df = _sem_colunas_vazias(df)

    # linhas vazias no fim da aba (só têm fórmula) não são obras
    df = df.dropna(subset=["N. OBRA"]).copy()
    df["N. OBRA"] = df["N. OBRA"].astype("int64").astype(str)

    # datas (a coluna PROGRAMAÇÃO FINAL às vezes tem texto, ex.: "AG. PRIMEIRO DIA")
    for col in ["DATA RECEBIMENTO", "DATA LIMITE", "1º PROGRAMAÇÃO", "PROGRAMAÇÃO FINAL"]:
        df[col] = pd.to_datetime(df[col], errors="coerce")

    # "09 - FATURADA" -> "FATURADA"
    df["STATUS"] = (
        df["STATUS DE PROGRAMAÇÃO"]
        .fillna("SEM STATUS")
        .str.replace(r"^\d+\s*-\s*", "", regex=True)
        .str.strip()
    )
    df["CONCLUIDA"] = df["STATUS"].isin(STATUS_CONCLUIDOS)

    # data em que a obra saiu da carteira: programação final (ou a 1ª, se faltar)
    df["DATA CONCLUSÃO"] = df["PROGRAMAÇÃO FINAL"].fillna(df["1º PROGRAMAÇÃO"])
    df.loc[~df["CONCLUIDA"], "DATA CONCLUSÃO"] = pd.NaT

    # ciclo de medição "03/26" -> data 01/03/2026 (para ordenar)
    df["CICLO DATA"] = pd.to_datetime("01/" + df["CICLO"].astype(str), format="%d/%m/%y", errors="coerce")

    for col in ["VALOR ORÇADO", "VALOR FATURADO"]:
        df[col] = df[col].map(_numero).astype("float64").fillna(0.0)

    return df.reset_index(drop=True)


def carregar_obras_google(url: str) -> pd.DataFrame:
    """Carrega a aba de obras diretamente do Google Sheets."""
    df = _ler_csv_google(url)
    df = _sem_colunas_vazias(df)

    obrigatorias = ["N. OBRA", "STATUS DE PROGRAMAÇÃO", "DATA RECEBIMENTO", "DATA LIMITE",
                    "1º PROGRAMAÇÃO", "PROGRAMAÇÃO FINAL", "CICLO", "VALOR ORÇADO", "VALOR FATURADO"]
    faltantes = [c for c in obrigatorias if c not in df.columns]
    if faltantes:
        raise ValueError(
            "A aba de obras foi encontrada, mas faltam estas colunas: " + ", ".join(faltantes)
            + "\nColunas encontradas: " + ", ".join(map(str, df.columns))
        )

    df["N. OBRA"] = _limpar_n_obra(df["N. OBRA"])
    df = df.dropna(subset=["N. OBRA"]).copy()
    df["N. OBRA"] = df["N. OBRA"].astype("int64").astype(str)

    for col in ["DATA RECEBIMENTO", "DATA LIMITE", "1º PROGRAMAÇÃO", "PROGRAMAÇÃO FINAL"]:
        df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)

    df["STATUS"] = (
        df["STATUS DE PROGRAMAÇÃO"]
        .fillna("SEM STATUS")
        .astype(str)
        .str.replace(r"^\d+\s*-\s*", "", regex=True)
        .str.strip()
    )
    df["CONCLUIDA"] = df["STATUS"].isin(STATUS_CONCLUIDOS)
    df["DATA CONCLUSÃO"] = df["PROGRAMAÇÃO FINAL"].fillna(df["1º PROGRAMAÇÃO"])
    df.loc[~df["CONCLUIDA"], "DATA CONCLUSÃO"] = pd.NaT

    # Aceita ciclos como 03/26, 03/2026 e valores de data.
    ciclo = df["CICLO"].astype(str).str.strip()
    ciclo_data = pd.to_datetime("01/" + ciclo, format="%d/%m/%y", errors="coerce")
    faltou = ciclo_data.isna()
    ciclo_data.loc[faltou] = pd.to_datetime("01/" + ciclo[faltou], format="%d/%m/%Y", errors="coerce")
    df["CICLO DATA"] = ciclo_data

    for col in ["VALOR ORÇADO", "VALOR FATURADO"]:
        df[col] = df[col].map(_numero).astype("float64").fillna(0.0)

    return df.reset_index(drop=True)


def carregar_programacao_google(url: str) -> pd.DataFrame:
    """Carrega a aba de programação diretamente do Google Sheets."""
    p = _ler_csv_google(url)
    p = _sem_colunas_vazias(p)
    p = p.rename(columns={"Coluna 1": "DATA"})
    obrigatorias = ["DATA", "EQUIPE", "PROJETO", "DESCRIÇÃO DA ATIVIDADE", "ENDEREÇO", "PERIODO"]
    faltantes = [c for c in obrigatorias if c not in p.columns]
    if faltantes:
        raise ValueError(
            "A aba de programação foi encontrada, mas faltam estas colunas: " + ", ".join(faltantes)
            + "\nColunas encontradas: " + ", ".join(map(str, p.columns))
        )
    p["DATA"] = pd.to_datetime(p["DATA"], errors="coerce", dayfirst=True)
    p["EQUIPE"] = p["EQUIPE"].fillna("").astype(str).str.strip()
    num = pd.to_numeric(p["PROJETO"], errors="coerce")
    p = p[num.notna() & p["DATA"].notna()].copy()
    p["PROJETO"] = num.loc[p.index].astype("int64").astype(str)
    atividade = p["DESCRIÇÃO DA ATIVIDADE"].fillna("").astype(str)
    p = p[~atividade.str.contains("FOLGA", case=False)].copy()
    p["OBRA"] = p["ENDEREÇO"].fillna(p["PROJETO"]).astype(str).str.strip()
    return p.reset_index(drop=True)


def evolucao_mensal(df: pd.DataFrame, hoje: pd.Timestamp) -> pd.DataFrame:
    """Entradas x conclusões por mês e carteira em aberto acumulada."""
    ent = df.dropna(subset=["DATA RECEBIMENTO"]).copy()
    ent["mes"] = ent["DATA RECEBIMENTO"].dt.to_period("M")
    con = df.dropna(subset=["DATA CONCLUSÃO"]).copy()
    con["mes"] = con["DATA CONCLUSÃO"].dt.to_period("M")

    ini = min(ent["mes"].min(), con["mes"].min())
    fim = max(ent["mes"].max(), con["mes"].max(), hoje.to_period("M"))
    meses = pd.period_range(ini, fim, freq="M")

    out = pd.DataFrame(index=meses)
    out["entradas"] = ent.groupby("mes").size()
    out["concluidas"] = con.groupby("mes").size()
    out["valor_entradas"] = ent.groupby("mes")["VALOR ORÇADO"].sum()
    out["valor_concluidas"] = con.groupby("mes")["VALOR ORÇADO"].sum()
    out = out.fillna(0)

    out["em_aberto"] = (out["entradas"] - out["concluidas"]).cumsum()
    out["valor_em_aberto"] = (out["valor_entradas"] - out["valor_concluidas"]).cumsum()
    out["entradas_acum"] = out["entradas"].cumsum()
    out["concluidas_acum"] = out["concluidas"].cumsum()

    out.index.name = "mes"
    out = out.reset_index()
    out["mes"] = out["mes"].dt.to_timestamp()
    return out


def resumo_status(df: pd.DataFrame) -> pd.DataFrame:
    r = (
        df.groupby("STATUS")
        .agg(obras=("N. OBRA", "count"), valor_orcado=("VALOR ORÇADO", "sum"))
        .reset_index()
    )
    ordem = {s: i for i, s in enumerate(ORDEM_STATUS)}
    r["ordem"] = r["STATUS"].map(ordem).fillna(99)
    return r.sort_values("ordem").drop(columns="ordem").reset_index(drop=True)


def resumo_ciclo(df: pd.DataFrame) -> pd.DataFrame:
    """Valor orçado x faturado por ciclo de medição."""
    r = (
        df.dropna(subset=["CICLO DATA"])
        .groupby("CICLO DATA")
        .agg(
            obras=("N. OBRA", "count"),
            valor_orcado=("VALOR ORÇADO", "sum"),
            valor_faturado=("VALOR FATURADO", "sum"),
        )
        .reset_index()
        .sort_values("CICLO DATA")
    )
    r["ciclo"] = r["CICLO DATA"].dt.strftime("%m/%y")
    return r


def obras_atrasadas(df: pd.DataFrame, hoje: pd.Timestamp) -> pd.DataFrame:
    """Obras ainda não concluídas cujo prazo (DATA LIMITE) já passou."""
    a = df[(~df["CONCLUIDA"]) & (df["DATA LIMITE"] < hoje)].copy()
    a["DIAS DE ATRASO"] = (hoje - a["DATA LIMITE"]).dt.days
    cols = [
        "N. OBRA", "DESCRIÇÃO PROJETO", "FISCAL CELESC", "STATUS",
        "DATA LIMITE", "DIAS DE ATRASO", "VALOR ORÇADO", "OBSERVAÇÕES",
    ]
    return a[cols].sort_values("DIAS DE ATRASO", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# PROGRAMAÇÃO POR EQUIPE
# ---------------------------------------------------------------------------
def carregar_programacao(origem) -> pd.DataFrame:
    p = pd.read_excel(_abrir(origem), sheet_name=ABA_PROGRAMACAO)
    p = _sem_colunas_vazias(p)
    p = p.rename(columns={"Coluna 1": "DATA"})
    p["DATA"] = pd.to_datetime(p["DATA"], errors="coerce")
    p["EQUIPE"] = p["EQUIPE"].astype(str).str.strip()

    # Só entram linhas com número de projeto de verdade.
    # (a coluna PROJETO também tem textos como FOLGA, FERIADO, SABADO, DOMINGO)
    num = pd.to_numeric(p["PROJETO"], errors="coerce")
    p = p[num.notna() & p["DATA"].notna()].copy()
    p["PROJETO"] = num[p.index].astype("int64").astype(str)

    # "folga" lançada como atividade não é execução
    atividade = p["DESCRIÇÃO DA ATIVIDADE"].fillna("")
    p = p[~atividade.str.contains("FOLGA", case=False)].copy()

    # nome da obra: usa o endereço (ex.: "400802158 - FORQUILINHAS"); se faltar, o nº do projeto
    p["OBRA"] = p["ENDEREÇO"].fillna(p["PROJETO"]).astype(str).str.strip()
    return p.reset_index(drop=True)


def dias_execucao(p: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por (dia, equipe, obra) - base do gráfico de Gantt."""
    d = (
        p.groupby(["DATA", "EQUIPE", "OBRA"], as_index=False)
        .agg(
            ATIVIDADE=("DESCRIÇÃO DA ATIVIDADE", "first"),
            PERIODOS=("PERIODO", "count"),  # 1 = meio dia, 2 = dia todo
        )
    )
    d["FIM"] = d["DATA"] + pd.Timedelta(days=1)
    return d.sort_values(["EQUIPE", "DATA"]).reset_index(drop=True)


def resumo_obra_equipe(d: pd.DataFrame) -> pd.DataFrame:
    r = (
        d.groupby(["OBRA", "EQUIPE"])
        .agg(
            dias=("DATA", "nunique"),
            inicio=("DATA", "min"),
            fim=("DATA", "max"),
        )
        .reset_index()
    )
    return r.sort_values(["inicio", "OBRA"]).reset_index(drop=True)


def ocupacao_semanal(d: pd.DataFrame) -> pd.DataFrame:
    """Tabela equipe x semana com a quantidade de dias com obra programada."""
    x = d.copy()
    x["SEMANA"] = x["DATA"] - pd.to_timedelta(x["DATA"].dt.weekday, unit="D")
    t = x.pivot_table(index="EQUIPE", columns="SEMANA", values="DATA", aggfunc="nunique", fill_value=0)
    t.columns = [c.strftime("%d/%m") for c in t.columns]
    return t
