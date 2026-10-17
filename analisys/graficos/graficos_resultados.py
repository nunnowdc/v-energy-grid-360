# %% [markdown]
# # Gráficos: profiling, integridade e summary

# %%
import json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

root = Path.cwd()
while not (root / 'data').exists() and root != root.parent:
    root = root.parent
if not (root / 'data').exists():
    raise FileNotFoundError(f"Pasta 'data' não encontrada subindo a partir de {Path.cwd()}")

expl = root / 'analisys'
out = expl / 'graficos' / 'resultados'
out.mkdir(parents=True, exist_ok=True)

def find_json(*patterns):
    for p in patterns:
        hits = sorted(expl.rglob(p))
        if hits:
            print("Usando:", hits[0])
            return hits[0]
    print("NÃO ENCONTRADO:", patterns)
    return None

def load(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)

def save(nome):
    plt.tight_layout()
    plt.savefig(out / nome, dpi=150)
    plt.show()

p_perfil = find_json('perfil_bruto.json', '*profil*.json', '*perfil*.json')
p_integr = find_json('*integr*.json')
p_resumo = find_json('summary_data.json')
p_corr = find_json('correlacoes.json', '*correl*.json')

# %% [markdown]
# ## 1. Profiling

# %%
if p_perfil:
    perfil = {k: v for k, v in load(p_perfil).items() if isinstance(v, dict) and 'columns' in v}
    quebradas = [k for k, v in perfil.items() if len(v['columns']) == 1]
    parcial = ['Leituras'] if 'Leituras' in perfil else []
    if quebradas:
        print("AVISO: fontes lidas com separador errado (1 coluna):", quebradas)
    if parcial:
        print("AVISO: Leituras tem colunas perfiladas só do 1º arquivo; só 'rows' é total.")

    # 1.1 Linhas por fonte
    nomes = sorted(perfil, key=lambda n: perfil[n]['rows'])
    linhas = [perfil[n]['rows'] for n in nomes]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.barh(nomes, linhas)
    ax.set_xscale('log')
    for i, v in enumerate(linhas):
        ax.text(v, i, f" {v:,}".replace(',', '.'), va='center')
    ax.set_title('Nº de linhas por fonte (escala log)')
    ax.set_xlabel('Linhas')
    save('perfil_linhas.png')

    # 1.2 % de linhas duplicadas
    dup = {n: perfil[n]['duplicates'] / perfil[n]['rows'] * 100 for n in perfil}
    nomes = sorted(dup, key=dup.get)
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.barh(nomes, [dup[n] for n in nomes])
    for i, n in enumerate(nomes):
        ax.text(dup[n], i, f" {dup[n]:.2f}%", va='center')
    ax.set_title('% de linhas duplicadas por fonte (Leituras: só 2022)')
    ax.set_xlabel('% das linhas')
    save('perfil_duplicatas.png')

    # 1.3 Nulos por coluna (só colunas com nulo > 0)
    nulos = []
    for n, v in perfil.items():
        if n in quebradas:
            continue
        for col, d in v['columns'].items():
            if d['null_pct'] > 0:
                nulos.append((f"{n}.{col}", d['null_pct']))
    nulos.sort(key=lambda x: x[1])
    if nulos:
        fig, ax = plt.subplots(figsize=(9, max(3, 0.3 * len(nulos))))
        ax.barh([x[0] for x in nulos], [x[1] for x in nulos])
        for i, (_, p) in enumerate(nulos):
            ax.text(p, i, f" {p:.2f}%", va='center')
        ax.set_title('% de nulos por coluna (só colunas com nulo)')
        ax.set_xlabel('% de nulos')
        save('perfil_nulos.png')

    # 1.4 Unicidade da 1ª coluna (chave candidata)
    uni = []
    for n, v in perfil.items():
        if n in quebradas or n in parcial:
            continue
        col = next(iter(v['columns']))
        uni.append((f"{n}.{col}", v['columns'][col]['distinct'] / v['rows'] * 100))
    uni.sort(key=lambda x: x[1])
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.barh([x[0] for x in uni], [x[1] for x in uni])
    for i, (_, p) in enumerate(uni):
        ax.text(p, i, f" {p:.1f}%", va='center')
    ax.set_xlim(0, 105)
    ax.set_title('Unicidade da chave candidata (distintos / linhas)')
    ax.set_xlabel('%  (100% = sem repetição)')
    save('perfil_unicidade.png')

    # 1.5 Tipos de coluna por fonte
    def tipo(t):
        if t.startswith('List'): return 'List'
        if t in ('String', 'Int64', 'Float64'): return t
        return 'Outro'
    cats = ['String', 'Int64', 'Float64', 'List', 'Outro']
    fontes = [n for n in perfil if n not in quebradas]
    cont = {c: [sum(1 for d in perfil[n]['columns'].values() if tipo(d['type']) == c)
                for n in fontes] for c in cats}
    fig, ax = plt.subplots(figsize=(9, 4))
    base = [0] * len(fontes)
    for c in cats:
        ax.bar(fontes, cont[c], bottom=base, label=c)
        base = [b + x for b, x in zip(base, cont[c])]
    ax.set_title('Tipos de coluna inferidos por fonte (muito String = datas/valores a converter)')
    ax.set_ylabel('Nº de colunas')
    ax.legend()
    plt.xticks(rotation=30, ha='right')
    save('perfil_tipos.png')

# %% [markdown]
# ## 2. Integridade

# %%
if p_integr:
    integ = {k: v for k, v in load(p_integr).items() if isinstance(v, dict)}
    rel = sorted(integ, key=lambda k: integ[k]['orphans_pct'])
    fig, ax = plt.subplots(figsize=(9, max(3, 0.5 * len(rel))))
    ax.barh(rel, [integ[k]['orphans_pct'] for k in rel])
    for i, k in enumerate(rel):
        d = integ[k]
        ax.text(d['orphans_pct'], i,
                f" {d['orphans_pct']:.1f}% ({d['orphans_count']:,} de {d['total_child_keys']:,})".replace(',', '.'),
                va='center')
    ax.set_title('Chaves órfãs por relacionamento (filho sem pai)')
    ax.set_xlabel('% de chaves distintas do filho sem correspondência')
    ax.set_xlim(0, max(10, max(integ[k]['orphans_pct'] for k in rel) * 1.4))
    save('integridade_orfaos.png')

# %% [markdown]
# ## 3. Summary

# %%
def pares(lst, top=15):
    if not lst:
        return [], []
    ks = list(lst[0].keys())
    cnt = 'count' if 'count' in ks else ks[-1]
    cat = [k for k in ks if k != cnt][0]
    ps = sorted(((str(d[cat]), d[cnt]) for d in lst), key=lambda x: x[1], reverse=True)
    if len(ps) > top:
        outros = sum(c for _, c in ps[top:])
        ps = ps[:top] + [('outros', outros)]
    return [p[0] for p in ps], [p[1] for p in ps]

def barra(lst, titulo, arquivo, top=15):
    nomes, vals = pares(lst, top)
    if not nomes:
        print("Sem dados:", titulo)
        return
    fig, ax = plt.subplots(figsize=(8, max(3, 0.35 * len(nomes))))
    ax.barh(nomes[::-1], vals[::-1])
    ax.set_title(titulo)
    ax.set_xlabel('Quantidade')
    save(arquivo)

if p_resumo:
    resumo = load(p_resumo)
    c = resumo.get('cadastro', {})
    k = resumo.get('consumo', {})
    r = resumo.get('rede', {})

    barra(c.get('classe', []), 'UCs por classe (grafias diferentes aparecem separadas)', 'sum_classe.png', top=20)
    barra(c.get('municipio', []), 'UCs por município', 'sum_municipio.png')
    barra(c.get('bairro', []), 'UCs por bairro (top 15)', 'sum_bairro.png')
    barra(c.get('med_types', []), 'Medidores por tipo', 'sum_medidor_tipo.png')
    barra(c.get('alim', []), 'UCs por alimentador (top 15)', 'sum_alimentador.png')
    barra(k.get('bandeiras', []), 'Faturas por bandeira tarifária', 'sum_bandeiras.png')
    barra(k.get('pagamentos', []), 'Faturas por status de pagamento', 'sum_pagamentos.png')
    barra(r.get('oco_tipo', []), 'Ocorrências por tipo', 'sum_oco_tipo.png')
    barra(r.get('oco_alim', []), 'Ocorrências por alimentador (top 15)', 'sum_oco_alimentador.png')
    barra(r.get('ins_res', []), 'Inspeções por resultado', 'sum_inspecoes.png')

    ev = k.get('evolucao', [])
    if ev:
        ev = sorted(ev, key=lambda d: str(d['mes_referencia']))
        meses = [str(d['mes_referencia']) for d in ev]
        fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
        campos = [('n_leituras', 'Nº de leituras'),
                  ('consumo_total', 'Consumo total (kWh)'),
                  ('n_ucs', 'UCs com leitura')]
        for ax, (campo, rot) in zip(axes, campos):
            ax.plot(range(len(meses)), [d[campo] for d in ev], marker='o')
            ax.set_ylabel(rot)
        axes[0].set_title('Evolução mensal das leituras (descritivo)')
        passo = max(1, len(meses) // 12)
        axes[-1].set_xticks(range(0, len(meses), passo))
        axes[-1].set_xticklabels(meses[::passo], rotation=45, ha='right')
        axes[-1].set_xlabel('Mês de referência')
        save('sum_evolucao_leituras.png')

# %% [markdown]
# ## 4. Correlações

# %%
if p_corr:
    correlacoes = load(p_corr)
    for fonte, dados in correlacoes.get('fontes', {}).items():
        for metodo in ('pearson', 'spearman'):
            matriz = dados.get(metodo)
            if not matriz:
                continue
            nomes = list(matriz)
            valores = np.array([
                [matriz[linha].get(coluna, np.nan) for coluna in nomes]
                for linha in nomes
            ], dtype=float)
            fig, ax = plt.subplots(figsize=(max(5.5, 1.2 * len(nomes)), 4.5))
            imagem = ax.imshow(valores, cmap='coolwarm', vmin=-1, vmax=1)
            ax.set_xticks(range(len(nomes)), nomes, rotation=45, ha='right')
            ax.set_yticks(range(len(nomes)), nomes)
            ax.set_title(f'{fonte} — correlação {metodo.title()} (n={dados["linhas_usadas"]:,})'
                         .replace(',', '.'))
            for i in range(len(nomes)):
                for j in range(len(nomes)):
                    if not np.isnan(valores[i, j]):
                        ax.text(j, i, f'{valores[i, j]:.2f}',
                                ha='center', va='center', fontsize=8)
            fig.colorbar(imagem, ax=ax, label='Correlação (-1 a 1)')
            save(f'correlacao_{fonte}_{metodo}.png')

print('Plotagens geradas com sucesso.')