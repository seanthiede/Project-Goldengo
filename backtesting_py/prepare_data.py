# prepare_data.py

import pandas as pd

def load_and_prepare_data(file_path):
    """
    Liest eine CSV-Datei, bereinigt sie und bereitet sie für backtesting.py vor.
    Diese Funktion ist so gebaut, dass sie häufige Datenprobleme automatisch löst.
    """
    print(f"--- Starte Datenvorbereitung für: {file_path} ---")

    try:
        # SCHRITT 1: DATEN LADEN
        data = pd.read_csv(file_path, index_col=0)
        
        # =============================================================================
        # NEUER REINIGUNGSSCHRITT: "SCHMUTZIGE" ZEILEN IM INDEX ENTFERNEN
        # =============================================================================
        # Wir versuchen, den Index in eine Zahl umzuwandeln. Alles, was keine Zahl ist
        # (wie das Wort "Ticker" oder andere Texte), wird zu 'NaT' (Not a Time) / 'NaN'.
        # 'errors=coerce' ist der Schlüssel hierfür.
        original_index = data.index
        clean_index = pd.to_datetime(original_index, errors='coerce', utc=True)
        
        # Wir behalten nur die Zeilen, bei denen die Umwandlung erfolgreich war.
        # Alle Zeilen, in denen "Ticker" o.ä. stand, werden hier entfernt.
        data = data[clean_index.notna()]
        
        # Wir weisen den jetzt sauberen Index wieder zu.
        data.index = pd.to_datetime(data.index, utc=True)
        data.index.name = 'Date'
        
        # SCHRITT 3: SPALTENNAMEN STANDARDISIEREN
        data.columns = data.columns.str.lower()
        rename_map = {'price': 'Close', 'adj close': 'Adj Close'}
        data.rename(columns=rename_map, inplace=True)
        data.columns = [col.capitalize() for col in data.columns]

        # SCHRITT 4: DATENTYPEN VALIDIEREN
        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in required_columns:
            if col not in data.columns:
                print(f"❌ FEHLER: Die erwartete Spalte '{col}' wurde nicht gefunden.")
                return None
            data[col] = pd.to_numeric(data[col], errors='coerce')
        
        # SCHRITT 5: DATEN SÄUBERN
        initial_rows = len(data)
        data.dropna(inplace=True)
        
        if len(data) < initial_rows:
            print(f"INFO: {initial_rows - len(data)} Zeilen mit fehlenden Werten wurden entfernt.")

        if data.empty:
            print("❌ FEHLER: Nach der Bereinigung sind keine gültigen Daten mehr übrig.")
            return None

        print("✅ Datenvorbereitung erfolgreich abgeschlossen.")
        return data

    except FileNotFoundError:
        print(f"❌ FEHLER: Die Datei unter dem Pfad '{file_path}' wurde nicht gefunden.")
        return None
    except Exception as e:
        print(f"❌ Ein unerwarteter Fehler ist aufgetreten: {e}")
        return None
