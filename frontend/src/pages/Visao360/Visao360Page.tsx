import { useParams } from 'react-router'
import CabecalhoPagina from '@/components/CabecalhoPagina/CabecalhoPagina'

function Visao360Page() {
  const { idUc } = useParams()

  return (
    <section className="flex flex-col gap-6">
      <CabecalhoPagina />
      <p className="text-sm text-muted-foreground">
        {idUc
          ? `Unidade consumidora: ${idUc}`
          : 'Nenhuma unidade consumidora selecionada.'}
      </p>
    </section>
  )
}

export default Visao360Page
