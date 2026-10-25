import FiltrosGlobais from '@/components/FiltrosGlobais/FiltrosGlobais'

function IndicadoresPage() {
  return (
    <section className="flex flex-col gap-4">
      <FiltrosGlobais campos={['periodo', 'municipio', 'classe']} />
      <p className="text-muted-foreground">
        Principais indicadores do negócio, comparados entre períodos.
      </p>
    </section>
  )
}

export default IndicadoresPage
