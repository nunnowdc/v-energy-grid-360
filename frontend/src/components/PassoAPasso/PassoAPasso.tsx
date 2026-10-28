import EstadoConsulta from '@/components/EstadoConsulta/EstadoConsulta'
import GrafoRaciocinio from '@/components/GrafoRaciocinio/GrafoRaciocinio'
import { Skeleton } from '@/components/ui/skeleton'
import { NO_AUDITORIA } from '@/config/nos-agente'
import { useAuditoriaAgente, type AuditoriaAgente } from '@/hooks/use-agente-ia'
import { formatarNumero } from '@/lib/formatacao'
import { lerListaPassos, montarPassos } from '@/lib/passos-agente'

const nomesRotas: Record<string, string> = {
  sql: 'Consulta aos dados',
  rag: 'Documentos',
  ambos: 'Dados e documentos',
  recusa: 'Recusa',
  fora_escopo: 'Fora do escopo',
}

const hora = new Intl.DateTimeFormat('pt-BR', { timeStyle: 'medium' })

const segundos = (ms: number) => `${formatarNumero(ms / 1000)} s`

function formatarValor(valor: unknown) {
  if (typeof valor === 'number') {
    return formatarNumero(valor)
  }
  return valor === null || valor === undefined ? '—' : String(valor)
}

// A auditoria guarda as primeiras linhas como texto JSON
function lerAmostra(amostra: string | null): Record<string, unknown>[] {
  try {
    const linhas: unknown = JSON.parse(amostra ?? '[]')
    return Array.isArray(linhas) ? linhas.filter((linha) => typeof linha === 'object' && linha !== null) : []
  } catch {
    return []
  }
}

function Consulta({ sql }: { sql: string }) {
  return (
    <pre className="mt-1 rounded-md border bg-card px-2.5 py-2 font-[Consolas,ui-monospace,monospace] text-xs leading-relaxed whitespace-pre-wrap break-words">
      {sql}
    </pre>
  )
}

function Amostra({ linhas, total }: { linhas: Record<string, unknown>[]; total: number }) {
  const colunas = Object.keys(linhas[0])

  return (
    <div className="mt-1 flex flex-col gap-1">
      <div className="overflow-x-auto rounded-md border bg-card">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b text-left text-muted-foreground">
              {colunas.map((coluna) => (
                <th key={coluna} scope="col" className="px-2 py-1.5 font-medium whitespace-nowrap">
                  {coluna}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {linhas.map((linha, indice) => (
              <tr key={indice} className="border-b last:border-0">
                {colunas.map((coluna) => (
                  <td key={coluna} className="px-2 py-1.5 tabular-nums whitespace-nowrap">
                    {formatarValor(linha[coluna])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-muted-foreground">
        {linhas.length < total
          ? `Primeiras ${linhas.length} de ${formatarNumero(total)} linhas`
          : `${formatarNumero(total)} ${total === 1 ? 'linha' : 'linhas'}`}
        , com campos pessoais mascarados
      </p>
    </div>
  )
}

function Indicador({ rotulo, valor }: { rotulo: string; valor: string }) {
  return (
    <div className="flex flex-col">
      <dt className="text-xs text-muted-foreground">{rotulo}</dt>
      <dd className="text-sm font-semibold tabular-nums">{valor}</dd>
    </div>
  )
}

function Raciocinio({ auditoria }: { auditoria: AuditoriaAgente }) {
  const passos = montarPassos(lerListaPassos(auditoria.passos_execucao))
  // O passo da auditoria é registrado depois de gravar, então não aparece na
  // lista; se o registro existe, ele aconteceu
  passos.push({
    no: NO_AUDITORIA,
    detalhes: [`Registro gravado às ${hora.format(new Date(auditoria.data_hora))}.`],
    situacao: 'concluido',
    repeticao: false,
  })

  const amostra = lerAmostra(auditoria.amostra_resultado_json)
  const sql = auditoria.sql_gerado
  // A consulta aparece no nó que a produziu: a certificada (6) ou a escrita pela IA (7)
  const noDaConsulta = auditoria.hit_cache ? 6 : 7

  return (
    <div className="flex flex-col gap-4">
      {auditoria.pergunta_autonoma && auditoria.pergunta_autonoma !== auditoria.pergunta_original && (
        <p className="text-sm">
          <span className="text-muted-foreground">A IA entendeu a pergunta como: </span>
          {auditoria.pergunta_autonoma}
        </p>
      )}

      <dl className="grid grid-cols-2 gap-3 rounded-lg border px-3 py-2.5">
        <Indicador rotulo="Caminho" valor={nomesRotas[auditoria.rota_escolhida] ?? auditoria.rota_escolhida} />
        <Indicador rotulo="Tempo total" valor={segundos(auditoria.tempo_execucao_ms)} />
        <Indicador rotulo="Linhas no resultado" valor={formatarNumero(auditoria.linhas_retornadas)} />
        <Indicador
          rotulo="Tokens do modelo"
          valor={formatarNumero(auditoria.tokens_prompt + auditoria.tokens_resposta)}
        />
      </dl>

      <GrafoRaciocinio
        passos={passos}
        extras={{
          ...(sql && { [noDaConsulta]: <Consulta sql={sql} /> }),
          ...(amostra.length > 0 && { 9: <Amostra linhas={amostra} total={auditoria.linhas_retornadas} /> }),
        }}
      />

      {auditoria.erro_mensagem && (
        <p className="rounded-md border border-destructive/30 px-2.5 py-2 text-[13px] text-destructive">
          Último erro registrado: {auditoria.erro_mensagem}
        </p>
      )}
    </div>
  )
}

function Esqueleto() {
  return (
    <div className="flex flex-col gap-5">
      <Skeleton className="h-14 w-full" />
      {Array.from({ length: 5 }, (_, indice) => (
        <div key={indice} className="flex gap-3">
          <Skeleton className="size-8 shrink-0 rounded-full" />
          <Skeleton className="h-16 flex-1" />
        </div>
      ))}
    </div>
  )
}

// "Como a IA chegou nisso?": a trilha de auditoria de uma resposta, aberta
// dentro da própria resposta na conversa
function PassoAPasso({ auditId }: { auditId: string }) {
  const consulta = useAuditoriaAgente(auditId)

  return (
    <section aria-label="Como a IA chegou nisso?" className="flex flex-col gap-3">
      <div className="flex flex-col gap-0.5">
        <h3 className="text-[13px] font-semibold">Como a IA chegou nisso?</h3>
        <p className="text-xs text-muted-foreground">Cada nó é um passo do agente, na ordem em que aconteceu</p>
      </div>
      <EstadoConsulta consulta={consulta} esqueleto={<Esqueleto />}>
        {(auditoria) => <Raciocinio auditoria={auditoria} />}
      </EstadoConsulta>
    </section>
  )
}

export default PassoAPasso
