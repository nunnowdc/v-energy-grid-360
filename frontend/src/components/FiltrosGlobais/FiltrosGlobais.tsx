import { X } from 'lucide-react'
import EstadoConsulta from '@/components/EstadoConsulta/EstadoConsulta'
import FiltroSelect from '@/components/FiltroSelect/FiltroSelect'
import SeletorPeriodo from '@/components/SeletorPeriodo/SeletorPeriodo'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { rotuloCausa } from '@/config/causas'
import { classesConsumo } from '@/config/classes'
import { useFiltros } from '@/hooks/use-filtros'
import { useOpcoesFiltros } from '@/hooks/use-opcoes-filtros'
import { periodoEscolhido, periodosDaReceita } from '@/lib/filtros-url'
import {
  atalhosDaBase,
  atalhosDoComparado,
  atalhosDoPeriodo,
  basePadrao,
  baseValida,
  comparadoPadrao,
  comparadoValido,
  periodoComAnterior,
  periodoPadrao,
  tamanhoDoPeriodo,
  type Periodo,
} from '@/lib/periodos'

// "periodo": um período comparado com o anterior, de mesmo tamanho (Indicadores e Continuidade).
// "comparacao": período base e período comparado da Receita
export type CampoFiltro = 'periodo' | 'comparacao' | 'municipio' | 'bairro' | 'classe' | 'alimentador' | 'causa'

const iguais = (a?: Periodo, b?: Periodo) => a?.de === b?.de && a?.ate === b?.ate

// Larguras fixas: escolher outro valor não muda o tamanho nem a posição dos filtros.
// Cabem os valores mais comuns; um valor maior é cortado com "…". No celular, cada filtro ocupa a linha toda
const larguras: Record<CampoFiltro, string> = {
  periodo: 'sm:w-64',
  comparacao: 'sm:w-72',
  municipio: 'sm:w-64',
  bairro: 'sm:w-56',
  classe: 'sm:w-64',
  alimentador: 'sm:w-56',
  causa: 'sm:w-60',
}

type FiltrosGlobaisProps = {
  // Quais filtros a tela usa, na ordem em que aparecem
  campos: CampoFiltro[]
}

// Barra de filtros das telas. Cada mudança vai para a URL e já é aplicada
function FiltrosGlobais({ campos }: FiltrosGlobaisProps) {
  const opcoes = useOpcoesFiltros()
  const { filtros, temFiltro, alterarFiltro, alterarFiltros, limparFiltros } = useFiltros()

  return (
    <EstadoConsulta consulta={opcoes} esqueleto={<Skeleton className="h-9 w-full max-w-md" />}>
      {(dados) => {
        const bairros =
          dados.municipios.find((municipio) => municipio.nome === filtros.municipio)?.bairros ?? []
        // Com município escolhido, só os alimentadores que atendem esse município
        const alimentadores = dados.alimentadores.filter(
          ({ municipios }) => !filtros.municipio || municipios.includes(filtros.municipio),
        )
        const { competencias } = dados
        const periodo = periodoEscolhido(competencias, filtros)
        const receita = periodosDaReceita(competencias, filtros)

        // O padrão não vai para a URL: escolher os últimos 12 meses limpa o filtro
        function mudarPeriodo(novo: Periodo) {
          const padrao = iguais(novo, periodoPadrao(competencias))
          alterarFiltros({ de: padrao ? undefined : novo.de, ate: padrao ? undefined : novo.ate })
        }

        // O comparado escolhido fica (com o tamanho do novo base) se ainda couber; senão, volta ao padrão
        function mudarBase(novo: Periodo) {
          const padrao = iguais(novo, basePadrao(competencias))
          const comparado = filtros.comparado_de
          alterarFiltros({
            base_de: padrao ? undefined : novo.de,
            base_ate: padrao ? undefined : novo.ate,
            comparado_de: comparado && comparadoValido(competencias, novo, comparado) ? comparado : undefined,
          })
        }

        function mudarComparado(novo: Periodo) {
          const padrao = iguais(novo, comparadoPadrao(competencias, receita!.base))
          alterarFiltro('comparado_de', padrao ? undefined : novo.de)
        }

        return (
          <div className="flex flex-wrap items-center gap-2">
            {campos.includes('periodo') && periodo && (
              <SeletorPeriodo
                rotulo="Período"
                competencias={competencias}
                valor={periodo}
                valido={(escolhido) => periodoComAnterior(competencias, escolhido)}
                atalhos={atalhosDoPeriodo(competencias)}
                className={larguras.periodo}
                aoMudar={mudarPeriodo}
              />
            )}
            {campos.includes('comparacao') && receita && (
              <>
                <SeletorPeriodo
                  rotulo="Período base"
                  competencias={competencias}
                  valor={receita.base}
                  valido={(escolhido) => baseValida(competencias, escolhido)}
                  atalhos={atalhosDaBase(competencias)}
                  className={larguras.comparacao}
                  aoMudar={mudarBase}
                />
                <SeletorPeriodo
                  rotulo="Comparado com"
                  competencias={competencias}
                  valor={receita.comparado}
                  valido={(escolhido) => comparadoValido(competencias, receita.base, escolhido.de)}
                  tamanhoFixo={tamanhoDoPeriodo(competencias, receita.base)}
                  atalhos={atalhosDoComparado(competencias, receita.base)}
                  tituloAtalhos="Mesmos meses do ano"
                  className={larguras.comparacao}
                  aoMudar={mudarComparado}
                />
              </>
            )}
            {campos.includes('municipio') && (
              <FiltroSelect
                rotulo="Município"
                valor={filtros.municipio}
                opcoes={dados.municipios.map(({ nome }) => ({ valor: nome, rotulo: nome }))}
                textoVazio="Todos"
                className={larguras.municipio}
                aoMudar={(valor) => alterarFiltro('municipio', valor)}
              />
            )}
            {campos.includes('bairro') && (
              <FiltroSelect
                rotulo="Bairro"
                valor={filtros.bairro}
                opcoes={bairros.map((bairro) => ({ valor: bairro, rotulo: bairro }))}
                textoVazio={filtros.municipio ? 'Todos' : 'Escolha um município'}
                desabilitado={!filtros.municipio}
                className={larguras.bairro}
                aoMudar={(valor) => alterarFiltro('bairro', valor)}
              />
            )}
            {campos.includes('classe') && (
              <FiltroSelect
                rotulo="Classe de consumo"
                valor={filtros.classe}
                opcoes={dados.classes.map((classe) => ({
                  valor: classe,
                  rotulo: classesConsumo[classe].label,
                }))}
                textoVazio="Todas"
                className={larguras.classe}
                aoMudar={(valor) => alterarFiltro('classe', valor)}
              />
            )}
            {campos.includes('alimentador') && (
              <FiltroSelect
                rotulo="Alimentador"
                valor={filtros.alimentador}
                opcoes={alimentadores.map(({ codigo }) => ({ valor: codigo, rotulo: codigo }))}
                textoVazio="Todos"
                className={larguras.alimentador}
                aoMudar={(valor) => alterarFiltro('alimentador', valor)}
              />
            )}
            {campos.includes('causa') && (
              <FiltroSelect
                rotulo="Causa"
                valor={filtros.causa}
                opcoes={dados.causas.map((causa) => ({ valor: causa, rotulo: rotuloCausa(causa) }))}
                textoVazio="Todas"
                className={larguras.causa}
                aoMudar={(valor) => alterarFiltro('causa', valor)}
              />
            )}
            <Button variant="ghost" className="h-9" disabled={!temFiltro} onClick={limparFiltros}>
              <X />
              Limpar filtros
            </Button>
          </div>
        )
      }}
    </EstadoConsulta>
  )
}

export default FiltrosGlobais
