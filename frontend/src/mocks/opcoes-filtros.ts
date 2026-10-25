import type { OpcoesFiltros } from '@/hooks/use-opcoes-filtros'

// DADOS DE EXEMPLO para desenvolver sem o backend. Não vêm da base real:
// são só alguns municípios e bairros públicos da Região Metropolitana do Recife

// jul/2022 a jun/2026, o mesmo intervalo da base
const competencias = Array.from({ length: 48 }, (_, indice) => {
  const data = new Date(2022, 6 + indice, 1)
  return `${data.getFullYear()}-${String(data.getMonth() + 1).padStart(2, '0')}`
})

export const opcoesFiltrosExemplo: OpcoesFiltros = {
  competencias,
  municipios: [
    { nome: 'Jaboatão dos Guararapes', bairros: ['Candeias', 'Piedade', 'Prazeres'] },
    { nome: 'Olinda', bairros: ['Bairro Novo', 'Casa Caiada', 'Rio Doce'] },
    { nome: 'Paulista', bairros: ['Janga', 'Maranguape I'] },
    { nome: 'Recife', bairros: ['Boa Viagem', 'Casa Forte', 'Ibura', 'Pina'] },
  ],
  classes: ['RESIDENCIAL', 'COMERCIAL', 'INDUSTRIAL', 'RURAL', 'PODER_PUBLICO'],
}
