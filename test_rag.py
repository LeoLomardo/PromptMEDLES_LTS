#!/usr/bin/env python3
# coding: utf-8
"""
RAG para PostgreSQL + pgvector (schema mpi) com pipeline map-reduce
- Recupera registros por similaridade (cosine) usando mpi.<=> e mpi.vector
- Monta contexto em lotes (batch) e gera resumos parciais (map)
- Faz uma reducao final (reduce) para responder a pergunta
- CLI interativo: digite sua pergunta; 'sair' para encerrar
"""

import os
import math
import re
from typing import List, Dict, Any, Iterable

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from openai import OpenAI

# =========================
# Config
# =========================
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DB_URL = (
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

# modelos
EMBEDDING_MODEL = "text-embedding-3-small"
GENERATE_MODEL = "gpt-4o-mini"

# retrieval
TOP_K = int(os.getenv("RAG_TOP_K", "200"))      # quantos documentos trazer do banco
BATCH_SIZE = int(os.getenv("RAG_BATCH_SIZE", "40"))  # tamanho do lote para "map"
MAX_MAP_SUMMARY_CHARS = int(os.getenv("RAG_MAP_SUMMARY_CHARS", "3000"))  # limite por resumo

# colunas que vamos projetar da tabela (adicione/ajuste se quiser)
TABLE = "mpi.mpi_jornada_paciete_teste"  # cuidado com o nome exato no seu ambiente
PROJECT_COLS = [
    "id",
    "nome_profissional",
    "nome_convenio",
    "idade",
    "descricao",
]

# =========================
# Clients
# =========================
client = OpenAI(api_key=OPENAI_API_KEY)
engine = create_engine(DB_URL)


# =========================
# Utils
# =========================
def get_embedding(text: str) -> List[float]:
    """Cria embedding para a pergunta."""
    if not text or not text.strip():
        raise ValueError("Pergunta vazia.")
    r = client.embeddings.create(model=EMBEDDING_MODEL, input=[text])
    return r.data[0].embedding


def rows_to_lines(rows: Iterable[Any]) -> List[str]:
    """
    Converte linhas SQL em linhas de texto curtas para contexto.
    Ajuste o formato conforme suas colunas.
    """
    out = []
    for r in rows:
        desc = (r.descricao or "").replace("\n", " ").strip()
        if len(desc) > 200:
            desc = desc[:200] + "..."
        line = (
            f"id={r.id} | medico={r.nome_profissional or 'Desconhecido'} | "
            f"convenio={r.nome_convenio or ''} | idade={r.idade or ''} | "
            f"desc={desc}"
        )
        out.append(line)
    return out


def strip_code_fence(s: str) -> str:
    """Remove cercas ``` de blocos de codigo, se existirem."""
    m = re.search(r"```(?:python)?\n(.*?)```", s, flags=re.S)
    return m.group(1) if m else s


# =========================
# Retrieval no PostgreSQL (pgvector no schema mpi)
# =========================
def retrieve_rows(question: str, top_k: int = TOP_K) -> List[Any]:
    """
    Busca por similaridade usando cosine com operador qualificado:
    embedding OPERATOR(mpi.<=>) CAST(:query_embedding AS mpi.vector)
    """
    q_emb = get_embedding(question)

    proj = ", ".join(PROJECT_COLS)
    sql = text(f"""
        SELECT
            {proj},
            embedding OPERATOR(mpi.<=>) CAST(:qemb AS mpi.vector) AS distance
        FROM {TABLE}
        WHERE embedding IS NOT NULL
        ORDER BY distance ASC
        LIMIT :k
    """)

    with engine.connect() as conn:
        rows = conn.execute(sql, {"qemb": str(q_emb), "k": top_k}).fetchall()
    return rows


# =========================
# Map-Reduce
# =========================
def summarize_batch(question: str, lines: List[str]) -> str:
    """
    Cria resumo focado na pergunta para um lote de linhas.
    Mantem o tamanho sob controle para evitar estouro de contexto.
    """
    # corta se o lote ficou grande demais
    joined = "\n".join(lines)
    if len(joined) > MAX_MAP_SUMMARY_CHARS:
        joined = joined[:MAX_MAP_SUMMARY_CHARS] + "\n...(cortado)"

    messages = [
        {
            "role": "system",
            "content": (
                "Voce e um assistente analitico. "
                "Resuma de forma fiel ao texto, enfatizando fatos relevantes para a pergunta."
            ),
        },
        {
            "role": "user",
            "content": (
                "Pergunta do usuario:\n"
                f"{question}\n\n"
                "Lote de registros (cada linha e um registro):\n"
                f"{joined}\n\n"
                "Tarefa: produza um resumo factual, sucinto e engajado com a pergunta. "
                "Use bullets quando util. Nao invente nada fora dos dados."
            ),
        },
    ]

    resp = client.chat.completions.create(
        model=GENERATE_MODEL, messages=messages, temperature=0.1
    )
    return resp.choices[0].message.content.strip()


def reduce_answer(question: str, batch_summaries: List[str]) -> str:
    """
    Combina os resumos parciais em uma resposta final.
    """
    joined = "\n\n".join(
        f"Resumo {i+1}:\n{bs}" for i, bs in enumerate(batch_summaries)
    )

    messages = [
        {
            "role": "system",
            "content": (
                "Voce e um especialista em analise clinica e dados. "
                "Responda com base SOMENTE nos resumos fornecidos."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Pergunta: {question}\n\n"
                "Considere APENAS os resumos a seguir como sua base de conhecimento. "
                "Se faltar informacao, explique de forma clara.\n\n"
                f"{joined}\n\n"
                "Agora responda a pergunta de forma objetiva e, quando relevante, liste evidencias (por id/medico) "
                "ou sugestoes de consultas SQL agregadas que poderiam validar os achados."
            ),
        },
    ]

    resp = client.chat.completions.create(
        model=GENERATE_MODEL, messages=messages, temperature=0.2
    )
    return resp.choices[0].message.content.strip()


def rag_answer(question: str) -> str:
    """
    Pipeline completo:
    1) retrieval TOP_K
    2) map (resumo por lote de linhas)
    3) reduce (resposta final)
    """
    rows = retrieve_rows(question, top_k=TOP_K)
    if not rows:
        return "Nao encontrei registros relevantes."

    # transforma em linhas curtas
    lines = rows_to_lines(rows)

    # divide em lotes
    batches = [lines[i : i + BATCH_SIZE] for i in range(0, len(lines), BATCH_SIZE)]

    # etapa map
    batch_summaries = []
    for b in batches:
        s = summarize_batch(question, b)
        batch_summaries.append(s)

    # etapa reduce
    final = reduce_answer(question, batch_summaries)
    return final


# =========================
# CLI
# =========================
def main():
    print("RAG pronto. Digite sua pergunta (ou 'sair' para encerrar).")
    while True:
        try:
            q = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nEncerrando.")
            break
        if not q:
            continue
        if q.lower() in {"sair", "exit", "quit"}:
            print("Tchau!")
            break

        try:
            ans = rag_answer(q)
            print("\n==== RESPOSTA ====\n")
            print(ans)
            print("\n==================\n")
        except Exception as e:
            print(f"Erro: {e}")


if __name__ == "__main__":
    main()
