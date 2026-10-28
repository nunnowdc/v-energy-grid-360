import type { ReactNode } from 'react'
import EstadoVazio from '@/components/EstadoVazio/EstadoVazio'
import Paginacao from '@/components/Paginacao/Paginacao'
import SeloBandeira from '@/components/SeloBandeira/SeloBandeira'
import StatusPagamento from '@/components/StatusPagamento/StatusPagamento'
import Variacao from '@/components/Variacao/Variacao'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { rotuloCausa } from '@/config/causas'
import { textoDoCodigo } from '@/config/codigos'
import type { HistoricoUc, Uc360 } from '@/hooks/use-uc-360'
import {
  formatarCompetencia,
  formatarData,
  formatarDataHora,
  formatarKwh,
  formatarMoeda,
  formatarNumero,
} from '@/lib/formatacao'
import { cn } from '@/lib/utils'

type HistoricosUcProps = {
  historicos: Uc360['historicos']
  aoMudarPagina: (historico: HistoricoUc, pagina: number) => void
  // Uma página nova está chegando: a tabela atual fica esmaecida
  atualizando?: boolean
}

const abas: { valor: HistoricoUc; rotulo: string; nomeItens: string; vazio: string }[] = [
  { valor: 'faturas', rotulo: 'Faturas', nomeItens: 'faturas', vazio: 'Nenhuma fatura registrada.' },
  { valor: 'leituras', rotulo: 'Leituras', nomeItens: 'leituras', vazio: 'Nenhuma leitura registrada.' },
  {
    valor: 'interrupcoes',
    rotulo: 'Interrupções',
    nomeItens: 'interrupções',
    vazio: 'Nenhuma interrupção registrada para esta unidade.',
  },
  { valor: 'chamados', rotulo: 'Chamados', nomeItens: 'chamados', vazio: 'Nenhum chamado registrado.' },
]

// Valor ausente aparece como travessão, nunca como zero
function ou<T>(valor: T | null, formatar: (valor: T) => ReactNode) {
  return valor === null ? <span className="text-muted-foreground">—</span> : formatar(valor)
}

const numeroDireita = 'text-right tabular-nums'

function TabelaFaturas({ itens }: { itens: Uc360['historicos']['faturas']['itens'] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Mês</TableHead>
          <TableHead className="text-right">Consumo</TableHead>
          <TableHead>Bandeira</TableHead>
          <TableHead className="text-right">Valor</TableHead>
          <TableHead>Vencimento</TableHead>
          <TableHead>Pagamento</TableHead>
          <TableHead>Situação</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {itens.map((fatura) => (
          <TableRow key={fatura.id_fatura}>
            <TableCell className="font-medium">{formatarCompetencia(fatura.mes_referencia)}</TableCell>
            <TableCell className={numeroDireita}>{ou(fatura.consumo_kwh, formatarKwh)}</TableCell>
            <TableCell>
              <SeloBandeira bandeira={fatura.bandeira_tarifaria} />
            </TableCell>
            <TableCell className={numeroDireita}>{ou(fatura.receita_faturada, formatarMoeda)}</TableCell>
            <TableCell>{ou(fatura.data_vencimento, formatarData)}</TableCell>
            <TableCell>{ou(fatura.data_pagamento, formatarData)}</TableCell>
            <TableCell>
              <StatusPagamento status={fatura.status_pagamento} diasAtraso={fatura.dias_atraso} />
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

function TabelaLeituras({ itens }: { itens: Uc360['historicos']['leituras']['itens'] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Mês</TableHead>
          <TableHead>Data da leitura</TableHead>
          <TableHead className="text-right">Leitura (anterior → atual)</TableHead>
          <TableHead className="text-right">Consumo</TableHead>
          <TableHead className="text-right">vs. ano anterior</TableHead>
          <TableHead>Tipo</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {itens.map((leitura) => (
          <TableRow key={leitura.id_leitura}>
            <TableCell className="font-medium">{formatarCompetencia(leitura.mes_referencia)}</TableCell>
            <TableCell>{ou(leitura.data_leitura, formatarData)}</TableCell>
            <TableCell className={cn(numeroDireita, 'text-muted-foreground')}>
              {ou(leitura.leitura_anterior, formatarNumero)} → {ou(leitura.leitura_atual, formatarNumero)}
            </TableCell>
            <TableCell className={numeroDireita}>
              {ou(leitura.consumo_kwh, formatarKwh)}
              {leitura.consumo_imputado && (
                <span className="block text-xs text-muted-foreground">estimado na troca de medidor</span>
              )}
            </TableCell>
            <TableCell className="text-right">
              {ou(leitura.variacao_ano_anterior_pct, (valor) => (
                <Variacao percentual={valor} />
              ))}
            </TableCell>
            <TableCell>
              {ou(leitura.tipo_leitura, (tipo) => (
                <span className={tipo === 'ESTIMADA' ? 'font-medium' : 'text-muted-foreground'}>
                  {textoDoCodigo(tipo)}
                </span>
              ))}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

function TabelaInterrupcoes({ itens }: { itens: Uc360['historicos']['interrupcoes']['itens'] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Início</TableHead>
          <TableHead>Fim</TableHead>
          <TableHead className="text-right">Duração</TableHead>
          <TableHead>Tipo</TableHead>
          <TableHead>Causa</TableHead>
          <TableHead>Alimentador</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {itens.map((interrupcao) => (
          <TableRow key={interrupcao.id_ocorrencia}>
            <TableCell>{ou(interrupcao.data_abertura, formatarDataHora)}</TableCell>
            <TableCell>{ou(interrupcao.data_encerramento, formatarDataHora)}</TableCell>
            <TableCell className={numeroDireita}>
              {ou(interrupcao.duracao_h, (horas) => `${interrupcao.duracao_truncada ? '≥ ' : ''}${formatarNumero(horas)} h`)}
            </TableCell>
            <TableCell>{ou(interrupcao.tipo, textoDoCodigo)}</TableCell>
            <TableCell>{ou(interrupcao.causa, rotuloCausa)}</TableCell>
            <TableCell className="tabular-nums">{ou(interrupcao.alimentador, (codigo) => codigo)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

function TabelaChamados({ itens }: { itens: Uc360['historicos']['chamados']['itens'] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Protocolo</TableHead>
          <TableHead>Aberto em</TableHead>
          <TableHead>Assunto</TableHead>
          <TableHead>Canal</TableHead>
          <TableHead>Situação</TableHead>
          <TableHead className="text-right">Tratativas</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {itens.map((chamado) => (
          <TableRow key={chamado.protocolo}>
            <TableCell className="tabular-nums">{chamado.protocolo}</TableCell>
            <TableCell>{ou(chamado.data_abertura, formatarDataHora)}</TableCell>
            <TableCell>
              {ou(chamado.assunto, textoDoCodigo)}
              {chamado.subassunto && (
                <span className="block text-xs text-muted-foreground">{textoDoCodigo(chamado.subassunto)}</span>
              )}
            </TableCell>
            <TableCell>{ou(chamado.canal, textoDoCodigo)}</TableCell>
            <TableCell>{ou(chamado.status_chamado, textoDoCodigo)}</TableCell>
            <TableCell className={numeroDireita}>{ou(chamado.qtd_tratativas, formatarNumero)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

function tabelaDa(historico: HistoricoUc, historicos: Uc360['historicos']) {
  switch (historico) {
    case 'faturas':
      return <TabelaFaturas itens={historicos.faturas.itens} />
    case 'leituras':
      return <TabelaLeituras itens={historicos.leituras.itens} />
    case 'interrupcoes':
      return <TabelaInterrupcoes itens={historicos.interrupcoes.itens} />
    case 'chamados':
      return <TabelaChamados itens={historicos.chamados.itens} />
  }
}

// Históricos completos da UC, um por aba, cada um com a própria paginação
function HistoricosUc({ historicos, aoMudarPagina, atualizando }: HistoricosUcProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-[15px] font-semibold">Histórico</CardTitle>
        <CardDescription>Do mais recente para o mais antigo</CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="faturas">
          {/* No celular as abas não cabem na largura: a fileira rola de lado */}
          <TabsList className="max-w-full justify-start overflow-x-auto">
            {abas.map(({ valor, rotulo }) => (
              <TabsTrigger key={valor} value={valor} className="px-3">
                {rotulo}
                <span className="tabular-nums text-xs text-muted-foreground">
                  {formatarNumero(historicos[valor].total)}
                </span>
              </TabsTrigger>
            ))}
          </TabsList>
          {abas.map(({ valor, nomeItens, vazio }) => {
            const pagina = historicos[valor]
            return (
              <TabsContent key={valor} value={valor} className="pt-2">
                {pagina.total === 0 ? (
                  <EstadoVazio mensagem={vazio} />
                ) : (
                  <div aria-busy={atualizando} className={cn('transition-opacity', atualizando && 'opacity-50')}>
                    {tabelaDa(valor, historicos)}
                    <Paginacao
                      pagina={pagina.pagina}
                      limite={pagina.limite}
                      total={pagina.total}
                      nomeItens={nomeItens}
                      desabilitado={atualizando}
                      aoMudar={(novaPagina) => aoMudarPagina(valor, novaPagina)}
                    />
                  </div>
                )}
              </TabsContent>
            )
          })}
        </Tabs>
      </CardContent>
    </Card>
  )
}

export default HistoricosUc
