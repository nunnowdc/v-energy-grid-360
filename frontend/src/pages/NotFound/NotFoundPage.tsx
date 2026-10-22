import { Link } from 'react-router'

function NotFoundPage() {
  return (
    <section>
      <p className="text-muted-foreground">
        O endereço acessado não existe.{' '}
        <Link to="/" className="text-primary underline-offset-4 hover:underline">
          Voltar para o início
        </Link>
      </p>
    </section>
  )
}

export default NotFoundPage
