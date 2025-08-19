import io
import base64
import matplotlib
import matplotlib.pyplot as plt
from collections import Counter 
from datetime import datetime 

event_dates = [
    "2025-02-25", "2025-03-20", "2024-12-23", "2025-01-02", "2024-12-23", 
    "2024-12-26", "2024-12-26", "2025-01-02", "2025-02-19", "2025-01-10", 
    "2025-06-17", "2025-07-21", "2025-08-06", "2025-08-18", "2025-08-06", 
    "2025-07-21", "2025-06-17", "2025-07-21", "2025-07-21", "2025-08-06", 
    "2024-12-23", "2024-12-26", "2024-12-26", "2025-01-02", "2025-01-02", 
    "2024-12-26", "2024-12-23", "2025-05-15", "2025-07-21", "2025-02-27", 
    "2025-01-17", "2024-12-26", "2025-01-22", "2025-06-26", "2025-02-27", 
    "2025-02-24", "2025-01-16", "2025-02-24", "2025-01-22", "2025-03-20", 
    "2025-05-15", "2025-06-17", "2025-07-21", "2025-08-06", "2025-07-21", 
    "2025-07-21", "2025-08-06", "2025-07-21", "2025-06-17", "2025-02-24", 
    "2025-08-06", "2025-07-21", "2025-06-17", "2025-02-24"
]

event_months = [datetime.strptime(date, "%Y-%m-%d").strftime("%Y-%m") for date in event_dates]

event_count = Counter(event_months)

months = sorted(event_count.keys())
counts = [event_count[month] for month in months]

plt.figure(figsize=(10, 5))
plt.bar(months, counts, color='skyblue')
plt.xlabel('Mes')
plt.ylabel('Numero de Eventos')
plt.title('Numero de Eventos por Mes')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()