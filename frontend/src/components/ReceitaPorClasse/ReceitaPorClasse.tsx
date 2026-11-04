import Variacao from '@/components/Variacao/Variacao'
import { classesConsumo } from '@/config/classes'
import type { IndicadoresGerais } from '@/hooks/use-indicadores'
import { variacaoPercentual } from '@/lib/comparacao'
import { formatarMoedaCompacta } from '@/lib/formatacao'

type ReceitaPorClasseProps = {
  classes: IndicadoresGerais['por_classe']
}

// Barras horizontais da receita de cada classe, da maior para a menor.
// A cor acompanha a classe; os números ficam escritos ao lado da barra
function ReceitaPorClasse({ classes }: ReceitaPorClasseProps) {
  const ordenadas = [...classes].sort((a, b) => b.receita_faturada - a.receita_faturada)
  const maior = Math.max(...ordenadas.map((linha) => linha.receita_faturada), 0)

  return (
    <ul className="flex flex-col gap-4">
      {ordenadas.map((linha) => {
        const { label, cor } = classesConsumo[linha.classe]
        const variacao = variacaoPercentual(linha.receita_faturada, linha.receita_faturada_anterior)
        return (
          <li key={linha.classe} className="flex flex-col gap-1.5">
            <div className="flex items-baseline justify-between gap-3 text-[13px]">
              <span className="font-medium">{label}</span>
              <span className="tabular-nums font-semibold">{formatarMoedaCompacta(linha.receita_faturada)}</span>
            </div>
            <div aria-hidden="true" className="h-2.5 rounded-r-[4px] bg-muted">
              <div
                className="h-full rounded-r-[4px]"
                style={{ width: maior > 0 ? `${(linha.receita_faturada / maior) * 100}%` : 0, background: cor }}
              />
            </div>
            {variacao !== undefined && <Variacao percentual={variacao} sentido="subir-e-bom" complemento="vs. período anterior" />}
          </li>
        )
      })}
    </ul>
  )
}

export default ReceitaPorClasse
