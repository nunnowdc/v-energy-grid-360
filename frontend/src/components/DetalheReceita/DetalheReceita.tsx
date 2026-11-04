import { ChevronRight, RotateCcw } from 'lucide-react'
import TabelaDecomposicao from '@/components/TabelaDecomposicao/TabelaDecomposicao'
import { Button } from '@/components/ui/button'
import { classesConsumo, ehClasseConsumo } from '@/config/classes'
import { temDados, type DecomposicaoCompleta, type NivelDetalhe, type VariacaoReceita } from '@/hooks/use-receita'

const nomeColuna: Record<NivelDetalhe, string> = {
  municipio: 'Município',
  bairro: 'Bairro',
  classe: 'Classe de consumo',
}

// O que o clique numa linha faz em cada nível
const textoAcao: Record<NivelDetalhe, string> = {
  municipio: 'Ver bairros',
  bairro: 'Ver classes',
  classe: 'Só esta classe',
}

// Um passo da trilha "Todos os municípios › Olinda › Rio Doce"
export type PassoTrilha = {
  rotulo: string
  // Sem ação, é o passo atual
  aoClicar?: () => void
}

type DetalheReceitaProps = {
  detalhamento: VariacaoReceita['detalhamento']
  trilha: PassoTrilha[]
  // Sem ação, as linhas não são clicáveis (ex.: já está numa classe só)
  aoDescer?: (nome: string) => void
}

const textoDaLinha = (nivel: NivelDetalhe, nome: string) =>
  nivel === 'classe' && ehClasseConsumo(nome) ? classesConsumo[nome].label : nome

// Tabela de onde está a variação, da maior perda de volume para a menor.
// Clicar numa linha desce um nível (município › bairro › classe) e preenche o filtro
// do topo. A trilha e o "Voltar" ficam junto da tabela: não precisa subir até os filtros
function DetalheReceita({ detalhamento, trilha, aoDescer }: DetalheReceitaProps) {
  const { nivel } = detalhamento
  // Linha sem dados não entra (a Gold não costuma mandar, mas o formato permite)
  const ordenadas = detalhamento.linhas
    .filter((linha): linha is typeof linha & DecomposicaoCompleta => temDados(linha))
    .sort((a, b) => a.efeito_volume - b.efeito_volume)
  // O primeiro passo ("Todos os municípios") só tem ação quando já se desceu algum nível
  const voltarAoInicio = trilha[0]?.aoClicar

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-md bg-muted/70 px-3 py-1.5">
        <nav aria-label="Nível do detalhamento">
          <ol className="flex flex-wrap items-center gap-1 text-[13px]">
            {trilha.map(({ rotulo, aoClicar }, indice) => (
              <li key={rotulo} className="flex items-center gap-1">
                {indice > 0 && <ChevronRight aria-hidden="true" className="size-3.5 text-muted-foreground" />}
                {aoClicar ? (
                  <button
                    type="button"
                    onClick={aoClicar}
                    className="cursor-pointer font-medium text-primary hover:underline"
                  >
                    {rotulo}
                  </button>
                ) : (
                  <span aria-current="location" className="font-semibold">
                    {rotulo}
                  </span>
                )}
              </li>
            ))}
          </ol>
        </nav>
        {voltarAoInicio && (
          <Button variant="ghost" size="sm" className="h-7" onClick={voltarAoInicio}>
            <RotateCcw />
            Voltar a todos os municípios
          </Button>
        )}
      </div>
      <TabelaDecomposicao
        colunaRotulo={nomeColuna[nivel]}
        linhas={ordenadas.map((linha) => ({
          chave: linha.nome,
          rotulo: textoDaLinha(nivel, linha.nome),
          dados: linha,
        }))}
        aoClicar={aoDescer}
        textoAcao={textoAcao[nivel]}
      />
    </div>
  )
}

export default DetalheReceita
