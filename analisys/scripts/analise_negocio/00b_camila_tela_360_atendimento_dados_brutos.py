# %% [markdown]
# # 00b — Camila: Tela 360 de Atendimento (Dados Brutos)
# Objetivo: montar a "tela única" para 5 UCs aleatórias e estatísticas de cobertura dos blocos.

# %%
import sys
from pathlib import Path

# Resolução de caminho compatível com script .py e notebook .ipynb (sem __file__ em notebooks)
_starts = [Path.cwd()]
if "__file__" in globals():
    _starts.append(Path(__file__).resolve().parent)

def _find_project_root(starts):
    checked = []
    for item in starts:
        current = item.resolve()
        if current.is_file():
            current = current.parent
        for candidate in (current, *current.parents):
            if candidate in checked:
                continue
            checked.append(candidate)
            if (candidate / "data").is_dir() and (candidate / "analisys").is_dir():
                return candidate
    locations = ", ".join(str(s.resolve()) for s in starts)
    raise FileNotFoundError(
        f"Raiz do projeto não encontrada. Esperado 'data/' e 'analisys/' a partir de: {locations}"
    )

PROJECT_ROOT = _find_project_root(_starts)
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import numpy as np
import json
import matplotlib
# Backend inline para exibir gráficos no notebook
import matplotlib_inline.backend_inline
matplotlib.use('module://matplotlib_inline.backend_inline')
import matplotlib.pyplot as plt
import random

# Configuração para saída de alta qualidade no notebook
matplotlib_inline.backend_inline.set_matplotlib_formats('retina')

# %% [markdown]
## Carregamento dos dados brutos (funções inline, sem _helpers)

# %%
_REQUIRED_DATA_FILES = (
    "unidades_consumidoras.csv",
    "medidores.csv",
    "faturas.csv",
    "geracao_distribuida.csv",
    "ocorrencias_rede.csv",
    "atendimentos.json",
    "inspecoes.xlsx",
)

def _read_csv(path: Path, **kwargs) -> pd.DataFrame:
    sample = path.read_text(encoding="utf-8", errors="replace").splitlines()[:1]
    if not sample:
        raise ValueError(f"Arquivo CSV vazio: {path}")
    separator = ";" if sample[0].count(";") > sample[0].count(",") else ","
    options = {"sep": separator, **kwargs}
    try:
        return pd.read_csv(path, **options)
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="latin-1", **options)

def _read_file(path: Path, **kwargs) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return _read_csv(path, **kwargs)
    if suffix == ".json":
        return pd.read_json(path, **kwargs)
    if suffix == ".xlsx":
        return pd.read_excel(path, **kwargs)
    raise ValueError(f"Formato não suportado: {path}")

def resolve_data_file(name: str, root: Path) -> Path:
    data_dir = root / "data"
    direct = data_dir / name
    if direct.is_file():
        return direct
    matches = sorted(p for p in data_dir.rglob(Path(name).name) if p.is_file())
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise FileNotFoundError(f"Arquivo obrigatório '{name}' não encontrado em {data_dir} nem subdiretórios.")
    raise FileNotFoundError(f"Arquivo '{name}' encontrado em múltiplos locais: {', '.join(str(p) for p in matches)}")

def resolve_readings_files(root: Path) -> list[Path]:
    data_dir = root / "data"
    candidates = sorted(p for p in data_dir.rglob("*.csv") if p.is_file() and "leitura" in p.stem.lower())
    if not candidates:
        raise FileNotFoundError(f"Nenhum CSV de leituras encontrado em {data_dir} ou subdiretórios.")
    return candidates

def load_all_raw_data(root: Path) -> dict[str, pd.DataFrame]:
    files = {name.removesuffix(Path(name).suffix): resolve_data_file(name, root) for name in _REQUIRED_DATA_FILES}
    files["leituras"] = resolve_readings_files(root)
    return {
        "uc": _read_file(files["unidades_consumidoras"]),
        "faturas": _read_file(files["faturas"]),
        "leituras": pd.concat([_read_file(p) for p in files["leituras"]], ignore_index=True, sort=False),
        "medidores": _read_file(files["medidores"]),
        "gd": _read_file(files["geracao_distribuida"]),
        "ocorrencias": _read_file(files["ocorrencias_rede"]),
        "atendimentos": _read_file(files["atendimentos"]),
        "inspecoes": _read_file(files["inspecoes"]),
    }

def to_numeric_safe(series: pd.Series, decimal_comma: bool = False) -> tuple[pd.Series, int]:
    values = series.astype("string").str.strip()
    if decimal_comma:
        values = values.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    converted = pd.to_numeric(values, errors="coerce")
    failures = int((values.notna() & values.ne("") & converted.isna()).sum())
    return converted, failures

def safe_divide(numerator: float, denominator: float):
    if denominator is None or pd.isna(denominator) or denominator == 0:
        return None
    return float(numerator / denominator)

def get_resultados_dir(subdir: str, root: Path) -> Path:
    directory = root / "analisys" / "resultados" / subdir
    directory.mkdir(parents=True, exist_ok=True)
    return directory

def get_graficos_dir(subdir: str | None, root: Path) -> Path:
    directory = root / "analisys" / "graficos"
    if subdir:
        directory /= subdir
    directory.mkdir(parents=True, exist_ok=True)
    return directory

# Carrega dados
dfs = load_all_raw_data(PROJECT_ROOT)

# Diretórios de saída
PASTA_RESULTADOS = get_resultados_dir("analise_negocio/dados_brutos", PROJECT_ROOT)
PASTA_GRAFICOS = get_graficos_dir("analise_negocio", PROJECT_ROOT)

def exibir_grafico(fig, nome: str):
    output = PASTA_GRAFICOS / f"{nome}.png"
    fig.savefig(output, dpi=150, bbox_inches="tight")
    print(f"Gráfico gerado: {output}")
    plt.show(fig)  # Exibe no notebook
    plt.close(fig)  # Libera memória

# %%
# Conversões mínimas
uc = dfs["uc"]
fat = dfs["faturas"]
leit = dfs["leituras"]
med = dfs["medidores"]
gd = dfs["gd"]
oco = dfs["ocorrencias"]
ate = dfs["atendimentos"]

# Faturas
fat["valor_energia_num"], falhas_valor = to_numeric_safe(fat["valor_energia"], decimal_comma=True)
fat["mes_ref_dt"] = pd.to_datetime(fat["mes_referencia"], format="%Y-%m", errors="coerce")

# Leituras
leit["consumo_num"], falhas_consumo = to_numeric_safe(leit["consumo_kwh"], decimal_comma=True)
leit["mes_ref_dt"] = pd.to_datetime(leit["mes_referencia"], format="%Y-%m", errors="coerce")

# GD - usar colunas que existem
# id_uc, potencia_kwp, data_conexao, modalidade, energia_injetada_kwh_media_mensal

# Ocorrências
oco["duracao_min_num"] = pd.to_numeric(oco["duracao_min"].astype(str).str.replace(",", "."), errors="coerce")

# Atendimentos - não tem coluna de status, vamos inferir
# data_abertura e data_fechamento - se data_fechamento nula/vazia = "aberto"

# Medidores - data_instalacao, data_retirada, status

# %%
# Escolhe 5 UCs aleatórias (seed 42)
np.random.seed(42)
ucs_amostra = uc["id_uc"].sample(n=5, random_state=42).tolist()
print("UCs selecionadas:", ucs_amostra)

# Verifica UCs duplicadas no cadastro
dup_uc = uc["id_uc"].value_counts()
ucs_duplicadas = dup_uc[dup_uc > 1]
n_ucs_duplicadas = int(len(ucs_duplicadas))
total_linhas_duplicadas = int(ucs_duplicadas.sum() - n_ucs_duplicadas)
print(f"UCs duplicadas no cadastro: {n_ucs_duplicadas} (linhas extras: {total_linhas_duplicadas})")

# Se alguma UC da amostra aparecer mais de uma vez, mostre os registros e colunas que diferem
for uc_id in ucs_amostra:
    uc_rows = uc[uc["id_uc"] == uc_id]
    if len(uc_rows) > 1:
        print(f"\nUC {uc_id} tem {len(uc_rows)} registros no cadastro:")
        print(uc_rows.to_string())
        # Colunas que diferem
        for col in uc_rows.columns:
            vals = uc_rows[col].unique()
            if len(vals) > 1:
                print(f"  Coluna '{col}' difere: {vals}")

telas = {}
for uc_id in ucs_amostra:
    uc_row = uc[uc["id_uc"] == uc_id].iloc[0]

    # Consumo últimos 3 meses (2026-04 a 2026-06) vs mesmo período 2025
    ult_meses = ["2026-04", "2025-04", "2026-05", "2025-05", "2026-06", "2025-06"]
    leit_uc = leit[leit["id_uc"] == uc_id]
    consumo_comp = {}
    for m_atual, m_ant in [("2026-04", "2025-04"), ("2026-05", "2025-05"), ("2026-06", "2025-06")]:
        v_ult = leit_uc[leit_uc["mes_referencia"] == m_atual]["consumo_num"]
        v_ant = leit_uc[leit_uc["mes_referencia"] == m_ant]["consumo_num"]

        # Se houver mais de uma leitura para o mesmo mês, mostre todas e marque
        ult_list = v_ult.tolist()
        ant_list = v_ant.tolist()

        leitura_duplicada_ult = len(ult_list) > 1
        leitura_duplicada_ant = len(ant_list) > 1

        v_ult_val = ult_list[0] if ult_list else np.nan
        v_ant_val = ant_list[0] if ant_list else np.nan

        subiu = "sim" if (not np.isnan(v_ult_val) and not np.isnan(v_ant_val) and v_ult_val > v_ant_val) else ("não" if not np.isnan(v_ult_val) and not np.isnan(v_ant_val) else "sem dado")

        consumo_comp[m_atual] = {
            "atual_kwh": float(v_ult_val) if not np.isnan(v_ult_val) else "sem dado",
            "ano_anterior_kwh": float(v_ant_val) if not np.isnan(v_ant_val) else "sem dado",
            "subiu": subiu,
            "leitura_duplicada_atual": leitura_duplicada_ult,
            "leitura_duplicada_anterior": leitura_duplicada_ant,
            "todas_leituras_atual": [float(x) if not np.isnan(x) else "sem dado" for x in ult_list] if ult_list else [],
            "todas_leituras_anterior": [float(x) if not np.isnan(x) else "sem dado" for x in ant_list] if ant_list else [],
        }

    # Faturas em aberto
    fat_uc = fat[(fat["id_uc"] == uc_id) & (fat["status"] == "EM ABERTO")]
    faturas_aberto = {
        "quantidade": int(len(fat_uc)),
        "valor_total_rs": float(fat_uc["valor_energia_num"].sum()) if not fat_uc.empty else 0
    }

    # Medidores - data_instalacao, data_retirada, status
    med_uc = med[med["id_uc"] == uc_id]
    if not med_uc.empty:
        medidores = []
        for _, m in med_uc.iterrows():
            med_info = {
                "id_medidor": m.get("id_medidor"),
                "modelo": m.get("modelo"),
                "tipo": m.get("tipo"),
                "data_instalacao": str(m.get("data_instalacao")) if pd.notna(m.get("data_instalacao")) else "sem dado",
                "data_retirada": str(m.get("data_retirada")) if pd.notna(m.get("data_retirada")) else "sem dado",
                "status": m.get("status"),
                "sem_data_retirada": pd.isna(m.get("data_retirada")) or str(m.get("data_retirada")).strip() == "",
            }
            medidores.append(med_info)
    else:
        medidores = "sem dado"

    # GD - usar colunas que existem na tabela
    gd_uc = gd[gd["id_uc"] == uc_id]
    tem_gd = not gd_uc.empty
    if tem_gd:
        gd_info = gd_uc[["id_uc", "potencia_kwp", "data_conexao", "modalidade", "energia_injetada_kwh_media_mensal"]].to_dict("records")
    else:
        gd_info = "sem dado"

    # Ocorrências UC e alimentador
    alimentador = uc_row.get("alimentador", "")
    oco_uc = oco[oco["id_uc"] == uc_id]
    oco_alim = oco[oco["alimentador"] == alimentador] if alimentador else pd.DataFrame()
    ocorrencias = {
        "na_uc": oco_uc[["id_ocorrencia", "tipo", "causa", "data_abertura", "data_encerramento", "duracao_min"]].to_dict("records") if not oco_uc.empty else "sem dado",
        "no_alimentador": oco_alim[["id_ocorrencia", "tipo", "causa", "data_abertura", "data_encerramento", "duracao_min"]].to_dict("records") if not oco_alim.empty else "sem dado",
    }

    # Chamados (atendimentos) - lista com data_abertura e data_fechamento, marca "aberto" se data_fechamento nula
    ate_uc = ate[ate["id_uc"] == uc_id]
    if not ate_uc.empty:
        chamados = []
        for _, c in ate_uc.iterrows():
            data_fech = c.get("data_fechamento")
            is_aberto = pd.isna(data_fech) or (isinstance(data_fech, str) and data_fech.strip() == "")
            chamados.append({
                "protocolo": c.get("protocolo"),
                "assunto": c.get("assunto"),
                "data_abertura": str(c.get("data_abertura")) if pd.notna(c.get("data_abertura")) else "sem dado",
                "data_fechamento": str(data_fech) if pd.notna(data_fech) and str(data_fech).strip() != "" else "sem dado",
                "status": "aberto" if is_aberto else "fechado",
            })
    else:
        chamados = "sem dado"

    telas[uc_id] = {
        "cliente": {
            "nome": uc_row.get("nome_titular", "sem dado"),
            "cpf_cnpj": uc_row.get("cpf_cnpj", "sem dado"),
            "endereco": f"{uc_row.get('logradouro','')} {uc_row.get('numero','')}, {uc_row.get('bairro','')}, {uc_row.get('municipio','')} - {uc_row.get('uf','')}",
            "classe": uc_row.get("classe", "sem dado"),
        },
        "consumo_ultimos_3_meses_vs_ano_anterior": consumo_comp,
        "faturas_em_aberto": faturas_aberto,
        "medidores": medidores,
        "geracao_distribuida": gd_info,
        "ocorrencias": ocorrencias,
        "chamados": chamados,
    }

# %%
# Cobertura dos blocos para TODAS as UCs
# Denominador = nº de id_uc DISTINTOS do cadastro
total_ucs_distintas = uc["id_uc"].nunique()
print(f"Total UCs distintas no cadastro: {total_ucs_distintas}")

tem_consumo = leit["id_uc"].nunique()
tem_fatura_aberta = fat[fat["status"] == "EM ABERTO"]["id_uc"].nunique()
tem_medidor = med["id_uc"].nunique()
tem_gd = gd["id_uc"].nunique()
tem_ocorrencia = oco["id_uc"].nunique()
tem_chamado = ate["id_uc"].nunique() if "id_uc" in ate.columns else 0

# IDs de outras tabelas que não existem no cadastro
ids_consumo_sem_cadastro = set(leit["id_uc"].unique()) - set(uc["id_uc"].unique())
ids_fatura_sem_cadastro = set(fat["id_uc"].unique()) - set(uc["id_uc"].unique())
ids_medidor_sem_cadastro = set(med["id_uc"].unique()) - set(uc["id_uc"].unique())
ids_gd_sem_cadastro = set(gd["id_uc"].unique()) - set(uc["id_uc"].unique())
ids_oco_sem_cadastro = set(oco["id_uc"].unique()) - set(uc["id_uc"].unique())
ids_chamado_sem_cadastro = set(ate["id_uc"].unique()) - set(uc["id_uc"].unique()) if "id_uc" in ate.columns else set()

print(f"IDs em leituras sem cadastro: {len(ids_consumo_sem_cadastro)}")
print(f"IDs em faturas sem cadastro: {len(ids_fatura_sem_cadastro)}")
print(f"IDs em medidores sem cadastro: {len(ids_medidor_sem_cadastro)}")
print(f"IDs em GD sem cadastro: {len(ids_gd_sem_cadastro)}")
print(f"IDs em ocorrências sem cadastro: {len(ids_oco_sem_cadastro)}")
print(f"IDs em chamados sem cadastro: {len(ids_chamado_sem_cadastro)}")

def pct(val, denom):
    if denom == 0:
        return None
    return round(val / denom * 100, 2)

cobertura = {
    "consumo": {"com_dado": int(tem_consumo), "pct": pct(tem_consumo, total_ucs_distintas)},
    "fatura_em_aberto": {"com_dado": int(tem_fatura_aberta), "pct": pct(tem_fatura_aberta, total_ucs_distintas)},
    "medidor": {"com_dado": int(tem_medidor), "pct": pct(tem_medidor, total_ucs_distintas)},
    "gd": {"com_dado": int(tem_gd), "pct": pct(tem_gd, total_ucs_distintas)},
    "ocorrencia": {"com_dado": int(tem_ocorrencia), "pct": pct(tem_ocorrencia, total_ucs_distintas)},
    "chamado": {"com_dado": int(tem_chamado), "pct": pct(tem_chamado, total_ucs_distintas)},
}

# %%
# Gráfico 1: % UCs com cada bloco
fig, ax = plt.subplots(figsize=(8, 5))
blocos = list(cobertura.keys())
pcts = [cobertura[b]["pct"] for b in blocos]
ax.barh(blocos, pcts, color="#4c72b0")
ax.set_xlabel("% de UCs com dado")
ax.set_title("Cobertura de informações por bloco (todas UCs)")
for i, v in enumerate(pcts):
    ax.text(v + 1, i, f"{v:.1f}%", va="center")
exibir_grafico(fig, "01_cobertura_blocos_ucs")

# %%
# Gráfico 2: consumo últimos 12 meses vs 12 meses anteriores para uma UC (primeira da amostra)
# Alinhar pelo mês do calendário (jan a dez), não pelo rótulo AAAA-MM
uc_exemplo = ucs_amostra[0]
leit_ex = leit[leit["id_uc"] == uc_exemplo].copy()
leit_ex = leit_ex.sort_values("mes_ref_dt")

# Obter últimos 12 meses disponíveis
meses_disponiveis = sorted(leit_ex["mes_referencia"].unique())
if len(meses_disponiveis) >= 12:
    ultimos_12_meses = meses_disponiveis[-12:]
    anteriores_12_meses = meses_disponiveis[-24:-12] if len(meses_disponiveis) >= 24 else []
else:
    ultimos_12_meses = meses_disponiveis
    anteriores_12_meses = []

ultimos_12 = leit_ex[leit_ex["mes_referencia"].isin(ultimos_12_meses)]
anteriores_12 = leit_ex[leit_ex["mes_referencia"].isin(anteriores_12_meses)]

# Criar rótulos de mês calendário (Jan, Fev, ...)
def mes_calendario(label):
    """Converte AAAA-MM para nome do mês."""
    try:
        return pd.to_datetime(label).strftime("%b")
    except:
        return label

fig, ax = plt.subplots(figsize=(10, 4))
if not ultimos_12.empty:
    x_ult = [mes_calendario(m) for m in ultimos_12["mes_referencia"]]
    ax.plot(x_ult, ultimos_12["consumo_num"], marker="o", label="Últimos 12 meses")
if not anteriores_12.empty:
    x_ant = [mes_calendario(m) for m in anteriores_12["mes_referencia"]]
    ax.plot(x_ant, anteriores_12["consumo_num"], marker="o", label="12 meses anteriores")
ax.set_ylabel("Consumo (kWh)")
ax.set_title(f"Consumo mensal — UC {uc_exemplo} (alinhado por mês calendário)")
ax.legend()
ax.tick_params(axis='x', rotation=45)
exibir_grafico(fig, "02_consumo_12m_vs_anterior_uc_exemplo")

# %%
# Helper para JSON seguro
def json_safe(obj):
    if isinstance(obj, dict):
        return {k: json_safe(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [json_safe(v) for v in obj]
    elif isinstance(obj, float):
        if pd.isna(obj) or np.isinf(obj):
            return None
        return obj
    elif pd.isna(obj):
        return None
    return obj

# %%
resultado = {
    "ucs_selecionadas": ucs_amostra,
    "telas": telas,
    "cobertura_blocos_todas_ucs": cobertura,
    "ucs_duplicadas_no_cadastro": {
        "qtd_ucs": n_ucs_duplicadas,
        "linhas_extras": total_linhas_duplicadas,
        "detalhes": {str(k): int(v) for k, v in ucs_duplicadas.items()},
    },
    "ids_sem_cadastro": {
        "leituras": len(ids_consumo_sem_cadastro),
        "faturas": len(ids_fatura_sem_cadastro),
        "medidores": len(ids_medidor_sem_cadastro),
        "gd": len(ids_gd_sem_cadastro),
        "ocorrencias": len(ids_oco_sem_cadastro),
        "chamados": len(ids_chamado_sem_cadastro),
    },
    "observacoes": [
        "Consumo comparado apenas onde há leitura nos dois períodos; 'sem dado' onde falta.",
        "Faturas em aberto considera status 'EM ABERTO' exatamente como está no dado.",
        "Chamados: tabela não tem coluna de status. Marcado 'aberto' se data_fechamento for nula/vazia, 'fechado' caso contrário.",
        "Medidores: mostrada data_instalacao, data_retirada, status; destacado 'sem_data_retirada' quando aplicável.",
        "Cobertura: denominador = nº de id_uc DISTINTOS do cadastro. Numerador conta só id_uc que existem no cadastro.",
        f"IDs de outras tabelas sem cadastro reportados em 'ids_sem_cadastro'.",
        f"UCs duplicadas no cadastro: {n_ucs_duplicadas} UCs com {total_linhas_duplicadas} linhas extras (multiplicam no join).",
        "Consumo: se houver mais de uma leitura para o mesmo mês, mostradas todas e marcado 'leitura_duplicada'.",
    ],
}

resultado = json_safe(resultado)

with open(PASTA_RESULTADOS / "camila_tela_360_atendimento_dados_brutos.json", "w", encoding="utf-8") as f:
    json.dump(resultado, f, ensure_ascii=False, indent=2, allow_nan=False)
print("JSON salvo.")