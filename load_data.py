import yfinance as yf
from datetime import datetime
import os

# --- Konfiguration ---
# Hier können Sie einfach Ticker hinzufügen oder das Datum ändern
TICKERS = ["BTC-USD", "ETH-USD"]
START_DATE = "2020-01-01"
# Wir setzen das Enddatum auf heute, um die aktuellsten Daten zu erhalten
END_DATE = datetime.now().strftime("%Y-%m-%d")
DATA_DIR = "data"

# Erstelle den data-Ordner, falls er nicht existiert
os.makedirs(DATA_DIR, exist_ok=True)

print("Starte den Download der Kryptodaten...")
print("-" * 30)

# Wir gehen unsere Liste von Tickern durch und laden die Daten für jeden
for ticker in TICKERS:
    try:
        print(f"Lade Daten für {ticker}")

        # Dateipfad für die CSV-Datei erstellen
        filepath = os.path.join(DATA_DIR, f"{ticker}.csv")

        # Daten herunterladen
        data = yf.download(ticker, start=START_DATE, end=END_DATE)

        # Prüfen, ob Daten heruntergeladen wurden
        if data.empty:
            print(f"WARNUNG: Keine Daten für {ticker} gefunden.")
            print("-" * 40)
            continue

        # Daten in eine CSV-Datei speichern
        data.to_csv(filepath)

        print(f"Erfolgreich {len(data)} Tage an Daten in '{filepath}' gespeichert.")
        print("-" * 40)

    except Exception as e:
        print(f"FEHLER beim Download für {ticker}: {e}")
        print("-" * 40)

print("Alle Downloads abgeschlossen.")