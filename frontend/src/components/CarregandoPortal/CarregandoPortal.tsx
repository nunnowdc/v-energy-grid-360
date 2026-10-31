import MarcaVEnergy from '@/components/MarcaVEnergy/MarcaVEnergy'

// Tela inteira enquanto o portal ainda não sabe quem está logado: nada de
// menu nem dados até o GET /api/auth/me responder
function CarregandoPortal() {
  return (
    <main className="flex min-h-svh flex-col items-center justify-center gap-3 bg-canvas p-4">
      <MarcaVEnergy className="size-10 animate-pulse p-[9px]" />
      <p role="status" className="text-sm text-muted-foreground">
        Carregando o portal…
      </p>
    </main>
  )
}

export default CarregandoPortal
