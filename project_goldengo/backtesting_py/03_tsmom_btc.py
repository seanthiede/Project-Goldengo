import os
import pandas as pd
import backtesting
from backtesting import Backtest, Strategy
from project_goldengo.prepare_data import load_and_prepare_data
import warnings
import multiprocessing
from project_goldengo.saved_output import save_backtest_outputs

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
    """Berechnet die prozentuale Rendite über eine gegebene Periode."""
    return pd.Series(series_data).pct_change(period)


class TSMOMStrategy(Strategy):
    """
    Time-Series Momentum (TSMOM) Strategie:
    - Kauft, wenn der Trend der letzten Tage positiv ist.
    - Verkauft bei negativem Trend.
    - Enthält einen 15% Stop-Loss.
    """
    lookback_period = 28
    stop_loss_pct = 0.85
    risk_per_trade = 0.01

    def init(self):
        self.momentum = self.I(momentum_indicator, self.data.Close, self.lookback_period)

    def next(self):
        price = self.data.Close[-1]
        # Verhindere Trades, wenn nicht genug Kapital für mindestens eine Einheit
        if self.equity < price:
            return

        m = self.momentum[-1]
        sl_price = price * self.stop_loss_pct
        risk_fraction = self.risk_per_trade / (1 - self.stop_loss_pct)

        # Entry
        if m > 0 and not self.position:
            self.buy(size=risk_fraction, sl=sl_price)

        # Trailing Stop & Exit
        elif self.position.is_long:
            entry_bar = self.trades[-1].entry_bar
            highest = self.data.High[entry_bar:].max()
            self.position.sl = highest * self.stop_loss_pct
            if m < 0:
                self.position.close()


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

        # Basis-Backtest ohne Optimierung
        stats = bt.run()

        print("\n--- Ergebnisse ---")
        print(stats)

        # Speichern aller Outputs via Helper
        strategy_name = f"TSMOM_{COIN}_{name}"
        save_backtest_outputs(bt, stats, strategy_name, filepath)

    print("\n=== Fertig ===")
