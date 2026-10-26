import { X } from 'lucide-react'
import EstadoConsulta from '@/components/EstadoConsulta/EstadoConsulta'
import FiltroSelect from '@/components/FiltroSelect/FiltroSelect'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { classesConsumo } from '@/config/classes'
import { useFiltros } from '@/hooks/use-filtros'
import { useOpcoesFiltros } from '@/hooks/use-opcoes-filtros'
import { formatarCompetencia } from '@/lib/formatacao'

export type CampoFiltro = 'periodo' | 'municipio' | 'bairro' | 'classe'

// Larguras fixas: escolher outro valor não muda o tamanho nem a posição dos filtros.
// Cabem os valores mais comuns; um valor maior é cortado com "…". No celular, cada filtro ocupa a linha toda
const larguras: Record<CampoFiltro, string> = {
  periodo: 'sm:w-52',
  municipio: 'sm:w-64',
  bairro: 'sm:w-56',
  classe: 'sm:w-64',
}

type FiltrosGlobaisProps = {
  // Quais filtros a tela usa, na ordem em que aparecem
  campos: CampoFiltro[]
}

// Barra de filtros das telas. Cada mudança vai para a URL e já é aplicada
function FiltrosGlobais({ campos }: FiltrosGlobaisProps) {
  const opcoes = useOpcoesFiltros()
  const { filtros, temFiltro, alterarFiltro, limparFiltros } = useFiltros()

  return (
    <EstadoConsulta consulta={opcoes} esqueleto={<Skeleton className="h-9 w-full max-w-md" />}>
      {(dados) => {
        const competencias = dados.competencias.map((competencia) => ({
          valor: competencia,
          rotulo: formatarCompetencia(competencia),
        }))
        const bairros =
          dados.municipios.find((municipio) => municipio.nome === filtros.municipio)?.bairros ?? []

        return (
          <div className="flex flex-wrap items-center gap-2">
            {campos.includes('periodo') && (
              <>
                <FiltroSelect
                  rotulo="De"
                  valor={filtros.inicio}
                  opcoes={competencias}
                  textoVazio="12 meses até o fim"
                  className={larguras.periodo}
                  aoMudar={(valor) => alterarFiltro('inicio', valor)}
                />
                <FiltroSelect
                  rotulo="Até"
                  valor={filtros.fim}
                  opcoes={competencias}
                  textoVazio="Último mês da base"
                  className={larguras.periodo}
                  aoMudar={(valor) => alterarFiltro('fim', valor)}
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
