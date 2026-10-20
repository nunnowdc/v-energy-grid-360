import { Link } from 'react-router'

function NotFoundPage() {
  return (
    <section>
      <h1>Página não encontrada</h1>
      <p>
        O endereço acessado não existe. <Link to="/">Voltar para o início</Link>
      </p>
    </section>
  )
}

export default NotFoundPage
