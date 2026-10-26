import { SearchX } from 'lucide-react'
import { Link } from 'react-router'
import { Button } from '@/components/ui/button'

function NotFoundPage() {
  return (
    <section className="flex flex-1 flex-col items-center justify-center gap-3 text-center">
      <SearchX className="size-10 text-muted-foreground" />
      <h1 className="text-xl font-bold tracking-tight">Página não encontrada</h1>
      <p className="max-w-md text-sm text-muted-foreground">
        O endereço acessado não existe. Confira o link ou volte para o início.
      </p>
      <Button className="mt-2" nativeButton={false} render={<Link to="/" />}>
        Voltar ao início
      </Button>
    </section>
  )
}

export default NotFoundPage
