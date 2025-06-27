import os
import pandas as pd
import backtesting
from backtesting import Backtest, Strategy
from project_goldengo.prepare_data import load_and_prepare_data
import warnings
import multiprocessing
from project_goldengo.saved_output import save_result

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
    COIN = 'BTC'
    print(f"=== Backtest TSMOMStrategy für {COIN} ===")

    # Pfad zum crypto_data-Ordner (eine Ebene oberhalb des Projekt-Pakets)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, '..'))
    data_root = os.path.join(project_root, 'crypto_data', COIN)

    if not os.path.isdir(data_root):
        print(f"⚠️ Verzeichnis nicht gefunden: {data_root}")
        exit(1)

    csv_files = sorted(
        os.path.join(data_root, fname)
        for fname in os.listdir(data_root)
        if fname.endswith('.csv') and fname.upper().startswith(COIN)
    )

    if not csv_files:
        print(f"⚠️ Keine CSV-Dateien für '{COIN}' in '{data_root}' gefunden.")
        exit(1)

    for filepath in csv_files:
        name = os.path.splitext(os.path.basename(filepath))[0]
        print(f"\n--- Datei: {name} ---")

        df = load_and_prepare_data(filepath)
        if df is None or df.empty:
            print("-> Übersprungen: keine Daten.")
            continue

        bt = Backtest(
            df,
            TSMOMStrategy,
            cash=1_000_000,
            commission=0.002,
            trade_on_close=True
        )
        stats, heatmap = bt.optimize(
            lookback_period=range(10, 61, 5),
            stop_loss_pct=[0.8, 0.85, 0.9, 0.95],
            maximize='Return [%]',
            return_heatmap=True
        )

        print("\n--- Ergebnisse ---")
        print(stats)

        # Speichern
        strategy_name = f"TSMOM_{COIN}_{name}"
        save_result(stats.to_dict(), strategy_name + '_metrics')
        heatmap.to_csv(os.path.join('backtest_results', f"{strategy_name}_heatmap.csv"))
        save_result({'script': __file__}, strategy_name + '_settings')

        # Chart speichern
        bt.plot(filename=f"{strategy_name}.html", open_browser=False)
        print(f"✅ Chart gespeichert als {strategy_name}.html")

    print("\n=== Fertig ===")
