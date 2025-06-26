import os
import pandas as pd
import backtesting
from backtesting import Backtest, Strategy
from prepare_data import load_and_prepare_data
import warnings
import multiprocessing

# Unterdrückt alle UserWarnings aus backtesting/backtesting.py
warnings.filterwarnings(
    'ignore',
    category=UserWarning,
    module=r'backtesting\.backtesting'
)

# Oder gezielter nur jene mit „insufficient margin“
warnings.filterwarnings(
    'ignore',
    message=r'.*relative-sized order due to insufficient margin.*'
)

backtesting.Pool = multiprocessing.Pool

def momentum_indicator(series_data, period):
    """ Hilfsfunktion: Berechnet die prozentuale Rendite über eine gegebene Periode. """
    # 'pct_change' berechnet die prozentuale Veränderung.
    series = pd.Series(series_data)
    return series.pct_change(period)

class TSMOMStrategy(Strategy):
    """
    Implementierung der Time-Series Momentum (TSMOM) Strategie.
    - Kauft, wenn der Trend der letzten 28 Tage positiv ist.
    - Verkauft, wenn der Trend negativ wird.
    - Enthält einen einfachen 15% Stop-Loss.
    """

    # Parameter basierend auf Forschungsergebnissen [10]
    lookback_period = 28
    stop_loss_pct = 0.85 # Stop-Loss 15% unter dem Einstiegspreis
    size_pct = 0.95
    risk_per_trade = 0.01

    def init(self):
        # Berechne Momentum Indikator
        self.momentum = self.I(momentum_indicator, self.data.Close, self.lookback_period)

    def next(self):
         # =================================================================================
        # FINALE KORREKTUR: Wir fügen eine manuelle Prüfung hinzu, bevor wir kaufen.
        # Dies verhindert die "insufficient margin"-Warnungen an der Wurzel.
        # =================================================================================
        price = self.data.Close[-1]
        
        # Prüfe, ob das gesamte Kapital ausreicht, um mindestens eine Einheit zu kaufen.
        if self.equity < price:
            # Wenn nicht, können wir nicht handeln. Breche die Logik für diesen Zeitschritt ab.
            return
        
        m = self.momentum[-1]

        fraction = self.risk_per_trade / (1 - self.stop_loss_pct)

        # Entry mit risikobasierter Grösse und statistischem SL
        if m > 0 and not self.position:
            self.buy(size=fraction, sl=price * self.stop_loss_pct)

        # Trailing Stop und Trend Exit
        elif self.position.is_long:
            # Hoch seit entry finden
            entry_bar = self.trades[-1].entry_bar
            highest = self.data.High[entry_bar:].max()
            # Trailing Stop auf 85% des Hochs setzen
            self.position.sl = highest * self.stop_loss_pct

            # Momentum basierter Exit
            if m < 0:
                self.position.close()
# --------------------------------------------------------------------------
# Schritt 2: Der "Laborroboter" - Hauptteil des Skripts
# --------------------------------------------------------------------------
if __name__ == '__main__':
    # Definiere welchen coin wir testen wollen
    COIN_TO_TEST = 'BTC'

    # Baue Pfad zum richtigen Ordner
    base_dir = os.path.dirname(os.path.abspath(__file__))
    target_folder = os.path.join(base_dir, '..', 'crypto_data', COIN_TO_TEST)

    print(f"=== Starte systematischen Backtest für: {COIN_TO_TEST} ===")
    print(f"Suche nach Datensätzen in: {target_folder}\n")

    # Überprüfe, ob der Ordner existiert
    if not os.path.isdir(target_folder):
        print(f"❌ FEHLER: Der Ordner '{target_folder}' wurde nicht gefunden.")
    else:
        # Finde alle CSV-Dateien im Zielordner
        all_files = [file for file in os.listdir(target_folder) if file.endswith('.csv')]

        if not all_files:
            print(f"⚠️ Keine .csv-Dateien im Ordner '{target_folder}' gefunden.")
        else:
            # Gehe jede gefundene Datei durch
            for filename in sorted(all_files):
                print(f"\n--- Teste jetzt: {filename} ---")
                file_path = os.path.join(target_folder, filename)

                # Lade Daten und bereite sie mit unserer Fnktion vor
                data = load_and_prepare_data(file_path)

                if data is not None and not data.empty:
                    # Führe Backtest für diese eine Datei aus
                    bt = Backtest(
                        data,
                        TSMOMStrategy,
                        cash = 1000000,
                        commission=.002,
                        trade_on_close=True
                    )
                    stats, heatmap = bt.optimize(
                        lookback_period=range(10, 61, 5),
                        stop_loss_pct=[0.8, 0.85, 0.9, 0.95],
                        maximize='Return [%]',
                        return_heatmap=True
                    )

                    print("\n--- ERGEBNISSE ---")
                    # Wir geben nur die wichtigsten Kennzahlen aus, um es übersichtlich zu halten
                    print(stats)

                    # Speichere den Plot als interaktive HTML-Datei, anstatt ihn anzuzeigen
                    plot_filename = f"result_{os.path.splitext(filename)[0]}.html"
                    bt.plot(filename=plot_filename, open_browser=False)
                    print(f"✅ Plot wurde als '{plot_filename}' gespeichert.")
                else:
                    print("-> Test übersprungen wegen eines Daten-Fehlers.")

    print("\n=== Alle Tests abgeschlossen. ===")
