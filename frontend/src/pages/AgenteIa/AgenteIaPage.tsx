import { MessageSquarePlus } from 'lucide-react'
import { useRef, useState } from 'react'
import CabecalhoPagina from '@/components/CabecalhoPagina/CabecalhoPagina'
import CaixaPergunta from '@/components/CaixaPergunta/CaixaPergunta'
import ConversaAgente, { type Troca } from '@/components/ConversaAgente/ConversaAgente'
import PainelRaciocinio from '@/components/PainelRaciocinio/PainelRaciocinio'
import SugestoesPerguntas from '@/components/SugestoesPerguntas/SugestoesPerguntas'
import { Button } from '@/components/ui/button'
import { Card, CardAction, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { usePerguntarAgente, type TurnoConversa } from '@/hooks/use-agente-ia'
import { useUsuario } from '@/hooks/use-usuario'
import { ErroApi } from '@/lib/api/erro-api'

// Quantas perguntas anteriores vão junto, para o agente entender "e em 2023?"
const TROCAS_NO_HISTORICO = 3

// A partir desta largura o passo a passo fica ao lado da conversa
const TELA_LARGA = '(min-width: 1024px)'

function historicoDe(anteriores: Troca[]): TurnoConversa[] {
  return anteriores
    .filter((troca) => troca.resposta)
    .slice(-TROCAS_NO_HISTORICO)
    .flatMap((troca) => [
      { role: 'user' as const, content: troca.pergunta },
      { role: 'assistant' as const, content: troca.resposta!.answer },
    ])
}

function AgenteIaPage() {
  const { usuario } = useUsuario()
  const perguntar = usePerguntarAgente()
  const [sessao, setSessao] = useState(() => crypto.randomUUID())
  const [trocas, setTrocas] = useState<Troca[]>([])
  // Resposta que a pessoa escolheu ver; sem escolha, o painel mostra a última
  const [escolhida, setEscolhida] = useState<string>()
  const painel = useRef<HTMLDivElement>(null)

  const selecionada = escolhida ?? trocas.findLast((troca) => troca.resposta)?.resposta?.audit_id
  const aguardando = trocas.some((troca) => !troca.resposta && !troca.erro)

  function atualizar(id: string, mudanca: Partial<Troca>) {
    setTrocas((atuais) => atuais.map((troca) => (troca.id === id ? { ...troca, ...mudanca } : troca)))
  }

  function perguntarAoAgente(troca: Troca, anteriores: Troca[]) {
    perguntar.mutate(
      {
        // Enquanto o login não existe, o usuário é o de teste do perfil
        user_id: `teste-${usuario.perfil.toLowerCase()}`,
        session_id: sessao,
        message: troca.pergunta,
        context: { page: 'agente_ia' },
        history: historicoDe(anteriores),
      },
      {
        onSuccess: (resposta) => {
          atualizar(troca.id, { resposta })
          setEscolhida(undefined)
        },
        onError: (erro) =>
          atualizar(troca.id, {
            erro: erro instanceof ErroApi ? erro.message : 'Algo deu errado. Tente de novo em instantes.',
          }),
      },
    )
  }

  function enviar(pergunta: string) {
    const troca = { id: crypto.randomUUID(), pergunta }
    perguntarAoAgente(troca, trocas)
    setTrocas([...trocas, troca])
  }

  function tentarDeNovo(troca: Troca) {
    atualizar(troca.id, { erro: undefined })
    perguntarAoAgente(troca, trocas.slice(0, trocas.indexOf(troca)))
  }

  function verPassos(auditId: string) {
    setEscolhida(auditId)
    // Na tela estreita o painel fica abaixo da conversa: rola até ele
    if (!window.matchMedia(TELA_LARGA).matches) {
      painel.current?.scrollIntoView?.({ behavior: 'smooth', block: 'start' })
    }
  }

  function novaConversa() {
    setTrocas([])
    setEscolhida(undefined)
    setSessao(crypto.randomUUID())
  }

  return (
    <section className="flex flex-col gap-6">
      <CabecalhoPagina />

      <div className="grid gap-4 lg:h-[calc(100svh-12.5rem)] lg:min-h-[32rem] lg:grid-cols-[minmax(0,1fr)_minmax(0,24rem)] xl:grid-cols-[minmax(0,1fr)_minmax(0,30rem)]">
        <Card className="h-[75svh] min-h-[28rem] lg:h-auto lg:min-h-0">
          <CardHeader>
            <CardTitle className="text-[15px] font-semibold">Conversa</CardTitle>
            {trocas.length > 0 && (
              <CardAction>
                <Button variant="outline" size="sm" disabled={aguardando} onClick={novaConversa}>
                  <MessageSquarePlus />
                  Nova conversa
                </Button>
              </CardAction>
            )}
          </CardHeader>
          <CardContent className="flex min-h-0 flex-1 flex-col gap-3">
            <div className="flex min-h-0 flex-1 flex-col overflow-y-auto pr-1">
              {trocas.length === 0 ? (
                <SugestoesPerguntas aoEscolher={enviar} />
              ) : (
                <ConversaAgente
                  trocas={trocas}
                  selecionada={selecionada}
                  aoVerPassos={verPassos}
                  aoTentarDeNovo={tentarDeNovo}
                />
              )}
            </div>
            <CaixaPergunta aoEnviar={enviar} aguardando={aguardando} />
            <p className="text-xs text-muted-foreground">
              Respostas geradas por IA a partir da base Gold. Confira o passo a passo antes de usar um número numa
              decisão.
            </p>
          </CardContent>
        </Card>

        <div ref={painel} className="scroll-mt-4 lg:min-h-0">
          <PainelRaciocinio auditId={selecionada} className="lg:h-full" />
        </div>
      </div>
    </section>
  )
}

export default AgenteIaPage
