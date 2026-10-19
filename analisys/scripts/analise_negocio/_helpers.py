"""Utilitários compartilhados para executar as análises em scripts e notebooks."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd


_REQUIRED_DATA_FILES = (
    "unidades_consumidoras.csv",
    "medidores.csv",
    "faturas.csv",
    "geracao_distribuida.csv",
    "ocorrencias_rede.csv",
    "atendimentos.json",
    "inspecoes.xlsx",
)


def _find_project_root(start: Path | None = None) -> Path:
    """Encontra a raiz pelo par ``data`` + ``analisys``, sem depender de __file__."""
    starts = []
    if start is not None:
        starts.append(Path(start))
    else:
        starts.append(Path.cwd())
        file_name = globals().get("__file__")
        if file_name:
            starts.append(Path(file_name).resolve().parent)

    checked: list[Path] = []
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

    locations = ", ".join(str(item.resolve()) for item in starts)
    raise FileNotFoundError(
        "Raiz do projeto não encontrada. Esperado um diretório contendo "
        f"'data/' e 'analisys/' a partir de: {locations}"
    )


def get_project_root(start: Path | None = None) -> Path:
    return _find_project_root(start)


def get_data_dir(root: Path | None = None) -> Path:
    data_dir = get_project_root(root) / "data"
    if not data_dir.is_dir():
        raise FileNotFoundError(f"Diretório de dados não encontrado: {data_dir}")
    return data_dir


def get_analisys_dir(root: Path | None = None) -> Path:
    return get_project_root(root) / "analisys"


def get_scripts_dir(root: Path | None = None) -> Path:
    return get_analisys_dir(root) / "scripts"


def get_resultados_dir(subdir: str | None = None, root: Path | None = None) -> Path:
    directory = get_analisys_dir(root) / "resultados"
    if subdir:
        directory /= subdir
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def get_graficos_dir(subdir: str | None = None, root: Path | None = None) -> Path:
    directory = get_analisys_dir(root) / "graficos"
    if subdir:
        directory /= subdir
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def add_project_root_to_path(root: Path | None = None) -> Path:
    project_root = get_project_root(root)
    value = str(project_root)
    if value not in sys.path:
        sys.path.insert(0, value)
    return project_root


def add_scripts_dir_to_path(root: Path | None = None) -> Path:
    scripts_dir = get_scripts_dir(root)
    value = str(scripts_dir)
    if value not in sys.path:
        sys.path.insert(0, value)
    return scripts_dir


def resolve_data_file(name: str, root: Path | None = None) -> Path:
    """Resolve um arquivo direto em data ou em subdiretórios, pelo nome."""
    data_dir = get_data_dir(root)
    direct = data_dir / name
    if direct.is_file():
        return direct
    matches = sorted(path for path in data_dir.rglob(Path(name).name) if path.is_file())
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise FileNotFoundError(
            f"Arquivo de dados obrigatório '{name}' não encontrado em {data_dir} "
            "nem em seus subdiretórios."
        )
    raise FileNotFoundError(
        f"Arquivo de dados '{name}' encontrado em múltiplos locais: "
        + ", ".join(str(path) for path in matches)
    )


def resolve_readings_files(root: Path | None = None) -> list[Path]:
    """Localiza CSVs de leituras em qualquer subdiretório de data."""
    data_dir = get_data_dir(root)
    candidates = sorted(
        path
        for path in data_dir.rglob("*.csv")
        if path.is_file() and "leitura" in path.stem.lower()
    )
    if not candidates:
        raise FileNotFoundError(
            f"Nenhum CSV de leituras encontrado em {data_dir} ou subdiretórios. "
            "Esperado ao menos um arquivo cujo nome contenha 'leitura'."
        )
    return candidates


def resolve_input_files(root: Path | None = None) -> dict[str, list[Path] | Path]:
    files: dict[str, list[Path] | Path] = {
        name.removesuffix(Path(name).suffix): resolve_data_file(name, root)
        for name in _REQUIRED_DATA_FILES
    }
    files["leituras"] = resolve_readings_files(root)
    return files


def _read_csv(path: Path, **kwargs: object) -> pd.DataFrame:
    sample = path.read_text(encoding="utf-8", errors="replace").splitlines()[:1]
    if not sample:
        raise ValueError(f"Arquivo CSV vazio: {path}")
    separator = ";" if sample[0].count(";") > sample[0].count(",") else ","
    options = {"sep": separator, **kwargs}
    try:
        return pd.read_csv(path, **options)
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="latin-1", **options)


def _read_file(path: Path, **kwargs: object) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return _read_csv(path, **kwargs)
    if suffix == ".json":
        return pd.read_json(path, **kwargs)
    if suffix == ".xlsx":
        return pd.read_excel(path, **kwargs)
    raise ValueError(f"Formato de dados não suportado: {path}")


def load_unidades_consumidoras(root: Path | None = None) -> pd.DataFrame:
    return _read_file(resolve_data_file("unidades_consumidoras.csv", root))


def load_faturas(root: Path | None = None) -> pd.DataFrame:
    return _read_file(resolve_data_file("faturas.csv", root))


def load_leituras(root: Path | None = None) -> pd.DataFrame:
    frames = [_read_file(path) for path in resolve_readings_files(root)]
    return pd.concat(frames, ignore_index=True, sort=False)


def load_medidores(root: Path | None = None) -> pd.DataFrame:
    return _read_file(resolve_data_file("medidores.csv", root))


def load_geracao_distribuida(root: Path | None = None) -> pd.DataFrame:
    return _read_file(resolve_data_file("geracao_distribuida.csv", root))


def load_ocorrencias_rede(root: Path | None = None) -> pd.DataFrame:
    return _read_file(resolve_data_file("ocorrencias_rede.csv", root))


def load_atendimentos(root: Path | None = None) -> pd.DataFrame:
    return _read_file(resolve_data_file("atendimentos.json", root))


def load_inspecoes(root: Path | None = None) -> pd.DataFrame:
    return _read_file(resolve_data_file("inspecoes.xlsx", root))


def load_all_raw_data(root: Path | None = None) -> dict[str, pd.DataFrame]:
    return {
        "uc": load_unidades_consumidoras(root),
        "faturas": load_faturas(root),
        "leituras": load_leituras(root),
        "medidores": load_medidores(root),
        "gd": load_geracao_distribuida(root),
        "ocorrencias": load_ocorrencias_rede(root),
        "atendimentos": load_atendimentos(root),
        "inspecoes": load_inspecoes(root),
    }


def to_numeric_safe(series: pd.Series, decimal_comma: bool = False) -> tuple[pd.Series, int]:
    values = series.astype("string").str.strip()
    if decimal_comma:
        values = values.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    converted = pd.to_numeric(values, errors="coerce")
    failures = int((values.notna() & values.ne("") & converted.isna()).sum())
    return converted, failures


def safe_divide(numerator: float, denominator: float) -> float | None:
    if denominator is None or pd.isna(denominator) or denominator == 0:
        return None
    return float(numerator / denominator)


def pct_change_safe(current: float | None, previous: float | None) -> float | None:
    if previous is None or pd.isna(previous) or previous == 0 or current is None or pd.isna(current):
        return None
    return float((current - previous) / previous * 100)


def setup_graficos(root: Path | None = None, salvar_graficos: bool = True) -> Path:
    return get_graficos_dir("analise_negocio" if salvar_graficos else None, root)


def init_notebook(
    root: Path | None = None, salvar_graficos: bool = True
) -> tuple[Path, Path, Path, Callable]:
    project_root = add_project_root_to_path(root)
    add_scripts_dir_to_path(project_root)
    data_dir = get_data_dir(project_root)
    graphics_dir = setup_graficos(project_root, salvar_graficos)

    def exibir_grafico(figure: object, nome: str) -> None:
        if salvar_graficos:
            output = graphics_dir / f"{nome}.png"
            figure.savefig(output, dpi=150, bbox_inches="tight")

    return project_root, data_dir, graphics_dir, exibir_grafico
