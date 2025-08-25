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
            FROM mpiv02.events  
            WHERE id_paciente = :pid
            ORDER BY id_paciente ASC
        """), {"pid": patient_id}).fetchall()
        return [dict(row._mapping) for row in result]


def buscar_convenios():
    with engine.connect() as conn:
        query = text("""
            SELECT DISTINCT nome_convenio
            FROM mpiv02.events
            WHERE nome_convenio IS NOT NULL
            ORDER BY nome_convenio;
        """)
        result = conn.execute(query).fetchall()
        return [row[0] for row in result]

def buscar_profissionais():
    with engine.connect() as conn:
        query = text("""
            SELECT DISTINCT nome_profissional
            FROM mpiv02.events
            WHERE nome_profissional IS NOT NULL
            ORDER BY nome_profissional;
        """)
        result = conn.execute(query).fetchall()
        return [row[0] for row in result]

def busca_conjunto():
        with engine.connect() as conn:
            query = text("""
                SELECT DISTINCT conjunto
                FROM mpiv02.events
                WHERE conjunto IS NOT NULL
                ORDER BY conjunto;
            """)
            result = conn.execute(query).fetchall()
            return [row[0] for row in result]

#funcao filtra pacientes considerando idade, convenio E/OU profissional responsavel
def filtrar_pacientes(idade_min: int = None, idade_max: int = None, convenios: list = None, profissionais: list = None, conjuntos: list = None):

    if idade_min is None and idade_max is None and not convenios and not profissionais and not conjuntos:
        return []

    with engine.connect() as conn:
        params = {}
        
        subquery_conditions = []
        if convenios:
            subquery_conditions.append("nome_convenio = ANY(:convenios)")
            params["convenios"] = convenios
        if profissionais:
            subquery_conditions.append("nome_profissional = ANY(:profissionais)")
            params["profissionais"] = profissionais
        if conjuntos:
            subquery_conditions.append("conjunto = ANY(:conjuntos)")
            params["conjuntos"] = conjuntos

        mpi_filter_subquery = ""
        if subquery_conditions:
            mpi_filter_subquery = f"""
                AND t.id_paciente IN (
                    SELECT DISTINCT id_paciente
                    FROM mpiv02.events
                    WHERE {' AND '.join(subquery_conditions)}
                )
            """

        having_clause = ""
        if idade_min is not None and idade_max is not None:
            having_clause = "HAVING EXTRACT(YEAR FROM AGE(NOW(), t.data_nascimento)) BETWEEN :idade_min AND :idade_max"
            params["idade_min"] = idade_min
            params["idade_max"] = idade_max

        main_query_sql = f"""
            SELECT
                t.id_paciente,
                EXTRACT(YEAR FROM AGE(NOW(), t.data_nascimento)) AS idade_calculada,
                COUNT(*) AS total_eventos
            FROM
                mpiv02.events t
            WHERE
                t.data_nascimento IS NOT NULL
                {mpi_filter_subquery}
            GROUP BY
                t.id_paciente, t.data_nascimento
            {having_clause}
            ORDER BY
                t.id_paciente;
        """

        query = text(main_query_sql)
        
        result = conn.execute(query, params).fetchall()
        return [dict(row._mapping) for row in result]