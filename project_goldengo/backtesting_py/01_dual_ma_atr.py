import os
import pandas as pd
import ta
from backtesting import Backtest, Strategy
from backtesting.lib import crossover

# Importieren Sie Ihre "kugelsichere" Funktion aus der anderen Datei
from project_goldengo.prepare_data import load_and_prepare_data

class DualMaAtrStrategy(Strategy):
    n1 = 20
    n2 = 50
    atr_period = 14
    atr_sl_multiplier = 2
    atr_tp_multiplier = 4
    
    # Diese Variable wird jetzt direkt als prozentuale Grösse verwendet
    size_prozent = 0.95 # Wir investieren 95% des Kapitals pro Trade

    def init(self):
        self.ema_fast = self.I(ta.trend.ema_indicator, pd.Series(self.data.Close), window=self.n1)
        self.ema_slow = self.I(ta.trend.ema_indicator, pd.Series(self.data.Close), window=self.n2)
        self.atr = self.I(ta.volatility.average_true_range, 
                          pd.Series(self.data.High), 
                          pd.Series(self.data.Low), 
                          pd.Series(self.data.Close), 
                          window=self.atr_period)

    def next(self):
        price = self.data.Close[-1]
        atr_value = self.atr[-1]

        if atr_value <= 0:
            return

        # Entry-Logik
        if not self.position:
            if crossover(self.ema_fast, self.ema_slow):
                # SL und TP Preise bleiben gleich berechnet
                stop_price = price - self.atr_sl_multiplier * atr_value
                tp_price = price + self.atr_tp_multiplier * atr_value

                # ========================== KORREKTUR ==========================
                # Wir verwenden jetzt eine feste prozentuale Grösse,
                # die backtesting.py direkt versteht.
                # `size` muss eine Zahl zwischen 0 und 1 sein.
                self.buy(size=self.size_prozent, sl=stop_price, tp=tp_price)
                # ===============================================================
        
        # Exit-Logik
        else:
            if crossover(self.ema_slow, self.ema_fast):
                self.position.close()


if __name__ == '__main__':
    from project_goldengo.prepare_data import load_and_prepare_data

    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(base_dir, '..', 'data', 'BTC-USD-20-24.csv')
    
    data = load_and_prepare_data(data_path)

    if data is not None and not data.empty:
        bt = Backtest(
            data,
            DualMaAtrStrategy,
            cash=100000,
            commission=0.001,
            # NEU: Erlaube den Handel mit Bruchteilen von Einheiten
            exclusive_orders=True 
        )

        print("Starte Optimierung... das kann einige Minuten dauern.")

        stats = bt.optimize(
            n1=range(10, 35, 5),
            n2=range(40, 75, 5),
            atr_sl_multiplier=range(2, 8, 1),

            # Wichtig: Wir stellen sicher, dass der schnelle EMA immer schneller ist als der langsame
            constraint=lambda params: params.n1 < params.n2,

            # Wir wollen die Strategie finden, die die höchste End-Equity hat
            maximize='Equity Final [$]'
        )
        print("\n--- BACKTEST ERGEBNISSE ---")
        print(stats)
        # =================================================================
        # DIESE ZEILE ZEIGT IHNEN DIE PARAMETER:
        print("\nBeste gefundene Parameter:")
        print(stats._strategy)
        # =================================================================

        bt.plot()
    else:
        print("\nBacktest wurde wegen eines Daten-Fehlers nicht gestartet.")
