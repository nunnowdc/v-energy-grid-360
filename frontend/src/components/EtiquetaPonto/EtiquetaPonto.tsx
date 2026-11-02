type EtiquetaPontoProps = {
  // Posição do ponto no gráfico, como o LabelList do recharts entrega
  x: number
  y: number
  texto: string
}

// O número de um ponto de gráfico de linha numa etiqueta com o fundo do cartão: a linha
// que sobe ou desce passa por trás dela, sem cortar o texto. Fica acima do ponto.
// Uso: <LabelList dataKey="valor" content={({ x, y, value }) => <EtiquetaPonto ... />} />
function EtiquetaPonto({ x, y, texto }: EtiquetaPontoProps) {
  // Largura aproximada do texto em 12px semibold, mais a folga dos lados
  const largura = texto.length * 7 + 12
  const altura = 20
  const topo = y - altura - 8

  return (
    <g>
      <rect
        x={x - largura / 2}
        y={topo}
        width={largura}
        height={altura}
        rx={5}
        fill="var(--card)"
        stroke="var(--border)"
      />
      <text
        x={x}
        y={topo + altura / 2}
        textAnchor="middle"
        dominantBaseline="central"
        fontSize={12}
        fontWeight={600}
        fill="var(--foreground)"
        className="tabular-nums"
      >
        {texto}
      </text>
    </g>
  )
}

export default EtiquetaPonto
