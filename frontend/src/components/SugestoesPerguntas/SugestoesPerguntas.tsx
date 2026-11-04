import { Sparkles } from 'lucide-react'

// Perguntas testadas no agente real, uma de cada área da base
const sugestoes = [
  'Qual o faturamento em Recife no ano de 2024?',
  'Quantas unidades consumidoras existem por classe de consumo?',
  'Qual alimentador teve o maior DEC em 2025?',
]

// Conversa vazia: explica o que dá para perguntar e oferece exemplos
function SugestoesPerguntas({ aoEscolher }: { aoEscolher: (pergunta: string) => void }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 py-6 text-center">
      <span className="flex size-10 items-center justify-center rounded-full bg-primary/10 text-primary">
        <Sparkles aria-hidden="true" className="size-5" />
      </span>
      <div className="flex max-w-md flex-col gap-1">
        <p className="font-semibold">Pergunte em português sobre os dados da V-Energy</p>
        <p className="text-sm text-muted-foreground">
          O agente consulta a base Gold, mostra o selo de confiança da resposta e o passo a passo de como chegou
          nela. Quando não tem base segura para responder, ele diz que não sabe.
        </p>
      </div>
      <ul aria-label="Sugestões de pergunta" className="flex flex-wrap justify-center gap-2">
        {sugestoes.map((sugestao) => (
          <li key={sugestao}>
            <button
              type="button"
              onClick={() => aoEscolher(sugestao)}
              className="rounded-full border bg-card px-3 py-1.5 text-left text-[13px] transition-colors hover:border-primary/40 hover:bg-primary/5 focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
            >
              {sugestao}
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default SugestoesPerguntas
