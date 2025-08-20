import pandas as pd
import matplotlib.pyplot as plt

# Lote de registros
data = [
    {"medico": "Keila Soraya Araujo Costa"},
    {"medico": "Fabiola Rangel Diniz Barbosa"},
    {"medico": "Keila Soraya Araujo Costa"},
    {"medico": "Fabiola Rangel Diniz Barbosa"},
    {"medico": "Taymara Fernanda Nonato"},
    {"medico": "Ang�lica da Silva Rodrigues"},
    {"medico": "Keila Soraya Araujo Costa"},
    {"medico": "Taymara Fernanda Nonato"},
    {"medico": "Taymara Fernanda Nonato"},
    {"medico": "Ang�lica da Silva Rodrigues"},
    {"medico": "Keila Soraya Araujo Costa"},
    {"medico": "Fabiola Rangel Diniz Barbosa"},
    {"medico": "Sabrina Corso Duffrayer"},
    # Adicione mais registros conforme necess�rio
]

# Criar DataFrame
df = pd.DataFrame(data)

# Contar atendimentos por m�dico
atendimentos_por_medico = df['medico'].value_counts()

# Plotar gr�fico
plt.figure(figsize=(10, 6))
atendimentos_por_medico.plot(kind='bar', color='skyblue')
plt.title('N�mero de Atendimentos por M�dico')
plt.xlabel('M�dico')
plt.ylabel('N�mero de Atendimentos')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()