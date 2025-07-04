import os, sys
# Füge das Elternverzeichnis zu sys.path hinzu
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import glob
import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
from project_goldengo.prepare_data import load_and_prepare_data
from project_goldengo.saved_output import save_result  # Ergebnisse abspeichern

# --- Hilfsfunktionen für Indikatoren ---
def ema(arr, span):
    arr = np.array(arr, dtype=float)
    alpha = 2 / (span + 1)
    ema_arr = np.empty_like(arr)
    ema_arr[0] = arr[0]
    for i in range(1, len(arr)):
        ema_arr[i] = alpha * arr[i] + (1 - alpha) * ema_arr[i-1]
    return ema_arr

def sma(arr, period):
    arr = np.array(arr, dtype=float)
    sma_arr = np.full_like(arr, np.nan)
    cumsum = np.cumsum(arr)
    for i in range(period - 1, len(arr)):
        sma_arr[i] = (cumsum[i] - (cumsum[i - period] if i >= period else 0)) / period
    return sma_arr

def rsi_func(arr, period):
    arr = np.array(arr, dtype=float)
    delta = np.diff(arr, prepend=arr[0])
    gains = np.where(delta > 0, delta, 0)
    losses = np.where(delta < 0, -delta, 0)
    avg_gain = np.full_like(arr, np.nan)
    avg_loss = np.full_like(arr, np.nan)
    avg_gain[period] = np.mean(gains[1:period+1])
    avg_loss[period] = np.mean(losses[1:period+1])
    for i in range(period+1, len(arr)):
        avg_gain[i] = (avg_gain[i-1] * (period-1) + gains[i]) / period
        avg_loss[i] = (avg_loss[i-1] * (period-1) + losses[i]) / period
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def obv_func(close, volume):
    close = np.array(close, dtype=float)
    volume = np.array(volume, dtype=float)
    obv = np.zeros_like(close)
    for i in range(1, len(close)):
        if close[i] > close[i-1]:
            obv[i] = obv[i-1] + volume[i]
        elif close[i] < close[i-1]:
            obv[i] = obv[i-1] - volume[i]
        else:
            obv[i] = obv[i-1]
    return obv

class DynamicMomentumCrossover(Strategy):
    fast_ema = 20
    medium_ema = 50
    slow_ema = 200
    rsi_period = 14
    rsi_threshold = 75
    obv_sma_period = 20
    atr_period = 14
    atr_multiple = 2.0
    risk_per_trade = 0.01  # 1% des Kapitals

    def init(self):
        price = self.data.Close
        self.ema_fast = self.I(ema, price, self.fast_ema)
        self.ema_medium = self.I(ema, price, self.medium_ema)
        self.ema_slow = self.I(ema, price, self.slow_ema)
        self.rsi = self.I(rsi_func, price, self.rsi_period)
        self.obv = self.I(obv_func, self.data.Close, self.data.Volume)
        self.obv_sma = self.I(sma, self.obv, self.obv_sma_period)
        span = self.atr_period
        self.atr = self.I(
            lambda hi, lo: np.convolve(np.abs(np.array(hi) - np.array(lo)),
                                       np.ones(span) / span, mode='same'),
            self.data.High, self.data.Low
        )
        self.stop_price = None

    def next(self):
        price = self.data.Close[-1]
        if not self.position:
            if price <= self.ema_slow[-1]: return
            if not crossover(self.ema_fast, self.ema_medium): return
            if self.rsi[-1] >= self.rsi_threshold: return
            if self.obv[-1] <= self.obv_sma[-1]: return
            atr_val = self.atr[-1]
            stop_dist = atr_val * self.atr_multiple
            risk_amount = self.equity * self.risk_per_trade
            if stop_dist <= 0 or np.isnan(stop_dist): return
            size = risk_amount / stop_dist
            if size > 1: size = int(size)
            if size <= 0: return
            self.buy(size=size)
            self.stop_price = price - stop_dist
        else:
            atr_val = self.atr[-1]
            new_stop = price - atr_val * self.atr_multiple
            if new_stop > self.stop_price: self.stop_price = new_stop
            if crossover(self.ema_medium, self.ema_fast) or price < self.stop_price:
                self.position.close()

if __name__ == '__main__':
    # BTC CSV-Dateien automatisch einlesen
    csv_dir = os.path.join('crypto_data', 'BTC')
    files = sorted(glob.glob(os.path.join(csv_dir, '*.csv')))

    for file in files:
        print(f"--- Starte Backtest für: {file} ---")
        df = load_and_prepare_data(file)
        if df is None or df.empty:
            print("Datei konnte nicht vorbereitet werden oder ist leer. Überspringe.")
            continue

        # Backtest initialisieren
        bt = Backtest(df,
                      DynamicMomentumCrossover,
                      cash=1000000,
                      commission=0.002,
                      exclusive_orders=True)

        # Basis-Backtest
        stats = bt.run()
        base_result = {
            'file': os.path.basename(file),
            'Return [%]': stats['Return [%]'],
            'Equity Final [$]': stats['Equity Final [$]'],
            'Sharpe Ratio': stats.get('Sharpe Ratio', np.nan)
        }
        print(f"Basis-Ergebnisse: {base_result}\n")
        save_result(base_result, 'DynamicMomentumCrossover_Base')

        # Optimierung mit Heatmap
        opt_stats, heatmap = bt.optimize(
            fast_ema=range(10, 61, 10),
            medium_ema=range(20, 121, 20),
            rsi_threshold=range(50, 101, 10),
            atr_multiple=[1.0, 1.5, 2.0, 2.5, 3.0],
            maximize='Return [%]',
            return_heatmap=True
        )
        opt_result = {
            'file': os.path.basename(file),
            'fast_ema': opt_stats._strategy.fast_ema,
            'medium_ema': opt_stats._strategy.medium_ema,
            'rsi_threshold': opt_stats._strategy.rsi_threshold,
            'atr_multiple': opt_stats._strategy.atr_multiple,
            'Opt Return [%]': opt_stats['Return [%]'],
            'Opt Equity [$]': opt_stats['Equity Final [$]']
        }
        print(f"Optimale Parameter & Ergebnis: {opt_result}\n")
        save_result(opt_result, 'DynamicMomentumCrossover_Opt')

        # Heatmap optional exportieren
        heatmap.to_csv(f"heatmap_{os.path.basename(file)}.csv")

    print("\n--- Alle Backtests und Optimierungen abgeschlossen ---")
