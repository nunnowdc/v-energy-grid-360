import CabecalhoPagina from '@/components/CabecalhoPagina/CabecalhoPagina'
import FiltrosGlobais from '@/components/FiltrosGlobais/FiltrosGlobais'

function ContinuidadePage() {
  return (
    <section className="flex flex-col gap-6">
      <CabecalhoPagina acoes={<FiltrosGlobais campos={['periodo', 'municipio']} />} />
    </section>
  )
}

export default ContinuidadePage
