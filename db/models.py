import os
import json
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from dotenv import load_dotenv
from collections import defaultdict


load_dotenv()

DB_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"

engine = create_engine(DB_URL, pool_pre_ping=True)


def buscar_jornada_por_id(patient_id: str):
    """
    Busca todos os eventos (jornada) de um paciente especifico pelo seu ID.
    
    Args:
        patient_id (str): O ID unico do paciente.
        
    Returns:
        list: Uma lista de dicionarios, onde cada dicionario representa um evento.
    """
    # Abre uma conexao com o banco de dados.
    with engine.connect() as conn:
        # Define a consulta SQL para buscar eventos de um paciente.
        query = text("""
            SELECT 
                *
            FROM 
                mpiv02.events  
            WHERE 
                id_paciente = :pid
            ORDER BY 
                id_paciente ASC
        """)
        # Executa a consulta, passando o ID do paciente como parametro para evitar SQL Injection.
        result = conn.execute(query, {"pid": patient_id}).fetchall()
        
        # Converte o resultado (lista de tuplas) em uma lista de dicionarios.
        return [dict(row._mapping) for row in result]


def buscar_convenios():
    """
    Busca todos os nomes de convenios unicos existentes na tabela de eventos.
    
    Returns:
        list: Uma lista de strings com os nomes dos convenios.
    """
    with engine.connect() as conn:
        query = text("""
            SELECT DISTINCT 
                nome_convenio
            FROM 
                mpiv02.events
            WHERE 
                nome_convenio IS NOT NULL
            ORDER BY 
                nome_convenio;
        """)
        result = conn.execute(query).fetchall()
        
        return [row[0] for row in result]


def buscar_profissionais():
    """
    Busca todos os nomes de profissionais unicos existentes na tabela de eventos.
    
    Returns:
        list: Uma lista de strings com os nomes dos profissionais.
    """
    with engine.connect() as conn:
        query = text("""
            SELECT DISTINCT 
                nome_profissional
            FROM 
                mpiv02.events
            WHERE 
                nome_profissional IS NOT NULL
            ORDER BY 
                nome_profissional;
        """)
        result = conn.execute(query).fetchall()
        
        return [row[0] for row in result]


def busca_conjunto():
    """
    Busca todos os nomes de conjuntos unicos existentes na tabela de eventos.
    
    Returns:
        list: Uma lista de strings com os nomes dos conjuntos.
    """
    with engine.connect() as conn:
        query = text("""
            SELECT DISTINCT 
                conjunto
            FROM 
                mpiv02.events
            WHERE 
                conjunto IS NOT NULL
            ORDER BY 
                conjunto;
        """)
        result = conn.execute(query).fetchall()
        
        # Retorna uma lista simples com os nomes dos conjuntos.
        return [row[0] for row in result]


def filtrar_pacientes(idade_min: int = None, idade_max: int = None, convenios: list = None, profissionais: list = None, conjuntos: list = None, termos_busca: list = None):
    """
    Filtra pacientes com base em uma combinacao de criterios.
    
    Args:
        idade_min (int, optional): Idade minima do paciente.
        idade_max (int, optional): Idade maxima do paciente.
        convenios (list, optional): Lista de nomes de convenios para filtrar.
        profissionais (list, optional): Lista de nomes de profissionais.
        conjuntos (list, optional): Lista de nomes de conjuntos.
        termos_busca (list, optional): Lista de termos para buscar na descricao dos eventos.
        
    Returns:
        list: Uma lista de dicionarios, cada um representando um paciente que
              corresponde aos filtros, com seu ID, idade e total de eventos.
    """

    # Se nenhum filtro for fornecido, retorna uma lista vazia para evitar
    # uma consulta desnecessariamente pesada ao banco.
    if idade_min is None and idade_max is None and not convenios and not profissionais and not conjuntos and not termos_busca:
        return []

    with engine.connect() as conn:
        # Dicionario para armazenar os parametros da consulta de forma segura.
        params = {}
        
        # Lista para construir as condicoes da subquery dinamicamente.
        subquery_conditions = []
        
        # Adiciona condicoes para filtros baseados em listas (convenios, profissionais, conjuntos).
        if convenios:
            subquery_conditions.append("nome_convenio = ANY(:convenios)")
            params["convenios"] = convenios
        if profissionais:
            subquery_conditions.append("nome_profissional = ANY(:profissionais)")
            params["profissionais"] = profissionais
        if conjuntos:
            subquery_conditions.append("conjunto = ANY(:conjuntos)")
            params["conjuntos"] = conjuntos
        
        # Adiciona condicoes para busca por termos na descricao do evento.
        if termos_busca:
            for i, termo in enumerate(termos_busca):
                param_name = f"termo_{i}"
                # A condicao busca o termo em qualquer lugar da descricao (case-insensitive ILIKE).
                subquery_conditions.append(f"""
                    id_paciente IN (
                        SELECT id_paciente FROM mpiv02.events WHERE descricao ILIKE :{param_name}
                    )
                """)
                params[param_name] = f"%{termo}%"

        # Monta o trecho SQL da subquery se alguma condicao foi adicionada.
        mpi_filter_subquery = ""
        if subquery_conditions:
            mpi_filter_subquery = f"""
                AND t.id_paciente IN (
                    SELECT DISTINCT id_paciente
                    FROM mpiv02.events
                    WHERE {' AND '.join(subquery_conditions)}
                )
            """

        # Monta a clausula HAVING para filtrar por faixa de idade, se aplicavel.
        # HAVING e usado porque a idade e calculada apos o agrupamento (GROUP BY).
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
        
        # Converte o resultado para uma lista de dicionarios e a retorna.
        return [dict(row._mapping) for row in result]