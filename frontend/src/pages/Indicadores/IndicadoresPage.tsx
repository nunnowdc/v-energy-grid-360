import CabecalhoPagina from '@/components/CabecalhoPagina/CabecalhoPagina'
import FiltrosGlobais from '@/components/FiltrosGlobais/FiltrosGlobais'

function IndicadoresPage() {
  return (
    <section className="flex flex-col gap-6">
      <CabecalhoPagina acoes={<FiltrosGlobais campos={['periodo', 'municipio', 'classe']} />} />
    </section>
  )
}

export default IndicadoresPage
