# %% [markdown]
# # Passo 2 — Integridade entre tabelas

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

def ler(nome, cols):
    path = data_dir / nome
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")
    if nome.endswith('.csv'):
        sep = detectar_sep(path)
        try:
            return pl.read_csv(path, separator=sep, infer_schema_length=0, columns=cols, truncate_ragged_lines=True)
        except Exception:
            return pl.read_csv(path, separator=sep, infer_schema_length=0, columns=cols,
                               truncate_ragged_lines=True, encoding='latin-1')
    if nome.endswith('.json'):
        with open(path, 'r', encoding='utf-8') as f:
            return pl.DataFrame(json.load(f)).select(cols).cast(pl.String)
    if nome.endswith('.xlsx'):
        return pl.from_pandas(pd.read_excel(path, dtype=str)).select(cols).cast(pl.String)
    raise ValueError(nome)

uc  = ler('unidades_consumidoras.csv', ['id_uc'])
med = ler('medidores.csv', ['id_medidor', 'id_uc'])
fat = ler('faturas.csv', ['id_uc'])
gd  = ler('geracao_distribuida.csv', ['id_uc'])
oco = ler('ocorrencias_rede.csv', ['id_uc'])
ate = ler('atendimentos.json', ['id_uc'])
ins = ler('inspecoes.xlsx', ['id_uc'])
arqs = sorted((data_dir / 'leituras').glob('*.csv'))
if not arqs:
    raise FileNotFoundError("Nenhum arquivo em data/leituras")
leit = pl.concat([ler(f"leituras/{f.name}", ['id_uc', 'id_medidor']) for f in arqs])
print("Tabelas carregadas. Linhas de leituras:", leit.height)

# %%
def pct(a, b):
    return float(a / b * 100) if b else 0.0

def norm(s):
    s = s.cast(pl.String).str.strip_chars().str.to_uppercase()
    return s.filter(s.is_not_null() & (s != ''))

def medir(pai, cp, filho, cf):
    pk, fk = norm(pai[cp]), norm(filho[cf])
    pu, fu = set(pk.unique().to_list()), set(fk.unique().to_list())
    bruto_p = set(pai[cp].drop_nulls().unique().to_list())
    bruto_f = set(filho[cf].drop_nulls().unique().to_list())
    orf = fu - pu
    linhas_orf = (pl.DataFrame({'k': fk})
                  .join(pl.DataFrame({'k': pk.unique()}), on='k', how='anti').height)
    return {
        "total_child_keys": len(fu),
        "orphans_count": len(orf),
        "orphans_pct": pct(len(orf), len(fu)),                       # normalizado
        "orphans_pct_sem_normalizar": pct(len(bruto_f - bruto_p), len(bruto_f)),
        "linhas_filho": filho.height,
        "linhas_orfas": linhas_orf,
        "linhas_orfas_pct": pct(linhas_orf, fk.len()),
        "chaves_nulas_ou_vazias_filho": filho.height - fk.len(),
        "pai_linhas": pai.height,
        "pai_chaves_distintas": len(pu),
        "pai_sem_filho_count": len(pu - fu),
        "pai_sem_filho_pct": pct(len(pu - fu), len(pu)),
    }

relacoes = [
    ("UC -> Medidores",    uc,  'id_uc', med,  'id_uc'),
    ("UC -> Faturas",      uc,  'id_uc', fat,  'id_uc'),
    ("UC -> GD",           uc,  'id_uc', gd,   'id_uc'),
    ("UC -> Ocorrencias",  uc,  'id_uc', oco,  'id_uc'),
    ("UC -> Atendimentos", uc,  'id_uc', ate,  'id_uc'),
    ("UC -> Inspecoes",    uc,  'id_uc', ins,  'id_uc'),
    ("UC -> Leituras",     uc,  'id_uc', leit, 'id_uc'),
    ("Medidor -> Leituras", med, 'id_medidor', leit, 'id_medidor'),
]
integrity_results = {r[0]: medir(*r[1:]) for r in relacoes}

# %%
with open(res_dir / 'integridade.json', 'w', encoding='utf-8') as f:
    json.dump(integrity_results, f, indent=2, ensure_ascii=False, default=str)
print("Salvo em:", res_dir / 'integridade.json')
for k, v in integrity_results.items():
    print(f"{k}: órfãs {v['orphans_pct']:.2f}% (sem normalizar: {v['orphans_pct_sem_normalizar']:.2f}%) | "
          f"linhas órfãs {v['linhas_orfas_pct']:.2f}% | pai sem filho {v['pai_sem_filho_pct']:.2f}%")