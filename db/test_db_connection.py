import psycopg2
from dotenv import load_dotenv
import os

# Carrega variáveis do .env
load_dotenv()

# Pega os dados
db_config = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": os.getenv("DB_PORT")
}

try:
    # Conecta ao banco
    conn = psycopg2.connect(**db_config)
    print("✅ Conexão bem-sucedida!")

    # Testa um comando simples
    cur = conn.cursor()
    cur.execute("SELECT NOW();")
    resultado = cur.fetchone()
    print("🕒 Hora atual no banco:", resultado)

    # Encerra conexão
    cur.close()
    conn.close()

except Exception as e:
    print("❌ Erro ao conectar:", e)
