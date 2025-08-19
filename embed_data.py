import os
from dotenv import load_dotenv
from openai import OpenAI
from sqlalchemy import create_engine, text
import numpy as np

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
DB_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
engine = create_engine(DB_URL)

EMBEDDING_MODEL = "text-embedding-3-small"

def get_embedding(text_to_embed):
    """Gera um embedding para o texto fornecido."""
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=[text_to_embed]
    )
    return response.data[0].embedding

def process_and_embed_data():
    print("Iniciando processo de embedding...")
    
    select_query = text("""
        SELECT id, descricao 
        FROM mpi.mpi_jornada_paciete_teste 
        WHERE embedding IS NULL AND descricao IS NOT NULL AND TRIM(descricao) != ''
    """)
    
    update_query = text("""
        UPDATE mpi.mpi_jornada_paciete_teste 
        SET embedding = :embedding 
        WHERE id = :id
    """)

    with engine.connect() as conn:
        registros_para_processar = conn.execute(select_query).fetchall()
        print(f"Encontrados {len(registros_para_processar)} registros para embeddar.")

        for i, row in enumerate(registros_para_processar):
            record_id, description = row[0], row[1]
            
            try:
                print(f"Processando registro {i+1}/{len(registros_para_processar)} (ID: {record_id})...")
                
                embedding_vector = get_embedding(description)
                
                embedding_np = np.array(embedding_vector)
                
                embedding_list = embedding_np.tolist()
                
                conn.execute(update_query, {
                    "embedding": embedding_list, # Envia a lista em vez do array numpy
                    "id": record_id
                })
                conn.commit()

            except Exception as e:
                print(f"Erro ao processar registro ID {record_id}: {e}")
                conn.rollback()

    print("Processo de embedding concluido.")

if __name__ == '__main__':
    process_and_embed_data()