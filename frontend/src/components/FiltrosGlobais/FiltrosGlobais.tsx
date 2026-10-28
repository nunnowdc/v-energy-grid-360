import { X } from 'lucide-react'
import EstadoConsulta from '@/components/EstadoConsulta/EstadoConsulta'
import FiltroSelect from '@/components/FiltroSelect/FiltroSelect'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { rotuloCausa } from '@/config/causas'
import { classesConsumo } from '@/config/classes'
import { useFiltros } from '@/hooks/use-filtros'
import { useOpcoesFiltros } from '@/hooks/use-opcoes-filtros'
import { MESES_PADRAO, mesesPeriodo } from '@/lib/filtros-url'

export type CampoFiltro = 'periodo' | 'municipio' | 'bairro' | 'classe' | 'alimentador' | 'causa'

// "Últimos 12 meses" é o padrão (sem parâmetro na URL); as outras janelas vêm depois
const opcoesPeriodo = mesesPeriodo
  .filter((meses) => meses !== MESES_PADRAO)
  .map((meses) => ({ valor: String(meses), rotulo: `Últimos ${meses} meses` }))

// Larguras fixas: escolher outro valor não muda o tamanho nem a posição dos filtros.
// Cabem os valores mais comuns; um valor maior é cortado com "…". No celular, cada filtro ocupa a linha toda
const larguras: Record<CampoFiltro, string> = {
  periodo: 'sm:w-56',
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
  const { filtros, temFiltro, alterarFiltro, limparFiltros } = useFiltros()

  return (
    <EstadoConsulta consulta={opcoes} esqueleto={<Skeleton className="h-9 w-full max-w-md" />}>
      {(dados) => {
        const bairros =
          dados.municipios.find((municipio) => municipio.nome === filtros.municipio)?.bairros ?? []
        // Com município escolhido, só os alimentadores que atendem esse município
        const alimentadores = dados.alimentadores.filter(
          ({ municipios }) => !filtros.municipio || municipios.includes(filtros.municipio),
        )

        return (
          <div className="flex flex-wrap items-center gap-2">
            {campos.includes('periodo') && (
              <FiltroSelect
                rotulo="Período"
                valor={filtros.meses ? String(filtros.meses) : undefined}
                opcoes={opcoesPeriodo}
                textoVazio={`Últimos ${MESES_PADRAO} meses`}
                className={larguras.periodo}
                aoMudar={(valor) => alterarFiltro('meses', valor)}
              />
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
