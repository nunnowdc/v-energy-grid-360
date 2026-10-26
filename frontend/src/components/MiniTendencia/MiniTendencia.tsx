type MiniTendenciaProps = {
  // Valores em ordem (ex.: os 12 meses do período); só a forma importa
  valores: number[]
}

const ALTURA_PX = 26

// Barrinhas que mostram a tendência no canto do cartão de KPI.
// É decorativa: o número e a variação já estão escritos no cartão
function MiniTendencia({ valores }: MiniTendenciaProps) {
  const maior = Math.max(...valores, 0)

  return (
    <div aria-hidden="true" className="flex items-end gap-0.5" style={{ height: ALTURA_PX }}>
      {valores.map((valor, indice) => (
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
