import pandas as pd
import matplotlib.pyplot as plt

# Lote de registros
data = [
    {"medico": "Keila Soraya Araujo Costa"},
    {"medico": "Fabiola Rangel Diniz Barbosa"},
    {"medico": "Keila Soraya Araujo Costa"},
    {"medico": "Fabiola Rangel Diniz Barbosa"},
    {"medico": "Taymara Fernanda Nonato"},
    {"medico": "Angélica da Silva Rodrigues"},
    {"medico": "Keila Soraya Araujo Costa"},
    {"medico": "Taymara Fernanda Nonato"},
    {"medico": "Taymara Fernanda Nonato"},
    {"medico": "Angélica da Silva Rodrigues"},
    {"medico": "Keila Soraya Araujo Costa"},
    {"medico": "Fabiola Rangel Diniz Barbosa"},
    {"medico": "Sabrina Corso Duffrayer"},
    # Adicione mais registros conforme necessário
]

# Criar DataFrame
df = pd.DataFrame(data)

# Contar atendimentos por médico
atendimentos_por_medico = df['medico'].value_counts()

# Plotar gráfico
plt.figure(figsize=(10, 6))
atendimentos_por_medico.plot(kind='bar', color='skyblue')
plt.title('Número de Atendimentos por Médico')
plt.xlabel('Médico')
plt.ylabel('Número de Atendimentos')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()