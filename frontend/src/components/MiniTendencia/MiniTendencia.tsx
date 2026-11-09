type MiniTendenciaProps = {
  // Valores em ordem (ex.: os 12 meses do período); só a forma importa
  valores: number[]
}

const ALTURA_PX = 26
// Com mais valores (ex.: 90 dias), as barrinhas ocupariam o cartão e espremeriam o texto
const MAXIMO_BARRAS = 12

// Junta valores vizinhos em até MAXIMO_BARRAS grupos, pela média de cada um
function agrupar(valores: number[]): number[] {
  if (valores.length <= MAXIMO_BARRAS) {
    return valores
  }
  return Array.from({ length: MAXIMO_BARRAS }, (_, grupo) => {
    const inicio = Math.floor((grupo * valores.length) / MAXIMO_BARRAS)
    const fim = Math.floor(((grupo + 1) * valores.length) / MAXIMO_BARRAS)
    const parte = valores.slice(inicio, fim)
    return parte.reduce((soma, valor) => soma + valor, 0) / parte.length
  })
}

// Barrinhas que mostram a tendência no canto do cartão de KPI.
// É decorativa: o número e a variação já estão escritos no cartão
function MiniTendencia({ valores }: MiniTendenciaProps) {
  const barras = agrupar(valores)
  const maior = Math.max(...barras, 0)

  return (
    <div aria-hidden="true" className="flex shrink-0 items-end gap-0.5" style={{ height: ALTURA_PX }}>
      {barras.map((valor, indice) => (
        <span
          key={indice}
          className="w-1 rounded-[1px] bg-primary/60"
          style={{ height: maior > 0 ? Math.max(2, (valor / maior) * ALTURA_PX) : 2 }}
        />
      ))}
    </div>
  )
}

export default MiniTendencia
