import CabecalhoPagina from '@/components/CabecalhoPagina/CabecalhoPagina'
import FiltrosGlobais from '@/components/FiltrosGlobais/FiltrosGlobais'

function ReceitaPage() {
  return (
    <section className="flex flex-col gap-6">
      <CabecalhoPagina acoes={<FiltrosGlobais campos={['municipio', 'bairro', 'classe']} />} />
    </section>
  )
}

export default ReceitaPage
