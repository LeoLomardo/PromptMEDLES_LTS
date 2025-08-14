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