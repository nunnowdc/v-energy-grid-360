import { SearchX, UserRoundSearch } from 'lucide-react'
import { useState } from 'react'
import { useParams } from 'react-router'
import BuscaUc from '@/components/BuscaUc/BuscaUc'
import CabecalhoPagina from '@/components/CabecalhoPagina/CabecalhoPagina'
import ConsumoDozeMeses from '@/components/ConsumoDozeMeses/ConsumoDozeMeses'
import EstadoErro from '@/components/EstadoErro/EstadoErro'
import FaturasEmAberto from '@/components/FaturasEmAberto/FaturasEmAberto'
import HistoricosUc from '@/components/HistoricosUc/HistoricosUc'
import InsightIa from '@/components/InsightIa/InsightIa'
import ResumoUc from '@/components/ResumoUc/ResumoUc'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { ehIdUc, PAGINAS_INICIAIS, useUc360, type HistoricoUc } from '@/hooks/use-uc-360'
import { ErroApi } from '@/lib/api/erro-api'

function Aviso({ icone, titulo, texto }: { icone: typeof SearchX; titulo: string; texto: string }) {
  const Icone = icone
  return (
    <Card>
      <CardContent className="flex min-h-56 flex-col items-center justify-center gap-2 text-center">
        <Icone aria-hidden="true" className="size-8 text-muted-foreground" />
        <p className="font-medium">{titulo}</p>
        <p className="max-w-md text-sm text-muted-foreground">{texto}</p>
      </CardContent>
    </Card>
  )
}

// Esqueleto no formato da tela, enquanto a UC carrega
function EsqueletoUc() {
  return (
    <div aria-label="Carregando unidade consumidora" className="flex flex-col gap-4">
      <div className="grid gap-4 lg:grid-cols-4">
        <Skeleton className="h-40 lg:col-span-2" />
        <Skeleton className="h-40" />
        <Skeleton className="h-40" />
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <Skeleton className="h-80 lg:col-span-2" />
        <Skeleton className="h-80" />
      </div>
      <Skeleton className="h-96" />
    </div>
  )
}

function DadosUc({ idUc }: { idUc: string }) {
  const [paginas, setPaginas] = useState(PAGINAS_INICIAIS)
  const consulta = useUc360(idUc, paginas)

  if (!ehIdUc(idUc) || (consulta.error instanceof ErroApi && consulta.error.status === 404)) {
    return (
      <Aviso
        icone={SearchX}
        titulo="Unidade consumidora não encontrada"
        texto={`Não existe unidade consumidora com o ID ${idUc}. Confira o número e busque de novo.`}
      />
    )
  }

  if (consulta.isPending) {
    return <EsqueletoUc />
  }

  if (consulta.isError) {
    return (
      <Card>
        <CardContent>
          <EstadoErro mensagem={consulta.error.message} aoTentarDeNovo={() => consulta.refetch()} />
        </CardContent>
      </Card>
    )
  }

  const dados = consulta.data

  function mudarPagina(historico: HistoricoUc, pagina: number) {
    setPaginas((atuais) => ({ ...atuais, [historico]: pagina }))
  }

  return (
    <div className="flex flex-col gap-4">
      <ResumoUc dados={dados} />
      <InsightIa tela="visao_360_uc" entidadeId={idUc} descricao="Sobre esta unidade consumidora" />
      <div className="grid gap-4 lg:grid-cols-3">
        <ConsumoDozeMeses meses={dados.consumo_12m} className="lg:col-span-2" />
        <FaturasEmAberto dados={dados} />
      </div>
      <HistoricosUc
        historicos={dados.historicos}
        aoMudarPagina={mudarPagina}
        atualizando={consulta.isPlaceholderData}
      />
    </div>
  )
}

function Visao360Page() {
  const { idUc } = useParams()

  return (
    <section className="flex flex-col gap-6">
      {/* key: trocar de UC recomeça a busca e as páginas do zero */}
      <CabecalhoPagina acoes={<BuscaUc key={idUc} idAtual={idUc} />} />
      {idUc ? (
        <DadosUc key={idUc} idUc={idUc} />
      ) : (
        <Aviso
          icone={UserRoundSearch}
          titulo="Busque uma unidade consumidora"
          texto="Digite o ID completo da UC acima para ver cadastro, consumo, faturas, interrupções e chamados em uma única tela."
        />
      )}
    </section>
  )
}

export default Visao360Page
