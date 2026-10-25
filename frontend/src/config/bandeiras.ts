// Valores da coluna "bandeira_tarifaria" na Gold
export type BandeiraTarifaria = 'VERDE' | 'AMARELA' | 'VERMELHA_P1' | 'VERMELHA_P2'

type InfoBandeira = {
  label: string
  cor: string
}

// Cor sempre acompanhada do nome da bandeira. As cores ficam no src/index.css
export const bandeirasTarifarias: Record<BandeiraTarifaria, InfoBandeira> = {
  VERDE: { label: 'Verde', cor: 'var(--bandeira-verde)' },
  AMARELA: { label: 'Amarela', cor: 'var(--bandeira-amarela)' },
  VERMELHA_P1: { label: 'Vermelha P1', cor: 'var(--bandeira-vermelha-p1)' },
  VERMELHA_P2: { label: 'Vermelha P2', cor: 'var(--bandeira-vermelha-p2)' },
}
