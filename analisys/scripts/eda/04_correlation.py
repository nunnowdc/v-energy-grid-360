"""Calcula correlações numéricas por fonte e gera heatmaps da EDA."""

# %% [markdown]
# # Correlação numérica por fonte
#
# Calcula Pearson e Spearman sem fazer joins entre tabelas.

# %%
import json
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import polars as pl

_starts = [Path.cwd()]
if "__file__" in globals():
    _starts.append(Path(__file__).resolve().parent)
for _start in _starts:
    for _candidate in (_start, *_start.parents):
        if (_candidate / "data").is_dir() and (_candidate / "analisys").is_dir():
            sys.path.insert(0, str(_candidate))
            break
    else:
        continue
    break

try:
    from analisys.scripts.analise_negocio._helpers import (
        get_data_dir,
        get_resultados_dir,
        get_graficos_dir,
        resolve_data_file,
        resolve_readings_files,
    )
except ModuleNotFoundError as error:
    if error.name != "analisys":
        raise
    from analise_negocio._helpers import (
        get_data_dir,
        get_resultados_dir,
        get_graficos_dir,
        resolve_data_file,
        resolve_readings_files,
    )


def find_root() -> Path:
    try:
        from analisys.scripts.analise_negocio._helpers import get_project_root
    except ModuleNotFoundError as error:
        if error.name != "analisys":
            raise
        from analise_negocio._helpers import get_project_root

    return get_project_root()


ROOT = find_root()
DATA_DIR = get_data_dir(ROOT)
RESULTS_DIR = get_resultados_dir(root=ROOT)
GRAPHICS_DIR = get_graficos_dir("resultados", ROOT)

# %%

def detect_separator(path: Path) -> str:
    with path.open("r", encoding="utf-8", errors="replace") as file:
        header = file.readline()
    return ";" if header.count(";") > header.count(",") else ","


def read_csv(path: Path) -> pl.DataFrame:
    kwargs = {
        "separator": detect_separator(path),
        "infer_schema_length": 0,
        "truncate_ragged_lines": True,
    }
    try:
        return pl.read_csv(path, **kwargs)
    except UnicodeDecodeError:
        return pl.read_csv(path, encoding="latin-1", **kwargs)


def read_source(path: Path) -> pl.DataFrame:
    if path.suffix.lower() == ".csv":
        return read_csv(path)
    if path.suffix.lower() == ".json":
        with path.open("r", encoding="utf-8") as file:
            return pl.from_dicts(json.load(file))
    if path.suffix.lower() == ".xlsx":
        return pl.from_pandas(pd.read_excel(path, dtype=str))
    raise ValueError(f"Formato não suportado: {path}")


def numeric_text(value: object) -> str:
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return ""
    text = re.sub(r"[R$€£\s]", "", text)
    if text.count(",") == 1 and text.count(".") > 1:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text and "." not in text:
        text = text.replace(",", ".")
    return text


def convert_column(series: pl.Series) -> tuple[pl.Series, int]:
    cleaned = series.map_elements(numeric_text, return_dtype=pl.String)
    converted = cleaned.cast(pl.Float64, strict=False)
    nonempty = cleaned.filter(cleaned != "").len()
    failed = nonempty - converted.drop_nulls().len()
    return converted, failed


def is_excluded(name: str) -> bool:
    normalized = name.lower()
    return (
        normalized.startswith("id_")
        or normalized in {"cpf_cnpj", "cep"}
        or normalized.endswith("_id")
    )


def select_numeric(df: pl.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    columns: dict[str, pl.Series] = {}
    conversion_failures: dict[str, int] = {}
    for name in df.columns:
        if is_excluded(name):
            continue
        converted, failed = convert_column(df[name])
        valid = converted.drop_nulls().len()
        nonempty = df[name].drop_nulls().len()
        if valid and (not nonempty or valid / nonempty >= 0.5):
            columns[name] = converted
            conversion_failures[name] = failed
    if not columns:
        return pd.DataFrame(), conversion_failures
    return pl.DataFrame(columns).to_pandas(), conversion_failures

# %%

def heatmap(matrix: pd.DataFrame, source: str, method: str, rows: int) -> str:
    safe_source = re.sub(r"[^a-z0-9]+", "_", source.lower()).strip("_")
    output = GRAPHICS_DIR / f"correlacao_{safe_source}_{method.lower()}.png"
    size = max(5.5, min(14, 1.2 * len(matrix.columns)))
    fig, ax = plt.subplots(figsize=(size, size * 0.8))
    image = ax.imshow(matrix.to_numpy(), cmap="coolwarm", vmin=-1, vmax=1)
    ax.set_xticks(range(len(matrix.columns)), matrix.columns, rotation=45, ha="right")
    ax.set_yticks(range(len(matrix.index)), matrix.index)
    ax.set_title(f"{source} — correlação {method} (n={rows:,})".replace(",", "."))
    for row in range(len(matrix.index)):
        for col in range(len(matrix.columns)):
            value = matrix.iloc[row, col]
            if pd.notna(value):
                ax.text(col, row, f"{value:.2f}", ha="center", va="center", fontsize=8)
    fig.colorbar(image, ax=ax, label="Correlação (-1 a 1)")
    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)
    return str(output.relative_to(ROOT))

# %%

def source_files() -> dict[str, list[Path]]:
    files = {
        "unidades_consumidoras": [resolve_data_file("unidades_consumidoras.csv", ROOT)],
        "medidores": [resolve_data_file("medidores.csv", ROOT)],
        "faturas": [resolve_data_file("faturas.csv", ROOT)],
        "geracao_distribuida": [resolve_data_file("geracao_distribuida.csv", ROOT)],
        "ocorrencias_rede": [resolve_data_file("ocorrencias_rede.csv", ROOT)],
        "atendimentos": [resolve_data_file("atendimentos.json", ROOT)],
        "inspecoes": [resolve_data_file("inspecoes.xlsx", ROOT)],
        "leituras": resolve_readings_files(ROOT),
    }
    return {name: paths for name, paths in files.items() if all(path.exists() for path in paths)}

# %% [markdown]
# ## Execução

# %%

def main() -> None:
    report: dict[str, object] = {"fontes": {}, "pngs": []}
    for source, paths in source_files().items():
        frames = [read_source(path) for path in paths]
        df = pl.concat(frames, how="diagonal_relaxed") if len(frames) > 1 else frames[0]
        numeric, failures = select_numeric(df)
        if numeric.shape[1] < 2:
            print(f"{source}: menos de duas variáveis numéricas; ignorada")
            continue
        pearson = numeric.corr(method="pearson")
        spearman = numeric.corr(method="spearman")
        rows = int(numeric.dropna(how="all").shape[0])
        pngs = [
            heatmap(pearson, source, "Pearson", rows),
            heatmap(spearman, source, "Spearman", rows),
        ]
        report["fontes"][source] = {
            "linhas_fonte": df.height,
            "linhas_usadas": rows,
            "variaveis": list(numeric.columns),
            "valores_nao_convertidos": failures,
            "pearson": pearson.round(8).where(pd.notna(pearson), None).to_dict(),
            "spearman": spearman.round(8).where(pd.notna(spearman), None).to_dict(),
            "pngs": pngs,
        }
        report["pngs"].extend(pngs)
        print(f"{source}: {rows} linhas, {len(numeric.columns)} variáveis, {', '.join(pngs)}")
    output = RESULTS_DIR / "correlacoes.json"
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Salvo em: {output}")
    print(f"PNG(s) gerado(s): {len(report['pngs'])}")


if __name__ == "__main__":
    main()
