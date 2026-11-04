// Tema do portal: o claro, em azul-petróleo (o padrão), ou o Dracula, a paleta
// escura do tema de mesmo nome do VS Code. As cores de cada um ficam no
// src/index.css; a escolha fica salva no navegador
export type Tema = 'claro' | 'dracula'

// A mesma chave do script do index.html, que aplica o tema antes de a página aparecer
export const CHAVE_TEMA = 'vgrid360-tema'

export function temaSalvo(): Tema {
  try {
    return localStorage.getItem(CHAVE_TEMA) === 'dracula' ? 'dracula' : 'claro'
  } catch {
    // Navegador que bloqueia o armazenamento fica no tema claro
    return 'claro'
  }
}

export function aplicarTema(tema: Tema) {
  document.documentElement.classList.toggle('dark', tema === 'dracula')
  try {
    localStorage.setItem(CHAVE_TEMA, tema)
  } catch {
    // Sem armazenamento, o tema vale até a página recarregar
  }
}
