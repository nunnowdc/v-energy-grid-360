import { CircleCheck, Download, LoaderCircle } from 'lucide-react'
import { useState } from 'react'
import CabecalhoPagina from '@/components/CabecalhoPagina/CabecalhoPagina'
import CartaoKpi from '@/components/CartaoKpi/CartaoKpi'
import CartaoKpiEsqueleto from '@/components/CartaoKpi/CartaoKpiEsqueleto'
import EstadoConsulta from '@/components/EstadoConsulta/EstadoConsulta'
import FilaSuspeitas from '@/components/FilaSuspeitas/FilaSuspeitas'
import FiltrosGlobais from '@/components/FiltrosGlobais/FiltrosGlobais'
import OrdensInspecao from '@/components/OrdensInspecao/OrdensInspecao'
import Paginacao from '@/components/Paginacao/Paginacao'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useExportarFila, useFilaInspecao, type FilaInspecao } from '@/hooks/use-fila-inspecao'
import { useFiltros } from '@/hooks/use-filtros'
import { useGerarOrdens, useOrdensInspecao, type OrdemInspecao } from '@/hooks/use-ordens-inspecao'
import { ErroApi } from '@/lib/api/erro-api'
import type { Filtros } from '@/lib/filtros-url'
import { formatarEnergia, formatarNumero } from '@/lib/formatacao'

const plural = (quantidade: number, singular: string, varios: string) =>
  `${formatarNumero(quantidade)} ${quantidade === 1 ? singular : varios}`

// No 409 o backend não gera nenhuma ordem do lote e lista as UCs que já têm ordem aberta
const ucsComOrdem = (erro: Error): string[] =>
  erro instanceof ErroApi && erro.status === 409 ? (erro.message.match(/UC\d{6}/g) ?? []) : []

function textoErroGerar(erro: Error) {
  const comOrdem = ucsComOrdem(erro)
  if (comOrdem.length > 0) {
    const uma = comOrdem.length === 1
    return `Nenhuma ordem foi gerada: ${comOrdem.join(', ')} já ${uma ? 'tem' : 'têm'} ordem aberta e ${uma ? 'saiu' : 'saíram'} da seleção.`
  }
  return erro instanceof ErroApi ? erro.message : 'Não foi possível gerar as ordens. Tente de novo.'
}

function Kpis({ fila, ordens }: { fila: FilaInspecao; ordens: OrdemInspecao[] }) {
  const emAndamento = ordens.filter((ordem) => ordem.status === 'ABERTA' || ordem.status === 'EM_CAMPO').length
  const concluidas = ordens.filter((ordem) => ordem.status === 'CONCLUIDA')
  const confirmadas = concluidas.filter((ordem) => ordem.resultado === 'IRREGULARIDADE_CONFIRMADA').length

  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <CartaoKpi titulo="UCs na fila" valor={formatarNumero(fila.resumo.ucs)} detalhe="Score de 20 a 100" />
      <CartaoKpi
        titulo="Energia estimada a recuperar"
        valor={`${formatarEnergia(fila.resumo.kwh_recuperavel_estimado_ano)}/ano`}
        detalhe="Soma da fila"
      />
      <CartaoKpi titulo="Ordens em andamento" valor={formatarNumero(emAndamento)} detalhe="Abertas e em campo" />
      <CartaoKpi
        titulo="Acerto das inspeções"
        valor={concluidas.length === 0 ? '—' : `${formatarNumero((confirmadas / concluidas.length) * 100)}%`}
        detalhe={
          concluidas.length === 0
            ? 'Nenhuma ordem concluída ainda'
            : `${confirmadas} de ${plural(concluidas.length, 'concluída', 'concluídas')} com irregularidade`
        }
      />
    </div>
  )
}

function KpisEsqueleto() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {Array.from({ length: 4 }, (_, indice) => (
        <CartaoKpiEsqueleto key={indice} />
      ))}
    </div>
  )
}

// Tudo o que depende dos filtros. Recomeça (página 1, nada selecionado) quando eles mudam
function ConteudoInspecoes({ filtros }: { filtros: Filtros }) {
  const [pagina, setPagina] = useState(1)
  const [selecionadas, setSelecionadas] = useState<Set<string>>(new Set())
  const [aviso, setAviso] = useState<string>()
  const fila = useFilaInspecao(filtros, pagina)
  const ordens = useOrdensInspecao(filtros)
  const gerar = useGerarOrdens()
  const exportar = useExportarFila(filtros)

  function marcar(idUc: string, marcada: boolean) {
    setAviso(undefined)
    setSelecionadas((atual) => {
      const proxima = new Set(atual)
      if (marcada) {
        proxima.add(idUc)
      } else {
        proxima.delete(idUc)
      }
      return proxima
    })
  }

  function gerarOrdens() {
    gerar.mutate([...selecionadas], {
      onSuccess: ({ ordens: novas }) => {
        setSelecionadas(new Set())
        setAviso(`${plural(novas.length, 'ordem de inspeção gerada', 'ordens de inspeção geradas')}.`)
      },
      // Quem já tem ordem sai da seleção; as outras ficam marcadas para gerar de novo
      onError: (erro) => {
        const comOrdem = ucsComOrdem(erro)
        setSelecionadas((atual) => new Set([...atual].filter((idUc) => !comOrdem.includes(idUc))))
      },
    })
  }

  return (
    <>
      <EstadoConsulta consulta={fila} esqueleto={<KpisEsqueleto />}>
        {(dados) => <Kpis fila={dados} ordens={ordens.data?.itens ?? []} />}
      </EstadoConsulta>

      <Card>
        <CardContent>
          <Tabs defaultValue="fila">
            <TabsList className="max-w-full justify-start overflow-x-auto">
              <TabsTrigger value="fila" className="px-3">
                Fila de suspeitas
              </TabsTrigger>
              <TabsTrigger value="ordens" className="px-3">
                Ordens de inspeção
                <span className="tabular-nums text-xs text-muted-foreground">
                  {formatarNumero(ordens.data?.itens.length ?? 0)}
                </span>
              </TabsTrigger>
            </TabsList>

            <TabsContent value="fila" className="flex flex-col gap-3 pt-3">
              <div className="flex flex-wrap items-center gap-3">
                <p className="text-sm text-muted-foreground">
                  Prioridade calculada pela base (score v1 por regras, pesos ainda em calibração). Clique na UC
                  para abrir a Visão 360.
                </p>
                <div className="ml-auto flex items-center gap-3">
                  <Button
                    variant="outline"
                    disabled={!fila.data || fila.data.total === 0 || exportar.isPending}
                    onClick={() => exportar.mutate()}
                  >
                    {exportar.isPending ? (
                      <>
                        <LoaderCircle aria-hidden="true" className="animate-spin" />
                        <span className="tabular-nums">
                          {exportar.progresso === undefined ? 'Exportando…' : `Exportando… ${exportar.progresso}%`}
                        </span>
                      </>
                    ) : (
                      <>
                        <Download aria-hidden="true" />
                        Exportar Excel
                      </>
                    )}
                  </Button>
                  <span className="text-sm whitespace-nowrap">
                    {plural(selecionadas.size, 'selecionada', 'selecionadas')}
                  </span>
                  <Button disabled={selecionadas.size === 0 || gerar.isPending} onClick={gerarOrdens}>
                    {gerar.isPending ? 'Gerando…' : 'Gerar ordens de inspeção'}
                  </Button>
                </div>
              </div>
              <div role="status" aria-live="polite">
                {aviso && (
                  <p className="flex items-center gap-1.5 text-sm font-medium text-primary">
                    <CircleCheck aria-hidden="true" className="size-4" />
                    {aviso} Acompanhe na aba Ordens de inspeção.
                  </p>
                )}
                {gerar.isError && <p className="text-sm text-destructive">{textoErroGerar(gerar.error)}</p>}
                {exportar.isError && (
                  <p className="text-sm text-destructive">
                    {exportar.error instanceof ErroApi
                      ? exportar.error.message
                      : 'Não foi possível exportar a fila. Tente de novo.'}
                  </p>
                )}
              </div>
              <EstadoConsulta
                consulta={fila}
                estaVazio={(dados) => dados.total === 0}
                mensagemVazio="Nenhuma UC suspeita para esses filtros."
              >
                {(dados) => (
                  <>
                    <FilaSuspeitas itens={dados.itens} selecionadas={selecionadas} aoMarcar={marcar} />
                    <Paginacao
                      pagina={dados.pagina}
                      limite={dados.limite}
                      total={dados.total}
                      nomeItens="UCs"
                      desabilitado={fila.isPlaceholderData}
                      aoMudar={setPagina}
                    />
                  </>
                )}
              </EstadoConsulta>
            </TabsContent>

            <TabsContent value="ordens" className="pt-3">
              <EstadoConsulta
                consulta={ordens}
                estaVazio={(dados) => dados.itens.length === 0}
                mensagemVazio="Nenhuma ordem gerada ainda. Marque UCs na fila e clique em Gerar ordens de inspeção."
              >
                {(dados) => <OrdensInspecao ordens={dados.itens} />}
              </EstadoConsulta>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </>
  )
}

function InspecoesPage() {
  const { filtros } = useFiltros()
  const chaveFiltros = [filtros.municipio, filtros.bairro, filtros.classe].join('|')

  return (
    <section className="flex flex-col gap-6">
      <CabecalhoPagina acoes={<FiltrosGlobais campos={['municipio', 'bairro', 'classe']} />} />
      <ConteudoInspecoes key={chaveFiltros} filtros={filtros} />
    </section>
  )
}

export default InspecoesPage
