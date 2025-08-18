import os
import json
from sqlalchemy import create_engine, text, bindparam
from sqlalchemy.exc import OperationalError
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv()

DB_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"

engine = create_engine(DB_URL, pool_pre_ping=True)

def buscar_jornada_por_id(patient_id: str):
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT *
            FROM mpi.mpi_jornada_paciete  
            WHERE mpi = :pid
            ORDER BY mpi ASC
        """), {"pid": patient_id}).fetchall()
        return [dict(row._mapping) for row in result]


#funcao filtra pacientes apenas considerando intervalo de idade, atualmente ele ordena pelo mpi, mas pode mudar pro q julgarem mais valido.
def filtrar_pacientes_por_idade(idade_min: int, idade_max: int):
    with engine.connect() as conn:
       
        query = text("""
            SELECT
                mpi,
                EXTRACT(YEAR FROM AGE(NOW(), data_nascimento)) AS idade_calculada
            FROM
                mpi.mpi_jornada_paciete
            WHERE
                data_nascimento IS NOT NULL
            GROUP BY
                mpi, data_nascimento
            HAVING
                EXTRACT(YEAR FROM AGE(NOW(), data_nascimento)) BETWEEN :idade_min AND :idade_max
            ORDER BY
                mpi;
        """)
        
        result = conn.execute(query, {"idade_min": idade_min, "idade_max": idade_max}).fetchall()
        return [dict(row._mapping) for row in result]