import pandas as pd
import matplotlib.pyplot as plt
from sqlalchemy import create_engine

engine = create_engine(DB_URL)
query = """
SELECT COALESCE(nome_profissional,'Desconhecido') AS medico,
       COUNT(*) AS consultas
FROM mpi.mpi_jornada_paciete_teste
GROUP BY medico
ORDER BY consultas DESC;
"""
df = pd.read_sql(query, engine)

plt.bar(df['medico'], df['consultas'])
plt.xticks(rotation=45, ha='right')
for i, v in enumerate(df['consultas']):
    plt.text(i, v + 0.5, str(v), ha='center')
plt.tight_layout()
plt.savefig('consultas_por_medico.png')
