import { useState } from 'react'
import { aplicarTema, temaSalvo, type Tema } from '@/lib/tema'

// Tema escolhido no menu da conta. Começa no que estava salvo, que o
// index.html já aplicou antes de a página aparecer
export function useTema() {
  const [tema, setTema] = useState<Tema>(temaSalvo)

  function mudarTema(novo: Tema) {
    aplicarTema(novo)
    setTema(novo)
  }

  return { tema, mudarTema }
}
