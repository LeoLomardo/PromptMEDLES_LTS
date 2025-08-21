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
            FROM mpi.mpi_jornada_paciete_teste  
            WHERE mpi = :pid
            ORDER BY mpi ASC
        """), {"pid": patient_id}).fetchall()
        return [dict(row._mapping) for row in result]


def buscar_convenios():
    with engine.connect() as conn:
        query = text("""
            SELECT DISTINCT nome_convenio
            FROM mpi.mpi_jornada_paciete_teste
            WHERE nome_convenio IS NOT NULL
            ORDER BY nome_convenio;
        """)
        result = conn.execute(query).fetchall()
        return [row[0] for row in result]

def buscar_profissionais():
    with engine.connect() as conn:
        query = text("""
            SELECT DISTINCT nome_profissional
            FROM mpi.mpi_jornada_paciete_teste
            WHERE nome_profissional IS NOT NULL
            ORDER BY nome_profissional;
        """)
        result = conn.execute(query).fetchall()
        return [row[0] for row in result]


#funcao filtra pacientes considerando idade, convenio E/OU profissional responsavel
def filtrar_pacientes(idade_min: int = None, idade_max: int = None, convenios: list = None, profissionais: list = None):

    # Se nenhum filtro for aplicado, retorna uma lista vazia para evitar buscar todos os pacientes.
    if idade_min is None and idade_max is None and not convenios and not profissionais:
        return []

    with engine.connect() as conn:
        params = {}
        
        # --- Subquery para encontrar MPIs que correspondem a convênio/profissional ---
        subquery_conditions = []
        if convenios:
            subquery_conditions.append("nome_convenio = ANY(:convenios)")
            params["convenios"] = convenios
        if profissionais:
            subquery_conditions.append("nome_profissional = ANY(:profissionais)")
            params["profissionais"] = profissionais

        mpi_filter_subquery = ""
        # Só cria a subquery se houver filtros de convênio ou profissional
        if subquery_conditions:
            mpi_filter_subquery = f"""
                AND t.mpi IN (
                    SELECT DISTINCT mpi
                    FROM mpi.mpi_jornada_paciete_teste
                    WHERE {' AND '.join(subquery_conditions)}
                )
            """

        # --- Query Principal ---
        # Cláusula HAVING para idade será adicionada dinamicamente
        having_clause = ""
        if idade_min is not None and idade_max is not None:
            having_clause = "HAVING EXTRACT(YEAR FROM AGE(NOW(), t.data_nascimento)) BETWEEN :idade_min AND :idade_max"
            params["idade_min"] = idade_min
            params["idade_max"] = idade_max

        main_query_sql = f"""
            SELECT
                t.mpi,
                EXTRACT(YEAR FROM AGE(NOW(), t.data_nascimento)) AS idade_calculada
            FROM
                mpi.mpi_jornada_paciete_teste t
            WHERE
                t.data_nascimento IS NOT NULL
                {mpi_filter_subquery}
            GROUP BY
                t.mpi, t.data_nascimento
            {having_clause}
            ORDER BY
                t.mpi;
        """

        query = text(main_query_sql)
        
        result = conn.execute(query, params).fetchall()
        return [dict(row._mapping) for row in result]