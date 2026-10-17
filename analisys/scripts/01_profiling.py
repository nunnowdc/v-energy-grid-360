# %% [markdown]
# # Passo 1 — Profiling das bases V-Energy

# %%
import json
from pathlib import Path
import pandas as pd
import polars as pl

root = Path.cwd()
while not (root / 'data').exists() and root != root.parent:
    root = root.parent
if not (root / 'data').exists():
    raise FileNotFoundError(f"Pasta 'data' não encontrada subindo a partir de {Path.cwd()}")
data_dir = root / 'data'
res_dir = root / 'analisys' / 'resultados'
res_dir.mkdir(parents=True, exist_ok=True)
print("Usando:", data_dir)

# %%
def detectar_sep(path):
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        linha = f.readline()
    return ';' if linha.count(';') > linha.count(',') else ','

def ler_csv(path):
    sep = detectar_sep(path)
    try:
        df = pl.read_csv(path, separator=sep, infer_schema_length=0, truncate_ragged_lines=True)
        enc = 'utf8'
    except Exception:
        df = pl.read_csv(path, separator=sep, infer_schema_length=0, truncate_ragged_lines=True, encoding='latin-1')
        enc = 'latin-1'
    return df, sep, enc

def perfilar_coluna(s):
    n = s.len()
    d = {"tipo_lido": str(s.dtype), "type": str(s.dtype),
         "null_pct": float(s.null_count() / n * 100) if n else 0.0}
    try:
        d["distinct"] = int(s.n_unique())
    except Exception:
        d["distinct"] = None
    if s.dtype == pl.String:
        nn = s.drop_nulls()
        if nn.len():
            num = nn.str.strip_chars().cast(pl.Float64, strict=False)
            ok = num.drop_nulls()
            d["numerico_pct"] = float(ok.len() / nn.len() * 100)
            d["exemplos"] = nn.head(3).to_list()
            if ok.len():
                d["min"], d["max"] = float(ok.min()), float(ok.max())
                if ok.len() == nn.len():
                    d["type"] = "Int64" if bool((ok % 1 == 0).all()) else "Float64"
                else:
                    d["exemplos_nao_numericos"] = nn.filter(num.is_null()).head(5).to_list()
    elif s.dtype.is_numeric() or s.dtype in (pl.Date, pl.Datetime):
        d["min"], d["max"] = str(s.min()), str(s.max())
    return d

def perfilar_df(df):
    n = df.height
    str_cols = [c for c in df.columns if df[c].dtype == pl.String]
    rep = df.filter(pl.any_horizontal([pl.col(c) == pl.lit(c) for c in str_cols])).height if str_cols else 0
    return {"rows": n, "cols": df.width,
            "duplicates": n - df.unique().height,
            "linhas_cabecalho_repetido": int(rep),
            "columns": {c: perfilar_coluna(df[c]) for c in df.columns}}

def carregar(nome):
    path = data_dir / nome
    if nome.endswith('.csv'):
        df, sep, enc = ler_csv(path)
        return df, {"separador": sep, "encoding": enc}
    if nome.endswith('.json'):
        with open(path, 'r', encoding='utf-8') as f:
            return pl.DataFrame(json.load(f)), {}
    if nome.endswith('.xlsx'):
        return pl.from_pandas(pd.read_excel(path)), {}
    raise ValueError(f"Formato não suportado: {nome}")

# %%
fontes = [
    ('unidades_consumidoras.csv', 'UCs'),
    ('medidores.csv', 'Medidores'),
    ('faturas.csv', 'Faturas'),
    ('geracao_distribuida.csv', 'GD'),
    ('ocorrencias_rede.csv', 'Ocorrencias'),
    ('atendimentos.json', 'Atendimentos'),
    ('inspecoes.xlsx', 'Inspecoes'),
]
faltando = [n for n, _ in fontes if not (data_dir / n).exists()]
arqs = sorted((data_dir / 'leituras').glob('*.csv'))
if faltando or not arqs:
    raise FileNotFoundError(f"Arquivos faltando: {faltando}; leituras encontradas: {len(arqs)}")

resultados = {}
for nome, rotulo in fontes:
    print(f"Profiling {rotulo}...")
    try:
        df, meta = carregar(nome)
        resultados[rotulo] = {**meta, **perfilar_df(df)}
    except Exception as e:
        resultados[rotulo] = f"Error: {type(e).__name__}: {e}"

# %% [markdown]
# ## Leituras: cada ano separado + comparação de layout

# %%
layouts, total, meses = {}, 0, set()
for f in arqs:
    rot = f"Leituras_{f.stem.split('_')[-1]}"
    print(f"Profiling {rot}...")
    df, sep, enc = ler_csv(f)
    resultados[rot] = {"separador": sep, "encoding": enc, **perfilar_df(df)}
    layouts[rot] = df.columns
    total += df.height
    if 'mes_referencia' in df.columns:
        meses.update(df['mes_referencia'].drop_nulls().unique().to_list())

base = next(iter(layouts.values()))
resultados['Leituras_total'] = {
    "rows": total, "arquivos": len(arqs), "meses_distintos": len(meses),
    "mes_min": min(meses) if meses else None, "mes_max": max(meses) if meses else None,
    "layout_igual_entre_anos": all(c == base for c in layouts.values()),
    "colunas_diferentes": {k: v for k, v in layouts.items() if v != base},
}

# %%
with open(res_dir / 'perfil_bruto.json', 'w', encoding='utf-8') as f:
    json.dump(resultados, f, indent=2, ensure_ascii=False, default=str)
print("Salvo em:", res_dir / 'perfil_bruto.json')
print(json.dumps(resultados['Leituras_total'], indent=2, ensure_ascii=False))