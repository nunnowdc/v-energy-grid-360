// Valores da coluna "classe" na Gold
export type ClasseConsumo =
  | 'RESIDENCIAL'
  | 'COMERCIAL'
  | 'INDUSTRIAL'
  | 'RURAL'
  | 'PODER_PUBLICO'

type InfoClasse = {
  label: string
  cor: string
}

// A cor acompanha a classe em todas as telas. As cores ficam no src/index.css
export const classesConsumo: Record<ClasseConsumo, InfoClasse> = {
  RESIDENCIAL: { label: 'Residencial', cor: 'var(--chart-1)' },
  COMERCIAL: { label: 'Comercial', cor: 'var(--chart-2)' },
  INDUSTRIAL: { label: 'Industrial', cor: 'var(--chart-3)' },
  RURAL: { label: 'Rural', cor: 'var(--chart-4)' },
  PODER_PUBLICO: { label: 'Poder público', cor: 'var(--chart-5)' },
}

export function ehClasseConsumo(valor: unknown): valor is ClasseConsumo {
  return typeof valor === 'string' && Object.hasOwn(classesConsumo, valor)
}
