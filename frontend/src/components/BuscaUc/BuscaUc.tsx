import { Search } from 'lucide-react'
import { useId, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ehIdUc } from '@/hooks/use-uc-360'

type BuscaUcProps = {
  // ID da UC aberta, para o campo já começar preenchido
  idAtual?: string
}

// Busca pelo ID completo da UC (não há busca por nome no MVP)
function BuscaUc({ idAtual = '' }: BuscaUcProps) {
  const navigate = useNavigate()
  const idAjuda = useId()
  const [texto, setTexto] = useState(idAtual)
  const [invalido, setInvalido] = useState(false)

  function buscar(evento: FormEvent) {
    evento.preventDefault()
    const id = texto.trim().toUpperCase()
    if (!ehIdUc(id)) {
      setInvalido(true)
      return
    }
    setInvalido(false)
    navigate(`/visao-360/${id}`)
  }

  return (
    <form role="search" onSubmit={buscar} className="flex flex-col gap-1.5">
      <div className="flex gap-2">
        <Input
          aria-label="ID da unidade consumidora"
          aria-describedby={idAjuda}
          aria-invalid={invalido}
          placeholder="Ex.: UC100000"
          value={texto}
          onChange={(evento) => setTexto(evento.target.value)}
          className="h-9 w-full bg-card tabular-nums uppercase placeholder:normal-case sm:w-56"
        />
        <Button type="submit" className="h-9">
          <Search />
          Buscar
        </Button>
      </div>
      <p id={idAjuda} className={invalido ? 'text-xs text-destructive' : 'text-xs text-muted-foreground'}>
        {invalido ? 'Digite UC seguido de 6 números, ex.: UC100000.' : 'Digite o ID completo da unidade consumidora.'}
      </p>
    </form>
  )
}

export default BuscaUc
