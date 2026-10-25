import FiltrosGlobais from '@/components/FiltrosGlobais/FiltrosGlobais'

function ContinuidadePage() {
  return (
    <section className="flex flex-col gap-4">
      <FiltrosGlobais campos={['periodo', 'municipio']} />
      <p className="text-muted-foreground">DEC e FEC por alimentador ao longo do tempo.</p>
    </section>
  )
}

export default ContinuidadePage
