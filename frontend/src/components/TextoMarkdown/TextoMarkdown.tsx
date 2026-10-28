import Markdown, { type Components } from 'react-markdown'
import remarkGfm from 'remark-gfm'

// Cada elemento do Markdown com o visual do portal. HTML escrito no texto não é
// interpretado (padrão do react-markdown), então a resposta da IA não injeta nada
const componentes: Components = {
  p: ({ children }) => <p className="leading-relaxed">{children}</p>,
  strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
  ul: ({ children }) => <ul className="flex list-disc flex-col gap-1 pl-5">{children}</ul>,
  ol: ({ children }) => <ol className="flex list-decimal flex-col gap-1 pl-5">{children}</ol>,
  li: ({ children }) => <li className="leading-relaxed">{children}</li>,
  h1: ({ children }) => <p className="font-semibold">{children}</p>,
  h2: ({ children }) => <p className="font-semibold">{children}</p>,
  h3: ({ children }) => <p className="font-semibold">{children}</p>,
  h4: ({ children }) => <p className="font-semibold">{children}</p>,
  hr: () => <hr className="border-border" />,
  a: ({ children, href }) => (
    <a href={href} target="_blank" rel="noreferrer" className="text-primary underline underline-offset-2">
      {children}
    </a>
  ),
  // Nomes de tabela e coluna (`agg_receita_mensal`) e blocos de consulta
  code: ({ children }) => (
    <code className="rounded bg-muted px-1 py-0.5 font-[Consolas,ui-monospace,monospace] text-[0.85em] break-words">
      {children}
    </code>
  ),
  pre: ({ children }) => (
    <pre className="overflow-x-auto rounded-md border bg-muted/50 p-2 text-xs [&_code]:bg-transparent [&_code]:p-0">
      {children}
    </pre>
  ),
  table: ({ children }) => (
    <div className="overflow-x-auto rounded-md border">
      <table className="w-full text-xs">{children}</table>
    </div>
  ),
  th: ({ children }) => <th className="border-b px-2 py-1.5 text-left font-medium text-muted-foreground">{children}</th>,
  td: ({ children }) => <td className="border-b px-2 py-1.5 tabular-nums">{children}</td>,
}

// Texto em Markdown das respostas do agente (negrito, listas, tabelas, código)
function TextoMarkdown({ texto }: { texto: string }) {
  return (
    <div className="flex flex-col gap-2 text-sm break-words">
      <Markdown remarkPlugins={[remarkGfm]} components={componentes}>
        {texto}
      </Markdown>
    </div>
  )
}

export default TextoMarkdown
