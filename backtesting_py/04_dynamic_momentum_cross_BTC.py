import os
import glob
import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
from prepare_data import load_and_prepare_data

# --- Hilfsfunktionen für Indikatoren ---
def ema(arr, span):
    """Exponentiellen gleitenden Durchschnitt berechnen"""
    arr = np.array(arr, dtype=float)
    alpha = 2 / (span + 1)
    ema = np.empty_like(arr)
    ema[0] = arr[0]
    for i in range(1, len(arr)):
        ema[i] = alpha * arr[i] + (1 - alpha) * ema[i-1]
    return ema

def sma(arr, period):
    """Einfachen gleitenden Durchschnitt berechnen"""
    arr = np.array(arr, dtype=float)
    sma = np.full_like(arr, np.nan)
    cumsum = np.cumsum(arr)
    for i in range(period-1, len(arr)):
        sma[i] = (cumsum[i] - (cumsum[i-period] if i>=period else 0)) / period
    return sma

def rsi_func(arr, period):
    """RSI nach Wilder berechnen"""
    arr = np.array(arr, dtype=float)
    delta = np.diff(arr, prepend=arr[0])
    gains = np.where(delta > 0, delta, 0)
    losses = np.where(delta < 0, -delta, 0)
    avg_gain = np.full_like(arr, np.nan)
    avg_loss = np.full_like(arr, np.nan)
    # First average
    avg_gain[period] = np.mean(gains[1:period+1])
    avg_loss[period] = np.mean(losses[1:period+1])
    # Wilder's smoothing
    for i in range(period+1, len(arr)):
        avg_gain[i] = (avg_gain[i-1] * (period - 1) + gains[i]) / period
        avg_loss[i] = (avg_loss[i-1] * (period - 1) + losses[i]) / period
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def obv_func(close, volume):
    """On-Balance Volume berechnen"""
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
    """Hybride Swing-Trading-Strategie: Trendfilter, EMA-Crossover, RSI, OBV, ATR-Trailing-Stop"""
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
        # ATR als gleitender Mittelwert der High-Low-Spanne
        span = self.atr_period
        self.atr = self.I(lambda high, low: np.convolve(np.abs(np.array(high)-np.array(low)),
                                                         np.ones(span)/span, mode='same'),
                         self.data.High, self.data.Low)
        self.stop_price = None

    def next(self):
        price = self.data.Close[-1]
        if not self.position:
            # Trendfilter
            if price <= self.ema_slow[-1]:
                return
            # EMA-Crossover
            if not crossover(self.ema_fast, self.ema_medium):
                return
            # RSI-Filter
            if self.rsi[-1] >= self.rsi_threshold:
                return
            # OBV-Filter
            if self.obv[-1] <= self.obv_sma[-1]:
                return
            # Positionsgröße berechnen
            atr_val = self.atr[-1]
            stop_dist = atr_val * self.atr_multiple
            risk_amount = self.equity * self.risk_per_trade
            if stop_dist <= 0 or np.isnan(stop_dist):
                return
            size = risk_amount / stop_dist
            # Größe anpassen: für size>1 auf ganze Einheiten abrunden (Backtesting.py verlangt ganze Einheiten)
            if size > 1:
                size = int(size)
            # Kleiner oder gleich null überspringen
            if size <= 0:
                return
            self.buy(size=size)
            self.stop_price = price - stop_dist
        else:
            # Trailing-Stop aktualisieren
            atr_val = self.atr[-1]
            new_stop = price - atr_val * self.atr_multiple
            if new_stop > self.stop_price:
                self.stop_price = new_stop
            # Ausstieg bei "Death Cross" oder Stop-Loss
            if crossover(self.ema_medium, self.ema_fast) or price < self.stop_price:
                self.position.close()

if __name__ == '__main__':
    # BTC CSV-Dateien automatisch einlesen
    csv_dir = os.path.join('crypto_data', 'BTC')
    files = sorted(glob.glob(os.path.join(csv_dir, '*.csv')))

    summary = []
    for file in files:
        print(f"--- Starte Backtest für: {file} ---")
        df = load_and_prepare_data(file)
        if df is None or df.empty:
            print("Datei konnte nicht vorbereitet werden oder ist leer. Überspringe.")
            continue

        bt = Backtest(
            df,
            DynamicMomentumCrossover,
            cash=1000000,
            commission=0.002,
            exclusive_orders=True
        )
        stats = bt.run()
        stats['file'] = os.path.basename(file)
        summary.append(stats)
        print(stats)

    # Zusammenfassung ausgeben
    results_df = pd.DataFrame(summary)
    print("\n--- Zusammenfassung aller Backtests ---")
    print(results_df[['file', 'Equity Final [$]', 'Return [%]', 'Sharpe Ratio']])


