import yfinance as yf
from datetime import datetime
import os
import time
import pandas as pd
from binance.client import Client

# --- Konfiguration ---
TICKERS_YFINANCE = [
    "BTC-USD", 
    "ETH-USD",
    "XRP-USD", 
    "SOL-USD", 
    "TRX-USD", 
    "ADA-USD"
]

TICKERS_BINANCE = [
    "BTCUSDT", 
    "ETHUSDT", 
    "XRPUSDT", 
    "SOLUSDT", 
    "TRXUSDT", 
    "ADAUSDT"
]




INTERVALS = ["15m", "5m"]

START_DATE_2020 = "2020-01-01"
# Wir setzen das Enddatum auf heute, um die aktuellsten Daten zu erhalten
END_DATE_TODAY = datetime.now()
DATA_DIR = "crypto_data"

binance_client = Client()

# --- HELFERFUNKTION FÜR BINANCE-DOWNLOAD ---
def download_binance_data(symbol, interval, start_str, end_dt):
    """Lädt historische Daten von Binance in Stücken (Chunks) herunter."""
    print(f"  Binance: Lade '{symbol}' mit Intervall '{interval}'...")

    try: 
        # Lade die Daten in einer Schleife, da Binance pro Anfrage limitiert ist
        klines = binance_client.get_historical_klines(
            symbol=symbol,
            interval=interval,
            start_str=start_str,
            end_str=end_dt.strftime("%d %b, %Y %H:%M:%S")
        )
        if not klines:
            print(f"  ⚠️ Keine Daten von Binance für {symbol} erhalten.")
            return None
        
        # Konvertiere die Rohdaten in einen sauberen Pandas DataFrame
        df = pd.DataFrame(klines, columns=[
            'Date', 'Open', 'High', 'Low', 'Close', 'Volume', 
            'CloseTime', 'QuoteAssetVolume', 'NumberofTrades', 
            'TakerBuyBaseAssetVolume', 'TakerBuyQuoteAssetVolume', 'Ignore'
        ])

        # Wichtige Spalten auswählen und Datentypen konvertieren
        df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
        df['Date'] = pd.to_datetime(df['Date'], unit='ms', utc=True)
        for col in df.columns[1:]:
            df[col] = pd.to_numeric(df[col])
        
        df.set_index('Date', inplace=True)
        return df
    
    except:
        print(f" ❌ FEHLER bei Binance-Download für {symbol}: {e}")
        return None
    
print("Starte den hybriden Download von Kryptodaten...")
os.makedirs(DATA_DIR, exist_ok=True)


# Wir gehen unsere Liste von Tickern durch und laden die Daten für jeden
for interval in INTERVALS:
    interval_dir = os.path.join(DATA_DIR, interval)
    os.makedirs(interval_dir, exist_ok=True)
    
    print(f"\n--- Bearbeite Intervall: {interval} ---")

    # Wähle das richtige Werkzeug und die richtige Ticker-Liste
    if interval == "1d":
        print("  -> Werkzeug: yfinance (für tägliche Daten)")
        for ticker in TICKERS_YFINANCE:
            print(f"  Ticker: {ticker}")
            # ANFRAGE 1: Längst möglicher Zeitraum
            try:
                data_max = yf.download(tickers=ticker, period="max", interval="1d", progress=False)
                if not data_max.empty:
                    data_max.to_csv(os.path.join(interval_dir, f"{ticker}_{interval}_max.csv"))
                    print(f"    ✅ MAX: {len(data_max)} Datenpunkte gespeichert.")
            except Exception as e:
                print(f"    ❌ FEHLER (max): {e}")
            time.sleep(1)

            # ANFRAGE 2: Zeitraum ab 2020
            try:
                data_2020 = yf.download(tickers=ticker, start="2020-01-01", end=END_DATE_TODAY, interval="1d", progress=False)
                if not data_2020.empty:
                    data_2020.to_csv(os.path.join(interval_dir, f"{ticker}_{interval}_2020-today.csv"))
                    print(f"    ✅ 2020-heute: {len(data_2020)} Datenpunkte gespeichert.")
            except Exception as e:
                print(f"    ❌ FEHLER (2020-heute): {e}")
            time.sleep(1)

    else: # Für alle Intraday-Intervalle
        print("  -> Werkzeug: python-binance (für Intraday-Daten)")
        for ticker in TICKERS_BINANCE:
            # Lade die vollständige Historie ab 2020
            binance_df = download_binance_data(ticker, interval, START_DATE_2020, END_DATE_TODAY)
            if binance_df is not None:
                # Wir fragen nur einen Zeitraum an, also speichern wir ihn als "full"
                filepath = os.path.join(interval_dir, f"{ticker}_{interval}_full.csv")
                binance_df.to_csv(filepath)
                print(f"  ✅ Erfolgreich {len(binance_df)} Datenpunkte in '{filepath}' gespeichert.")
            time.sleep(2) # Längere Pause für Binance API

print("\n" + "=" * 40)
print("Alle Download-Aufgaben abgeschlossen.")
print(f"Alle Daten wurden im Ordner '{DATA_DIR}' gespeichert.")
print("=" * 40)
