# %% [markdown]
# # Passo 3 — Summary (contagens agregadas)

# %%
import json
import sys
from pathlib import Path
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
        get_analisys_dir,
        resolve_data_file,
        resolve_readings_files,
    )
except ModuleNotFoundError as error:
    if error.name != "analisys":
        raise
    from analise_negocio._helpers import (
        get_data_dir,
        get_analisys_dir,
        resolve_data_file,
        resolve_readings_files,
    )

data_dir = get_data_dir()
out_dir = get_analisys_dir()
out_dir.mkdir(parents=True, exist_ok=True)
print("Usando:", data_dir)

# %%
def detectar_sep(path):
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        linha = f.readline()
    return ';' if linha.count(';') > linha.count(',') else ','

def ler(nome, cols=None):
    path = resolve_data_file(nome)
    if nome.endswith('.xlsx'):
        return pl.from_pandas(pd.read_excel(path, dtype=str))
    sep = detectar_sep(path)
    kw = dict(separator=sep, infer_schema_length=0, columns=cols, truncate_ragged_lines=True)
    try:
        return pl.read_csv(path, **kw)
    except UnicodeDecodeError:
        return pl.read_csv(path, encoding='latin-1', **kw)

def vc(df, col):
    return df[col].value_counts(sort=True).to_dicts()

# %%
uc  = ler('unidades_consumidoras.csv', ['id_uc', 'classe', 'municipio', 'bairro', 'alimentador'])
med = ler('medidores.csv', ['id_medidor', 'tipo'])
fat = ler('faturas.csv', ['id_fatura', 'bandeira_tarifaria', 'status'])
oco = ler('ocorrencias_rede.csv', ['tipo', 'alimentador'])
ins = ler('inspecoes.xlsx')

arqs = resolve_readings_files()
leit = pl.concat(
    [ler(str(f), ['id_leitura', 'id_uc', 'mes_referencia', 'consumo_kwh']) for f in arqs],
    how="diagonal_relaxed")

consumo = pl.col('consumo_kwh').str.strip_chars().cast(pl.Float64, strict=False)
evolucao = (leit.group_by('mes_referencia')
            .agg([pl.len().alias('n_leituras'),
                  consumo.sum().alias('consumo_total'),
                  pl.col('id_uc').n_unique().alias('n_ucs')])
            .sort('mes_referencia').to_dicts())

qualidade = {
    "consumo_nao_numerico": leit.filter(pl.col('consumo_kwh').is_not_null() & consumo.is_null()).height,
    "faturas_cabecalho_repetido": fat.filter(
        (pl.col('status') == 'status') | (pl.col('bandeira_tarifaria') == 'bandeira_tarifaria')).height,
}

summary = {
    "cadastro": {"classe": vc(uc, 'classe'), "municipio": vc(uc, 'municipio'),
                 "bairro": vc(uc, 'bairro'), "med_types": vc(med, 'tipo'),
                 "alim": vc(uc, 'alimentador')},
    "consumo": {"evolucao": evolucao, "bandeiras": vc(fat, 'bandeira_tarifaria'),
                "pagamentos": vc(fat, 'status')},
    "rede": {"oco_tipo": vc(oco, 'tipo'), "oco_alim": vc(oco, 'alimentador'),
             "ins_res": vc(ins, 'resultado')},
    "qualidade": qualidade,
}

with open(out_dir / 'summary_data.json', 'w', encoding='utf-8') as f:
    json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
print("Salvo em:", out_dir / 'summary_data.json')
print(qualidade)