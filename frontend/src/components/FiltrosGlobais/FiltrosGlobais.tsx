import { X } from 'lucide-react'
import EstadoConsulta from '@/components/EstadoConsulta/EstadoConsulta'
import FiltroSelect from '@/components/FiltroSelect/FiltroSelect'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { rotuloCausa } from '@/config/causas'
import { classesConsumo } from '@/config/classes'
import { useFiltros } from '@/hooks/use-filtros'
import { useOpcoesFiltros } from '@/hooks/use-opcoes-filtros'
import { formatarCompetencia, formatarPeriodo } from '@/lib/formatacao'
import {
  anosDaBase,
  anosDaReceita,
  MESES_PADRAO,
  mesesFinais,
  mesesPeriodo,
  type AnoDaBase,
} from '@/lib/filtros-url'

// "ate" é o mês em que o período termina; "anos" são o ano base e o ano comparado da Receita
export type CampoFiltro = 'periodo' | 'ate' | 'anos' | 'municipio' | 'bairro' | 'classe' | 'alimentador' | 'causa'

// "Últimos 12 meses" é o padrão (sem parâmetro na URL); as outras janelas vêm depois
const opcoesPeriodo = mesesPeriodo
  .filter((meses) => meses !== MESES_PADRAO)
  .map((meses) => ({ valor: String(meses), rotulo: `Últimos ${meses} meses` }))

// Larguras fixas: escolher outro valor não muda o tamanho nem a posição dos filtros.
// Cabem os valores mais comuns; um valor maior é cortado com "…". No celular, cada filtro ocupa a linha toda
const larguras: Record<CampoFiltro, string> = {
  periodo: 'sm:w-56',
  ate: 'sm:w-36',
  anos: 'sm:w-72',
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
        // O último mês da base é o padrão de "Até"; os outros vêm do mais recente para o mais antigo
        const ultimoMes = dados.competencias.at(-1)
        const outrosFins = mesesFinais(dados.competencias, filtros.meses).slice(0, -1).reverse()
        // Cada lista só oferece os anos que deixam o comparado depois do base
        const anos = anosDaBase(dados.competencias)
        const emVigor = anosDaReceita(dados.competencias, filtros)
        const rotuloAno = (ano?: AnoDaBase) => (ano ? formatarPeriodo(ano.inicio, ano.fim) : '—')
        const opcaoAno = (ano: AnoDaBase) => ({ valor: ano.inicio, rotulo: rotuloAno(ano) })

        return (
          <div className="flex flex-wrap items-center gap-2">
            {campos.includes('periodo') && (
              <FiltroSelect
                rotulo="Período"
                // "meses=12" na URL é o mesmo que o padrão, que é a opção vazia
                valor={filtros.meses && filtros.meses !== MESES_PADRAO ? String(filtros.meses) : undefined}
                opcoes={opcoesPeriodo}
                textoVazio={`Últimos ${MESES_PADRAO} meses`}
                className={larguras.periodo}
                aoMudar={(valor) => alterarFiltro('meses', valor)}
              />
            )}
            {campos.includes('ate') && (
              <FiltroSelect
                rotulo="Até"
                valor={filtros.ate}
                opcoes={outrosFins.map((mes) => ({ valor: mes, rotulo: formatarCompetencia(mes) }))}
                textoVazio={ultimoMes ? formatarCompetencia(ultimoMes) : '—'}
                className={larguras.ate}
                aoMudar={(valor) => alterarFiltro('ate', valor)}
              />
            )}
            {campos.includes('anos') && (
              <>
                <FiltroSelect
                  rotulo="Período base"
                  valor={filtros.base}
                  opcoes={anos.slice(1).filter(({ inicio }) => inicio < emVigor.comparado!).map(opcaoAno)}
                  textoVazio={rotuloAno(anos[0])}
                  className={larguras.anos}
                  aoMudar={(valor) => alterarFiltro('base', valor)}
                />
                <FiltroSelect
                  rotulo="Comparado com"
                  valor={filtros.comparado}
                  opcoes={anos.slice(0, -1).filter(({ inicio }) => inicio > emVigor.base!).map(opcaoAno)}
                  textoVazio={rotuloAno(anos.at(-1))}
                  className={larguras.anos}
                  aoMudar={(valor) => alterarFiltro('comparado', valor)}
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
