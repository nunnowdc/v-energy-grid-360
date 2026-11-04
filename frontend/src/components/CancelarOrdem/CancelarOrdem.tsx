import { useState } from 'react'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'
import type { OrdemInspecao } from '@/hooks/use-ordens-inspecao'

type CancelarOrdemProps = {
  ordem: OrdemInspecao
  desabilitado: boolean
  aoConfirmar: () => void
}

// Cancelar encerra a ordem inteira e não tem volta, então pede confirmação e explica
// o que acontece com a UC. Só aparece em ordem aberta ou em campo
function CancelarOrdem({ ordem, desabilitado, aoConfirmar }: CancelarOrdemProps) {
  const [aberto, setAberto] = useState(false)

  function confirmar() {
    aoConfirmar()
    setAberto(false)
  }

  return (
    <AlertDialog open={aberto} onOpenChange={setAberto}>
      <AlertDialogTrigger
        render={
          <Button
            size="sm"
            variant="ghost"
            disabled={desabilitado}
            className="text-muted-foreground hover:bg-negativo-fundo hover:text-negativo"
          />
        }
      >
        Cancelar ordem
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Cancelar a ordem {ordem.id_ordem}?</AlertDialogTitle>
          <AlertDialogDescription>
            {ordem.status === 'EM_CAMPO' && 'A equipe já foi enviada a campo. '}A {ordem.id_uc} volta para a fila de
            suspeitas e pode receber uma ordem nova. A ordem cancelada não pode ser reaberta.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Manter a ordem</AlertDialogCancel>
          <AlertDialogAction variant="destructive" onClick={confirmar}>
            Cancelar ordem
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}

export default CancelarOrdem
