import sys
from pathlib import Path

# Adiciona o diretório ai-agent ao sys.path
root_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(root_dir))

from tests.test_avaliacao_golden_set import test_sql_esperado_do_golden_usa_tabelas_e_colunas_obrigatorias, test_avaliacao_completa_golden_dataset

if __name__ == "__main__":
    print("Iniciando validação estática do Golden Dataset...")
    test_sql_esperado_do_golden_usa_tabelas_e_colunas_obrigatorias()
    print("Sucesso: Tabelas e colunas obrigatórias validadas via AST SQLGlot!")

    print("\nIniciando avaliação completa do agente (Golden Dataset)...")
    try:
        test_avaliacao_completa_golden_dataset()
        print("Sucesso: Avaliação completa do Golden Dataset executada com êxito!")
    except Exception as e:
        print(f"Erro na avaliação completa: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
