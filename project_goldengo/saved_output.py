import os
import csv
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt

# Basisverzeichnis für alle Outputs
LOG_DIR = "backtest_results"
os.makedirs(LOG_DIR, exist_ok=True)


def save_metrics(stats, strategy_name, file_stem):
    """
    Speichert die wichtigsten Kennzahlen eines Backtests als CSV.
    Inkl. Buy & Hold Return, Return, Sharpe, Max Drawdown, CAGR, Volatility, Trades und Win Rate.
    """
    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ")
    metrics = {
        'timestamp': timestamp,
        'strategy': strategy_name,
        'Return [%]': stats['Return [%]'],
        'Buy & Hold Return [%]': stats['Buy & Hold Return [%]'],
        'Sharpe Ratio': stats.get('Sharpe Ratio', float('nan')),
        'CAGR [%]': stats.get('CAGR [%]', float('nan')),
        'Volatility (Ann.) [%]': stats.get('Volatility (Ann.) [%]', float('nan')),
        'Max Drawdown [%]': stats.get('Max. Drawdown [%]', float('nan')),
        'Num Trades': stats.get('# Trades', float('nan')),
        'Win Rate [%]': stats.get('Win Rate [%]', float('nan'))
    }
    filepath = os.path.join(LOG_DIR, f"{file_stem}_metrics_{timestamp}.csv")
    pd.DataFrame([metrics]).to_csv(filepath, index=False)
    print(f"✅ Kennzahlen gespeichert: {filepath}")


def save_equity_curve(stats, file_stem):
    """Speichert die Equity-Kurve des Backtests als CSV."""
    eq = stats._equity_curve
    filepath = os.path.join(LOG_DIR, f"{file_stem}_equity_curve.csv")
    eq.to_csv(filepath)
    print(f"✅ Equity Curve gespeichert: {filepath}")


def save_trades(stats, file_stem):
    """Speichert alle Trades des Backtests als CSV."""
    trades = stats._trades
    filepath = os.path.join(LOG_DIR, f"{file_stem}_trades.csv")
    trades.to_csv(filepath, index=False)
    print(f"✅ Trades gespeichert: {filepath}")


def save_chart(bt, stats, file_stem):
    """Erzeugt und speichert den Chart des Backtests als PNG-Datei."""
    figs = bt.plot()
    if figs:
        fig = figs[0]
        filepath = os.path.join(LOG_DIR, f"{file_stem}_equity_chart.png")
        fig.savefig(filepath)
        plt.close(fig)
        print(f"✅ Chart gespeichert: {filepath}")


def save_backtest_outputs(bt, stats, strategy_name, file_path):
    """
    Konsolidierte Funktion, um alle Outputs eines Backtests zu speichern:
    - Metrics (inkl. Buy & Hold)
    - Equity Curve
    - Trades
    - Chart

    `file_path` wird als Basisname verwendet (ohne Extension).
    """
    # Basisname aus Pfad
    file_stem = os.path.splitext(os.path.basename(file_path))[0]
    # Speichern
    save_metrics(stats, strategy_name, file_stem)
    save_equity_curve(stats, file_stem)
    save_trades(stats, file_stem)
    save_chart(bt, stats, file_stem)