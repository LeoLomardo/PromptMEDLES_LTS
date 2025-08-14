import os
import json
from sqlalchemy import create_engine, text, bindparam
from sqlalchemy.exc import OperationalError
from dotenv import load_dotenv
from collections import defaultdict


# Carrega variáveis do .env
load_dotenv()

# Monta a URL do banco de dados
DB_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"

# Cria engine
engine = create_engine(DB_URL, pool_pre_ping=True)


##################################################################################################################

def buscar_jornada_pacientes(limit: int = 3000):
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT patient_mpi_id,
                   tipo,
                   data,
                   observacao,
                   local,
                   profissional,
                   status,
                   fonte
            FROM mpi_jornada_paciente.mpi_jornada_paciente
            ORDER BY patient_mpi_id ASC
            LIMIT :limite
        """), {"limite": limit}).fetchall()
        return [dict(row._mapping) for row in result]


def buscar_observacoes(limit: int = 3000):
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT patient_mpi_id,
                   data,
                   observacao,
                   local,
                   profissional,
                   status,
                   fonte
            FROM mpi_jornada_paciente.mpi_jornada_paciente
            WHERE observacao IS NOT NULL
            ORDER BY patient_mpi_id ASC
            LIMIT :limite
        """), {"limite": limit}).fetchall()
        return [dict(row._mapping) for row in result]


def stream_observacoes(batch_size: int = 1000):
    """
    Itera toda a tabela em chunks de tamanho batch_size,
    retornando dicionários com patient_mpi_id, data e observacao.
    """
    offset = 0
    while True:
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT patient_mpi_id,
                           data,
                           observacao
                    FROM mpi_jornada_paciente.mpi_jornada_paciente
                    WHERE observacao IS NOT NULL
                    ORDER BY patient_mpi_id ASC
                    LIMIT :limit OFFSET :offset
                """),
                {"limit": batch_size, "offset": offset}
            ).fetchall()
            if not result:
                break
            for row in result:
                yield dict(row._mapping)
        offset += batch_size

############################################################################################################

def buscar_jornada_por_id(patient_id: str):
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT *
            FROM mpi.mpi_jornada_paciete  
            WHERE mpi = :pid
            ORDER BY mpi ASC
        """), {"pid": patient_id}).fetchall()
        return [dict(row._mapping) for row in result]