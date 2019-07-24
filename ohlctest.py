from zeratul import *;

class MyStrategy(OrderManager):
    def __init__(self):
        super(MyStrategy, self).__init__();
        self.k = 0.1;
        self.lastclose = 0;
        self.lastema = 0;

    def onBook(self, m):
        ema = self.lastema * (1.-self.k) + m.cPrice * self.k;
        if (m.cPrice - ema) * (self.lastclose - self.lastema) < 0:
            if m.cPrice > ema and self.curPosition() == 0:
                self.newOrder(m.timestamp, Order.Side.BUY, m.cPrice, 100, 'UP');
            elif m.cPrice < ema and self.curPosition() > 0:
                self.newOrder(m.timestamp, Order.Side.SELL, m.cPrice, 100, 'DOWN');
        self.lastema = ema;
        self.lastclose = m.cPrice;

md = OHLCMarketData();
md.load("SPY.txt");
fe = PerQuantityFeeStructure();

strategy = MyStrategy();
strategy.setMarketData(md);
strategy.setFeeStructure(fe);
strategy.run();
strategy.dump();
strategy.plotProfits();
