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

type FiltrosGlobaisProps = {
  // Quais filtros a tela usa, na ordem em que aparecem
  campos: CampoFiltro[]
}

// Barra de filtros das telas. Cada mudança vai para a URL e já é aplicada
function FiltrosGlobais({ campos }: FiltrosGlobaisProps) {
  const opcoes = useOpcoesFiltros()
  const { filtros, temFiltro, alterarFiltro, limparFiltros } = useFiltros()

  return (
    <EstadoConsulta consulta={opcoes} esqueleto={<Skeleton className="h-14 w-full" />}>
      {(dados) => {
        const competencias = dados.competencias.map((competencia) => ({
          valor: competencia,
          rotulo: formatarCompetencia(competencia),
        }))
        const bairros =
          dados.municipios.find((municipio) => municipio.nome === filtros.municipio)?.bairros ?? []

        return (
          <div className="flex flex-wrap items-end gap-3">
            {campos.includes('periodo') && (
              <>
                <FiltroSelect
                  rotulo="De"
                  valor={filtros.inicio}
                  opcoes={competencias}
                  textoVazio="12 meses até o fim"
                  aoMudar={(valor) => alterarFiltro('inicio', valor)}
                />
                <FiltroSelect
                  rotulo="Até"
                  valor={filtros.fim}
                  opcoes={competencias}
                  textoVazio="Último mês da base"
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
                aoMudar={(valor) => alterarFiltro('classe', valor)}
              />
            )}
            <Button variant="ghost" size="sm" disabled={!temFiltro} onClick={limparFiltros}>
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
