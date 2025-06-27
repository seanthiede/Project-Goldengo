import os
import csv
from datetime import datetime

LOG_DIR = "backtest_results"
os.makedirs(LOG_DIR, exist_ok=True)

def save_result(result_dict, strategy_name):
    """
    Speichert Ergebnisse in einer individuellen CSV-Datei pro Backtest.
    Dateiname enthält Strategie und Zeitstempel.
    """
    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ")
    result_dict["timestamp"] = timestamp
    result_dict["strategy"] = strategy_name

    filename = f"{strategy_name}_{timestamp}.csv"
    filepath = os.path.join(LOG_DIR, filename)
    
    with open(filepath, mode="w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=result_dict.keys())
        writer.writeheader()
        writer.writerow(result_dict)

    print(f"✅ Ergebnis gespeichert: {filepath}")