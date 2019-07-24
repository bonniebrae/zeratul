from zeratul import *;
from datetime import *;

#This is used for strategies with two legs; the first leg is the reference leg and the second leg is the trading leg.
class TriggerSnapshot(Snapshot):
    def __init__(self):
        super(TriggerSnapshot, self).__init__();
        self.rBestLevel = BookLevel();  # Reference leg
        self.tBestLevel = BookLevel();  # Trading leg
    def settlementPrice(self):
        return self.tBestLevel.midPrice();
    def match(self, openOrders):
        trades = [];
        for o in openOrders:
            if o.state == Order.State.CANCELED or o.state == Order.State.FILLED:
                continue;
            #need to check the quantity: TODO;
            if o.side == Order.Side.BUY and o.price >= self.tBestLevel.askPrice:
                trades.append(self.fillOrder(o));
                o.openQty = 0;
                o.tradeQty = o.qty;
                o.state = Order.State.FILLED;
            elif o.side == Order.Side.SELL and o.price <= self.tBestLevel.bidPrice:
                trades.append(self.fillOrder(o));
                o.openQty = 0;
                o.tradeQty = o.qty;
                o.state = Order.State.FILLED;
        return trades;

    def LOCMatch(self, openOrders):
        return self.match(openOrders);

class TirggerMarketData(MarketData):
    def load(self, file1, file2):
        f1 = open(file1, 'r');
        f2 = open(file2, 'r');
        data1 = f1.readlines();
        data2 = f2.readlines();
        if len(data1) != len(data2):
            raise Exception('wrong input files');
        for i in range(len(data1)):
            l1 = data1[i].split(',');
            l2 = data2[i].split(',');
            t = TriggerSnapshot();
            t.timestamp = int(l1[0]);
            t.rBestLevel.bidPrice = float(l1[1]);
            t.rBestLevel.bidQty = int(l1[2]);
            t.rBestLevel.askPrice = float(l1[3]);
            t.rBestLevel.askQty = int(l1[4]);
            t.tBestLevel.bidPrice = float(l2[1]);
            t.tBestLevel.bidQty = int(l2[2]);
            t.tBestLevel.askPrice = float(l2[3]);
            t.tBestLevel.askQty = int(l2[4]);
            self.market.append(t);

class EMATrigger(OrderManager):
    def __init__(self):
        super(EMATrigger, self).__init__();
        self.k = 0.75;
        self.ema = 0.;
        self.n = 0;
        self.startn = 300 * 2;  # 5 min
        self.signaln = 2;       # cycles to calcuate EMA
        self.units = 0;
        self.orderLifetime = timedelta(0, 15, 0);  # order lifetime is 15 seconds.
        self.lastBuy = 0;
        self.lastSell = 0;
        self.myAsk = 0;
        self.myBid = 0;
        self.tick = 10.;
        self.maxpos = 1;
    def onTrade(self, t):
        if t.side == Order.Side.BUY:
            self.lastBuy = t.price;
            self.lastSell = 0;
        else:
            self.lastBuy = 0;
            self.lastSell = t.price;
    def onBook(self, m):
        #print m.timestamp, m.rBestLevel, m.tBestLevel
        if self.n % self.signaln == 0:
            self.ema = self.ema * (1.0 - self.k) + self.k * (m.tBestLevel.midPrice() - m.rBestLevel.midPrice());
        if self.n < self.startn:
            self.n = self.n + 1;
            return;
        self.cancelOldOrders(m);
        self.emaTrigger(m);
        #maintain the count and default period to replace the timer.
        self.n = self.n + 1;
    def cancelOldOrders(self, m):
        for o in self.openOrders:
            if CommUtil.timeDelta(o.timestamp, m.timestamp) > self.orderLifetime and o.state != Order.State.CANCELED:
                self.cancelOrder(o.orderid);
    def emaTrigger(self, m):
        self.myBid = int((m.rBestLevel.bidPrice + self.ema) / self.tick - 1.5) * self.tick;
        self.myAsk = int((m.rBestLevel.askPrice + self.ema) / self.tick + 1.5) * self.tick;
        if self.myBid >= m.tBestLevel.bidPrice and self.myBid != self.lastBuy:
            curPos = self.curPosition();
            openBuySell = self.openBuySell();
            qtyToBuy = 0;
            if curPos < self.maxpos and curPos >= 0:
                qtyToBuy = self.maxpos - curPos;
            elif curPos < 0:
                qtyToBuy = -curPos;
            if openBuySell[0] < qtyToBuy:
                self.newOrder(m.timestamp, Order.Side.BUY, self.myBid, qtyToBuy - openBuySell[0] , '');
        elif self.myAsk <= m.tBestLevel.askPrice and self.myAsk != self.lastSell:
            curPos = self.curPosition();
            openBuySell = self.openBuySell();
            qtyToSell = 0;
            if curPos <= 0 and -curPos < self.maxpos :
                qtyToSell = self.maxpos + curPos;
            elif curPos > 0:
                qtyToSell = curPos;
            if openBuySell[1] < qtyToSell:
                self.newOrder(m.timestamp, Order.Side.SELL, self.myAsk, qtyToSell - openBuySell[1], '');

