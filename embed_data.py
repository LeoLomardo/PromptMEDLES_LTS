import os
from dotenv import load_dotenv
from openai import OpenAI
from sqlalchemy import create_engine, text, Row
import numpy as np

# Carrega variaveis de ambiente do arquivo .env
load_dotenv()

# --- Configuracoes ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DB_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
EMBEDDING_MODEL = "text-embedding-3-small"
BATCH_SIZE = 100

# --- Inicializacao dos Clientes ---
client = OpenAI(api_key=OPENAI_API_KEY)
engine = create_engine(DB_URL)

def get_embedding(text_to_embed):
    """Gera um embedding para o texto fornecido."""
    if not text_to_embed or not text_to_embed.strip():
        return None
    try:
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=[text_to_embed]
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"  -> Erro na API da OpenAI: {e}")
        return None

def criar_contexto_do_registro(row: Row) -> str:
    """
    Combina as colunas de um registro em um unico texto para o embedding.
    Trata valores nulos ou vazios de forma elegante.
    """
    partes_texto = []
    # Mapeia o nome da coluna para um rotulo amigavel no texto
    mapeamento_colunas = {
        'nome_convenio': 'Convenio',
        'idade': 'Idade do Paciente',
        'nome_profissional': 'Profissional Responsavel',
        'fonte': 'Fonte do Registro',
        'conjunto': 'Conjunto de Dados',
        'descricao': 'Descricao do Atendimento'
    }

    for coluna, rotulo in mapeamento_colunas.items():
        valor = getattr(row, coluna, None) # Pega o valor da coluna pelo nome
        if valor is not None and str(valor).strip() != '':
            partes_texto.append(f"{rotulo}: {valor}.")
    
    return " ".join(partes_texto)


def process_and_embed_data():
    """
    Busca registros sem embedding, gera o embedding combinado em ordem de ID,
    e atualiza o banco de dados em lotes.
    """
    print("Iniciando processo de embedding...")
    
    # A sua query esta correta, pois precisamos de todas as colunas para o contexto.
    select_query = text("""
        SELECT mpi, cpf, data_nascimento, idade, nome_convenio, data_registro, descricao, nome_profissional, fonte, conjunto, id
        FROM mpi.mpi_jornada_paciete_teste 
        WHERE embedding IS NULL AND descricao IS NOT NULL AND TRIM(descricao) != ''
        ORDER BY id ASC
    """)
    
    update_query = text("""
        UPDATE mpi.mpi_jornada_paciete_teste 
        SET embedding = :embedding 
        WHERE id = :id
    """)

    with engine.connect() as conn:
        transaction = conn.begin()
        try:
            registros_para_processar = conn.execute(select_query).fetchall()
            total_registros = len(registros_para_processar)
            print(f"Encontrados {total_registros} registros para embeddar.")

            for i, row in enumerate(registros_para_processar):
                record_id = row.id
                print(f"Processando registro {i+1}/{total_registros} (ID: {record_id})...")
                
                # 1. Criar o texto combinado a partir das colunas
                contexto_completo = criar_contexto_do_registro(row)
                
                # 2. Gerar o embedding a partir do texto combinado
                embedding_vector = get_embedding(contexto_completo)
                
                if embedding_vector is None:
                    print(f"  -> Aviso: Nao foi possivel gerar contexto ou embedding para o ID {record_id}. Pulando.")
                    continue
                
                # 3. Atualizar o banco de dados
                conn.execute(update_query, {"embedding": embedding_vector, "id": record_id})
                
                if (i + 1) % BATCH_SIZE == 0:
                    transaction.commit()
                    print(f"--- Lote de {BATCH_SIZE} registros comitado com sucesso. ---")
                    transaction = conn.begin()

            transaction.commit()
            print("--- Lote final comitado com sucesso. ---")

        except Exception as e:
            print(f"ERRO CRITICO durante o processamento: {e}")
            print("Revertendo todas as alteracoes nao comitadas (rollback)...")
            transaction.rollback()

    print("Processo de embedding concluido.")

if __name__ == '__main__':
    process_and_embed_data()