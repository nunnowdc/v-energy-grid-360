import { Gauge, MapPin, Sun } from 'lucide-react'
import type { ReactNode } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { classesConsumo } from '@/config/classes'
import { textoDoCodigo } from '@/config/codigos'
import type { Uc360 } from '@/hooks/use-uc-360'
import { formatarData, formatarNumero } from '@/lib/formatacao'

type ResumoUcProps = {
  dados: Pick<Uc360, 'uc' | 'medidor_atual' | 'geracao_distribuida'>
}

function Campo({ rotulo, children }: { rotulo: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-xs text-muted-foreground">{rotulo}</dt>
      <dd className="font-medium">{children}</dd>
    </div>
  )
}

function endereco({ logradouro, numero, bairro, municipio, uf }: Uc360['uc']) {
  const rua = [logradouro, numero].filter(Boolean).join(', ')
  const cidade = [municipio, uf].filter(Boolean).join('/')
  return [rua, bairro, cidade].filter(Boolean).join(' · ')
}

// Cadastro da UC: quem é, onde fica, o medidor e a geração própria
function ResumoUc({ dados }: ResumoUcProps) {
  const { uc, medidor_atual: medidor, geracao_distribuida: gd } = dados
  const classe = uc.classe ? classesConsumo[uc.classe] : undefined

  return (
    <div className="grid gap-4 lg:grid-cols-4">
      <Card className="lg:col-span-2">
        <CardHeader>
          <CardDescription className="font-mono text-xs tracking-wider uppercase">
            Unidade consumidora · {uc.id_uc}
          </CardDescription>
          <CardTitle className="text-xl font-semibold">{uc.nome_titular ?? 'Titular não informado'}</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <p className="flex items-start gap-1.5 text-muted-foreground">
            <MapPin aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
            {endereco(uc) || 'Endereço não informado'}
          </p>
          {classe && (
            <span className="inline-flex w-fit items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium">
              <span aria-hidden="true" className="size-2 rounded-full" style={{ backgroundColor: classe.cor }} />
              {classe.label}
            </span>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-[15px] font-semibold">
            <Gauge aria-hidden="true" className="size-4 text-muted-foreground" />
            Medidor atual
          </CardTitle>
        </CardHeader>
        <CardContent>
          {medidor ? (
            <dl className="grid gap-2">
              <Campo rotulo="Tipo">
                {medidor.tipo_medidor_atual ? textoDoCodigo(medidor.tipo_medidor_atual) : '—'}
              </Campo>
              <Campo rotulo="Modelo">
                <span className="font-mono">{medidor.modelo_medidor_atual ?? '—'}</span>
              </Campo>
              <Campo rotulo="Instalado em">
                {medidor.data_instalacao_medidor_atual ? formatarData(medidor.data_instalacao_medidor_atual) : '—'}
              </Campo>
            </dl>
          ) : (
            <p className="text-muted-foreground">Sem medidor ativo no cadastro.</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-[15px] font-semibold">
            <Sun aria-hidden="true" className="size-4 text-muted-foreground" />
            Geração própria
          </CardTitle>
        </CardHeader>
        <CardContent>
          {gd.possui_gd ? (
            <dl className="grid gap-2">
              <Campo rotulo="Potência">
                <span className="font-mono">
                  {gd.potencia_gd_kwp === null ? '—' : `${formatarNumero(gd.potencia_gd_kwp)} kWp`}
                </span>
              </Campo>
              <Campo rotulo="Modalidade">{gd.modalidade_gd ? textoDoCodigo(gd.modalidade_gd) : '—'}</Campo>
              <Campo rotulo="Conectada em">{gd.data_conexao_gd ? formatarData(gd.data_conexao_gd) : '—'}</Campo>
            </dl>
          ) : (
            <p className="text-muted-foreground">Não possui geração distribuída (painel solar).</p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export default ResumoUc
