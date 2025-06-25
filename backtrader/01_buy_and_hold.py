from datetime import datetime
import backtrader as bt
import os

class BuyAndHold(bt.Strategy):
    def __init__(self):
        self.close = self.data.close
        self.order = None

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()} - {txt}')

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status in [order.Completed]:
            self.log(f'KAUF AUSGEFÜHRT, Preis: {order.executed.price:.2f}, Kosten: {order.executed.value:.2f}, Gebühr: {order.executed.comm:.2f}')
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order storniert/abgelehnt')

        self.order = None

    def next(self):
        """
        next() wird für jede Kerze (jeden Tag) in den Daten aufgerufen.
        Hier lebt die eigentliche Handelslogik.
        """
        # Wir prüfen, ob wir bereits eine Position im Markt haben.
        # Wenn nicht, führen wir unseren Kauf aus.
        if not self.position:
        # Wir haben noch keine Position, also kaufen wir.
            size_to_buy = int(0.95 *self.broker.getcash() / self.data.close[0])
            self.log(f'KAUFSIGNAL ERSTELLT, Preis: {self.data.close[0]:.2f}, Größe: {size_to_buy}')
            self.order = self.buy(size=size_to_buy)

if __name__ == "__main__":
    cerebro = bt.Cerebro()

    data_file = os.path.join('data', 'BTC-USD-20-24.csv')

    data = bt.feeds.YahooFinanceCSVData(
        dataname=data_file,
        fromdate=datetime(2022, 1, 1)
        #date=datetime(2023, 12, 31)
    )


    cerebro.adddata(data)
    cerebro.addstrategy(BuyAndHold)
    cerebro.broker.setcash(10000.0)
    cerebro.broker.setcommission(commission=0.003)

    print(f'Startkapital: {cerebro.broker.getvalue():.2f}')
    cerebro.run()
    print(f'Endkapital:   {cerebro.broker.getvalue():.2f}')
    cerebro.plot(iplot=False) # iplot=False sorgt für ein separates Plot-Fenster