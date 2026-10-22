import { useParams } from 'react-router'

function Visao360Page() {
  const { idUc } = useParams()

  return (
    <section>
      <p className="text-muted-foreground">
        {idUc
          ? `Unidade consumidora: ${idUc}`
          : 'Nenhuma unidade consumidora selecionada.'}
      </p>
    </section>
  )
}

export default Visao360Page
