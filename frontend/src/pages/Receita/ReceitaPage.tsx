import FiltrosGlobais from '@/components/FiltrosGlobais/FiltrosGlobais'

function ReceitaPage() {
  return (
    <section className="flex flex-col gap-4">
      <FiltrosGlobais campos={['municipio', 'bairro', 'classe']} />
      <p className="text-muted-foreground">
        Variação de receita entre períodos, separando efeito-preço e efeito-volume.
      </p>
    </section>
  )
}

export default ReceitaPage
