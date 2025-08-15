import matplotlib.pyplot as plt
from collections import Counter

consultas = [
    "Miguel Oliveira Neves",  
    "Miguel Oliveira Neves",  
    "Rejane Helena Fagundes Murta",  
    "Leonara Casqueira de Oliveira Castanheira",  
    "Isabella de Forneiro", 
    "Rizia Andrade Protes Faria", 
    "Fabiola Rangel Diniz Barbosa",  
    "Leonara Casqueira de Oliveira Castanheira",  
    "Rejane Helena Fagundes Murta",  
    "Miguel Oliveira Neves"  
]

contador_consultas = Counter(consultas)

medicos = list(contador_consultas.keys())
num_consultas = list(contador_consultas.values())

plt.figure(figsize=(10, 6))
plt.bar(medicos, num_consultas, color='skyblue')
plt.xlabel('Medico Responsavel')
plt.ylabel('Numero de Consultas')
plt.title('Numero de Consultas por Medico Responsavel')
plt.xticks(rotation=45, ha='right')
plt.tight_layout()

plt.show()