import { MessageSquarePlus, Sparkles, X } from 'lucide-react'
import { useEffect, useRef, useState, type KeyboardEvent } from 'react'
import { useLocation, useNavigate } from 'react-router'
import CaixaPergunta from '@/components/CaixaPergunta/CaixaPergunta'
import ConversaAgente, { type Troca } from '@/components/ConversaAgente/ConversaAgente'
import SugestoesPerguntas from '@/components/SugestoesPerguntas/SugestoesPerguntas'
import { Button } from '@/components/ui/button'
import { buscarItemAtual } from '@/config/navegacao'
import {
  usePerguntarAgente,
  type PerguntaAgente,
  type RespostaAgente,
  type TurnoConversa,
} from '@/hooks/use-agente-ia'
import { useOpcoesFiltros } from '@/hooks/use-opcoes-filtros'
import { useUsuario } from '@/hooks/use-usuario'
import { ErroApi } from '@/lib/api/erro-api'
import { telaDaPergunta, telaDoAgente, type TelaDaResposta } from '@/lib/tela-da-resposta'

// Quantas perguntas anteriores vão junto, para o agente entender "e em 2023?"
const TROCAS_NO_HISTORICO = 3

// Só resposta com base (dados ou documentos) mexe no dashboard; recusa e erro, não
const SELOS_QUE_MOSTRAM_TELA = ['certificada', 'gerada_confiavel', 'documental_rag']

function historicoDe(anteriores: Troca[]): TurnoConversa[] {
  return anteriores
    .filter((troca) => troca.resposta)
    .slice(-TROCAS_NO_HISTORICO)
    .flatMap((troca) => [
      { role: 'user' as const, content: troca.pergunta },
      { role: 'assistant' as const, content: troca.resposta!.answer },
    ])
}

// Tela aberta ao lado do agente, pelo endereço: "/visao-360/UC100000" →
// { page: 'visao-360', id_uc: 'UC100000' }. Base para o agente, no futuro,
// responder sobre o que está na tela e atualizar o dashboard
function contextoDaTela(pathname: string): PerguntaAgente['context'] {
  const [, tela, idUc] = pathname.split('/')
  return {
    page: tela || 'indicadores',
    ...(tela === 'visao-360' && idUc && { id_uc: idUc }),
  }
}

type PainelAgenteProps = {
  aberto: boolean
  aoFechar: () => void
}

// Agente de IA numa coluna à direita, ao lado do dashboard. Fica montado
// mesmo fechado, então a conversa continua ao trocar de tela ou reabrir.
// Telas largas: coluna fixa que divide o espaço com a tela; estreitas: por cima.
// Cada resposta leva o dashboard para a tela e os filtros dos dados dela
function PainelAgente({ aberto, aoFechar }: PainelAgenteProps) {
  const { pathname, search } = useLocation()
  const navigate = useNavigate()
  const { usuario, pode } = useUsuario()
  const { data: opcoes } = useOpcoesFiltros()
  const perguntar = usePerguntarAgente()
  const [sessao, setSessao] = useState(() => crypto.randomUUID())
  const [trocas, setTrocas] = useState<Troca[]>([])
  const aguardando = trocas.some((troca) => !troca.resposta && !troca.erro)

  // A resposta chega segundos depois; até lá a pessoa pode ter mudado de tela
  const enderecoAtual = useRef(pathname + search)
  useEffect(() => {
    enderecoAtual.current = pathname + search
  }, [pathname, search])

  // Tela e filtros dos dados da resposta, se o perfil pode abrir essa tela.
  // Com consulta, a tela vem do agente; sem consulta (glossário, normas), do
  // assunto da pergunta
  function telaPara(troca: Troca, resposta: RespostaAgente): Troca['tela'] {
    if (!SELOS_QUE_MOSTRAM_TELA.includes(resposta.selo_confianca)) {
      return undefined
    }
    let tela: TelaDaResposta | null = null
    if (resposta.dashboard) {
      tela = telaDoAgente(resposta.dashboard, opcoes)
    } else if (!resposta.sql) {
      tela = telaDaPergunta(troca.pergunta, opcoes)
    }
    const item = tela && buscarItemAtual(tela.caminho.split('?')[0])
    if (!tela || !item || !pode(item.permissao)) {
      return undefined
    }
    return { caminho: tela.caminho, descricao: [item.label, ...tela.filtros].join(' · ') }
  }

  // Ao abrir, o cursor já vai para a pergunta
  useEffect(() => {
    if (aberto) {
      document.getElementById('pergunta-agente')?.focus()
    }
  }, [aberto])

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
        context: contextoDaTela(pathname),
        history: historicoDe(anteriores),
      },
      {
        onSuccess: (resposta) => {
          const tela = telaPara(troca, resposta)
          atualizar(troca.id, { resposta, tela })
          if (tela && tela.caminho !== enderecoAtual.current) {
            navigate(tela.caminho)
          }
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

  function novaConversa() {
    setTrocas([])
    setSessao(crypto.randomUUID())
  }

  function aoTeclar(evento: KeyboardEvent) {
    if (evento.key === 'Escape') {
      aoFechar()
    }
  }

  return (
    <aside
      id="painel-agente"
      aria-label="Agente de IA"
      hidden={!aberto}
      onKeyDown={aoTeclar}
      className="fixed inset-0 z-40 flex flex-col bg-agente shadow-xl sm:left-auto sm:w-[26rem] sm:border-l lg:sticky lg:top-0 lg:z-auto lg:h-svh lg:w-[24rem] lg:shrink-0 lg:shadow-none 2xl:w-[28rem]"
    >
      <header className="flex h-14 shrink-0 items-center gap-2 border-b px-4">
        <Sparkles aria-hidden="true" className="size-4 text-primary" />
        <h2 className="text-sm font-semibold">Agente de IA</h2>
        <div className="ml-auto flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            disabled={trocas.length === 0 || aguardando}
            onClick={novaConversa}
          >
            <MessageSquarePlus />
            Nova conversa
          </Button>
          <Button variant="ghost" size="icon-sm" aria-label="Fechar o agente" onClick={aoFechar}>
            <X />
          </Button>
        </div>
      </header>

      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-4 py-4">
        {trocas.length === 0 ? (
          <SugestoesPerguntas aoEscolher={enviar} />
        ) : (
          <ConversaAgente trocas={trocas} aoTentarDeNovo={tentarDeNovo} />
        )}
      </div>

      <div className="flex shrink-0 flex-col gap-2 border-t px-4 py-3">
        <CaixaPergunta aoEnviar={enviar} aguardando={aguardando} />
        <p className="text-xs text-muted-foreground">
          Respostas geradas por IA a partir da base Gold. Confira o passo a passo antes de usar um número numa decisão.
        </p>
      </div>
    </aside>
  )
}

export default PainelAgente
