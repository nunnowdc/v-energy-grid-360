import { useParams } from 'react-router'

function Visao360Page() {
  const { idUc } = useParams()

  return (
    <section>
      <h1>Visão 360</h1>
      <p>
        {idUc
          ? `Unidade consumidora: ${idUc}`
          : 'Nenhuma unidade consumidora selecionada.'}
      </p>
    </section>
  )
}

export default Visao360Page
