-- Ordem ativa só para UC da fila de inspeção.
-- Abrir uma ordem libera o nome e o endereço da UC (vw_ordens_campo). Sem esta regra, quem cria
-- ordens poderia abrir uma para qualquer UC, ler os dados e cancelar. O backend já confere a fila
-- antes de criar a ordem; o trigger repete a conferência no banco.
-- Não dá para ser FK: a chave da fila_inspecao é a prioridade, e a carga recria a tabela.
-- A carga não apaga a função nem o trigger: rodar uma vez por ambiente.

CREATE OR REPLACE FUNCTION ordem_exige_uc_na_fila() RETURNS trigger
LANGUAGE plpgsql
SET search_path = public
AS $$
BEGIN
    -- Ordem que já estava ativa segue o fluxo (ABERTA -> EM_CAMPO), mesmo se a UC saiu da fila numa carga
    IF TG_OP = 'UPDATE' AND OLD.status IN ('ABERTA', 'EM_CAMPO') THEN
        RETURN NEW;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM fila_inspecao WHERE id_uc = NEW.id_uc) THEN
        RAISE EXCEPTION 'A UC % não está na fila de inspeção', NEW.id_uc
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$;

-- Vale para criar uma ordem e para reativar uma concluída ou cancelada
DROP TRIGGER IF EXISTS ordem_exige_uc_na_fila ON ordens_inspecao;
CREATE TRIGGER ordem_exige_uc_na_fila
    BEFORE INSERT OR UPDATE OF status ON ordens_inspecao
    FOR EACH ROW
    WHEN (NEW.status IN ('ABERTA', 'EM_CAMPO'))
    EXECUTE FUNCTION ordem_exige_uc_na_fila();
