class Order:
    ORDER_ID = 0;
    class Side:
        BUY  = 1;
        SELL = 2;
        @staticmethod
        def toString(side):
            if side == Order.Side.BUY:
                return "BUY";
            else:
                return "SELL";
    class State:
        OPEN           = 1;
        CANCELED      = 2;
        PARTIAL_FILLED = 3;
        FILLED         = 4;
    def __init__(self):
        self.timestamp = 0;
        self.side      = 0;
        self.price     = 0;
        self.qty       = 0;
        self.openQty   = 0;
        self.tradeQty  = 0;
        self.text      = '';
        self.orderid   = 0;
        self.state     = Order.State.OPEN;
    @staticmethod
    def nextOrderId():
        Order.ORDER_ID = Order.ORDER_ID + 1;
        return Order.ORDER_ID;
    def __repr__(self):
        s = "%d,%s,%.3f,%d,%d,%d,%s,%d,%d" % (self.timestamp,
                                              Order.Side.toString(self.side),
                                              self.price,
                                              self.qty,
                                              self.openQty,
                                              self.tradeQty,
                                              self.text,
                                              self.orderid,
                                              self.state);
        return s;

class Trade:
    TRADE_ID = 0;
    def __init__(self):
        self.timestamp = 0;
        self.side      = 0;
        self.price     = 0;
        self.qty       = 0;
        self.text      = '';
        self.orderid   = 0;
        self.tradeid   = 0;
    @staticmethod
    def nextTradeID():
        Trade.TRADE_ID = Trade.TRADE_ID + 1;
        return Trade.TRADE_ID;
    def __repr__(self):
        s = "%d,%s,%.3f,%d,%s,%d,%d" % (self.timestamp,
                                        Order.Side.toString(self.side),
                                        self.price,
                                        self.qty,
                                        self.text,
                                        self.orderid,
                                        self.tradeid);
        return s;

class OrderManager(object):
    def __init__(self):
        # open orders;
        self.openOrders   = [];
        # open positions;
        self.positions    = [];

        # filled or cancelled orders
        self.closedOrders = [];
        # all the fills
        self.trades       = [];

        self.comm = 0;              #commisions
        self.realizedProfit = 0;    #realized profits
        self.unrealizedProfit = 0;  #non relaized profits.
        # Profit records for the time period;
        self.profits = [];
        # Margin used for the time period.; TODO:
        self.margins = [];
    def dump(self):
        print "Realized profits = ", self.realizedProfit;
        print "Non Realized Profits = ", self.unrealizedProfit;
        print "Commission = ", self.comm;
        print "Number of trades made = ", len(self.trades);
        #print "Max Draw Down = ", self.drawDown()[0];

    def drawDown(self, sampling = 100):
        marks = range(0, len(self.profits), sampling);
        if len(self.profits) % sampling != 0:
            marks.append(len(self.profits));
        highMarks = [];
        for i in range(1, len(marks)):
            highProfit = max(self.profits[marks[i-1]:marks[i]], key = lambda t : t[1]);
            highMarks.append([self.profits.index(highProfit), highProfit[0], highProfit[1]]);
        highMarks.append([len(self.profits)-1, self.profits[len(self.profits)-1]]);
        down = [];
        for i in range(0, len(highMarks)-1):
            start = highMarks[i][0];
            for j in range(i+1, len(highMarks)):
                if j == len(highMarks) -1 or highMarks[j][2] > highMarks[i][2]:
                    end = highMarks[j][0];
                    lowProfit = min(self.profits[start+1:end], key = lambda t : t[1]);
                    down.append([highMarks[i][1], lowProfit[0], lowProfit[1]-highMarks[i][2]]);
                    break;
        down.sort(key = lambda t : t[2]);
        return down;

    def setMarketData(self, md):
        self.md = md;
    def setFeeStructure(self, fs):
        self.fs = fs;

    def run(self):
        for m in self.md:
            trades = m.match(self.openOrders);
            self.checkTrades(trades);
            self.onBook(m);
            trades = m.LOCMatch(self.openOrders);
            self.checkTrades(trades);
            self.calProfits(m);

    def checkTrades(self, trades):
        if len(trades) != 0:
            for t in trades:
                self.comm = self.comm + self.fs.fee(t);
                self.onTrade(t);
            self.positions.extend(trades);
            self.trades.extend(trades);
            self.closedOrders.extend(filter(lambda o : o.state != Order.State.OPEN, self.openOrders));
            self.openOrders = filter(lambda o : o.state == Order.State.OPEN, self.openOrders);

    def calProfits(self, m):
        buy_sale = 0.;  buy_qty = 0.;
        sell_sale = 0.; sell_qty = 0.;
        for p in self.positions:
            if p.side == Order.Side.BUY:
                buy_sale = buy_sale + p.price * p.qty;
                buy_qty = buy_qty + p.qty;
            else:
                sell_sale = sell_sale + p.price * p.qty;
                sell_qty = sell_qty + p.qty;
        if buy_qty == 0 or sell_qty == 0 or buy_qty == sell_qty:
            if sell_qty == 0:
                self.unrealizedProfit = m.settlementPrice() * buy_qty - buy_sale;
            elif buy_qty == 0:
                self.unrealizedProfit = sell_sale - m.settlementPrice() * sell_qty;
            else:
                self.realizedProfit = self.realizedProfit + sell_sale - buy_sale;
                self.unrealizedProfit = 0;
                self.positions = [];    # no positions left.
        elif sell_qty < buy_qty:          # Long
            self.realizedProfit = self.realizedProfit + sell_sale - buy_sale * sell_qty / buy_qty;
            t = Trade();
            t.timestamp = m.timestamp;
            t.side = Order.Side.BUY;
            t.price = buy_sale / buy_qty;
            t.qty = buy_qty - sell_qty;
            self.positions = [];
            self.positions.append(t);
            self.unrealizedProfit = (m.settlementPrice() - t.price) * t.qty;
        elif sell_qty > buy_qty:          # Short
            self.realizedProfit = self.realizedProfit + sell_sale * buy_qty / sell_qty - buy_sale;
            t = Trade();
            t.timestamp = m.timestamp;
            t.side = Order.Side.SELL;
            t.price = sell_sale / sell_qty;
            t.qty = sell_qty - buy_qty;
            self.positions = []
            self.positions.append(t);
            self.unrealizedProfit = (t.price - m.settlementPrice()) * t.qty;
        curprofit = self.realizedProfit + self.unrealizedProfit - self.comm;
        self.profits.append([m.timestamp, curprofit]);

    def plotProfits(self):
        import matplotlib.pyplot as plt;
        import dateutil.parser as parser;
        x = [];
        y = [];
        for p in self.profits:
            x.append(parser.parse(str(p[0])));
            y.append(p[1]);
        plt.plot_date(x, y);
        plt.show();

    def curPosition(self):
        pos = 0;
        for p in self.positions:
            if p.side == Order.Side.BUY:
                pos = pos + p.qty;
            else:
                pos = pos - p.qty;
        return pos;

    def openBuySell(self):
        buys = 0; sells = 0;
        for o in self.openOrders:
            if o.side == Order.Side.BUY:
                buys = buys + o.openQty;
            else:
                sells = sells + o.openQty;
        return (buys, sells);

    def newOrder(self, ts, side, price, qty, text):
        o = Order();
        o.timestamp = ts;
        o.side = side;
        o.price = price;
        o.qty = qty;
        o.openQty = qty;
        o.tradeQty = 0;
        o.text = text;
        o.orderid = Order.nextOrderId();
        self.openOrders.append(o);
        print "New Order = ", o
        return o.orderid;

    def cancelOrder(self, orderid):
        for o in self.openOrders:
            if o.orderid == orderid and o.state != Order.State.FILLED:
                o.state = Order.State.CANCELED;
                o.openQty = 0;
                print "Cancel Order = ", o

    #cancel all orders on the same side
    def cancelAllOrders(self, side):
        for o in self.openOrders:
            if o.openQty > 0 and o.side == side:
                o.state = Order.State.CANCELED;
                o.openQty = 0;
                print "Cancel Order = ", o

    def onTrade(self, t):
        pass;   #overwrite when there are trades matched.
    def onBook(self, m):
        pass    #implemente this for trading algorithm operations.

# Market Snapshot at a certain time and its matching rule
class Snapshot(object):
    def __init__(self):
        self.timestamp = 0;
    def settlementPrice(self):
        return 0;
    def match(self, openOrders):
        return [];
    def LOCMatch(self, openOrders):
        return [];
    def fillOrder(self, order):
        t = Trade();
        t.timestamp = self.timestamp;
        t.side = order.side;
        t.price = order.price;
        t.qty = order.qty;
        t.text = order.text;
        t.orderid = order.orderid;
        t.tradeid = Trade.nextTradeID();
        return t;

class OHLCSnapshot(Snapshot):
    def __init__(self):
        super(OHLCSnapshot, self).__init__();
        self.oPrice = 0;
        self.hPrice = 0;
        self.lPrice = 0;
        self.cPrice = 0;
        self.vol    = 0;

    def __repr__(self):
        s = "%d,%.3f,%.3f,%.3f,%.3f,%d" % (self.timestamp,
                                           self.oPrice,
                                           self.hPrice,
                                           self.lPrice,
                                           self.cPrice,
                                           self.vol,);
        return s;
    def settlementPrice(self):
        return self.cPrice;
    def match(self, openOrders):
        trades = [];
        for o in openOrders:
            if o.state == Order.State.CANCELED or o.state == Order.State.FILLED:
                continue;
            if o.side == Order.Side.BUY and o.price > self.lPrice:
                trades.append(self.fillOrder(o));
                o.openQty = 0;
                o.tradeQty = o.qty;
                o.state = Order.State.FILLED;
            elif o.side == Order.Side.SELL and o.price < self.hPrice:
                trades.append(self.fillOrder(o));
                o.openQty = 0;
                o.tradeQty = o.qty;
                o.state = Order.State.FILLED;
        return trades;
    def LOCMatch(self, openOrders):
        trades = [];
        for o in openOrders:
            if o.state == Order.State.CANCELED or o.state == Order.State.FILLED:
                continue;
            if o.side == Order.Side.BUY and o.price >= self.cPrice:
                trades.append(self.fillOrder(o));
                o.openQty = 0;
                o.tradeQty = o.openQty;
                o.state = Order.State.FILLED;
            elif o.side == Order.Side.SELL and o.price <= self.cPrice:
                trades.append(self.fillOrder(o));
                o.openQty = 0;
                o.tradeQty = o.qty;
                o.state = Order.State.FILLED;
        return trades;

class BestLevelSnapshot(Snapshot):
    def __init__(self):
        super(BestLevelSnapshot, self).__init__();
        self.bidPrice = 0.;
        self.bidQty = 0.;
        self.askPrice = 0.;
        self.askQty = 0.;
    def __repr__(self):
        s = "%d,%.3f,%d,%.3f,%d" % (self.timestamp,
                                    self.bidPrice,
                                    self.bidQty,
                                    self.askPrice,
                                    self.askQty,);
        return s;
    def settlementPrice(self):  # Use the mid price.
        return (self.bidPrice + self.askPrice) / 2.0;

    def match(self, openOrders):
        trades = [];
        for o in openOrders:
            if o.state == Order.State.CANCELED or o.state == Order.State.FILLED:
                continue;
            if o.side == Order.Side.BUY and o.price >= self.askPrice:
                trades.append(self.fillOrder(o));
                o.openQty = 0;
                o.tradeQty = o.qty;
                o.state = Order.State.FILLED;
            elif o.side == Order.Side.SELL and o.price <= self.bidPrice:
                trades.append(self.fillOrder(o));
                o.openQty = 0;
                o.tradeQty = o.qty;
                o.state = Order.State.FILLED;
        return trades;

    def LOCMatch(self, openOrders):
        return self.match(openOrders);

class MarketData(object):
    def __init__(self):
        #store a list of Snapshot objects
        self.market = [];
    def load(self):
        #overwrite this to load market data.
        pass
    def __len__(self):
        return len(self.market);
    def __getitem__(self, i):
        return self.market[i];

class OHLCMarketData(MarketData):
    def load(self, datafile):
        f = open(datafile, 'r');
        data = f.readlines()[1:];
        for line in data:
            l = line.split(',');
            s = OHLCSnapshot();
            s.timestamp =  int(l[0]);
            s.oPrice = float(l[1]);
            s.hPrice = float(l[2]);
            s.lPrice = float(l[3]);
            s.cPrice = float(l[4]);
            s.vol = int(l[5]);
            self.market.append(s);

class FeeStructure(object):
    def fee(self, trade):
        return 0;

class PerQuantityFeeStructure(FeeStructure):
    def __init__(self):
        self.feePerQuantity = 0.01;
    def fee(self, trade):
        return trade.qty * self.feePerQuantity;

class VariableFeeStructure(FeeStructure):
    def __init__(self):
        self.percentValue = 0.0001;
        self.feePerQuantity = 0;
        self.fixedFee = 0;
    def fee(self, trade):
        f = trade.qty * trade.price * self.percentValue + self.feePerQuantity * trade.qty + self.fixedFee;
        return f;

class BookLevel:
    def __init__(self):
        self.bidPrice = 0.;
        self.bidQty = 0.;
        self.askPrice = 0.;
        self.askQty = 0.;
    def midPrice(self):
        return (self.bidPrice + self.askPrice) / 2.0;
    def __repr__(self):
        return "[%.2f, %d, %.2f, %d]" %  (self.bidPrice, self.bidQty, self.askPrice, self.askQty);

class CommUtil:
    #Time Stamp is in the format YYYYMMDDhhmmssuuuuuu.
    #Covert timestamp to DateTime object
    @staticmethod
    def dateTime(ts):
        from dateutil.parser import parse;
        return parse(str(ts/1000000));
    #Calcucate the time delta between two timestamps
    @staticmethod
    def timeDelta(begin, end):
        return CommUtil.dateTime(end) - CommUtil.dateTime(begin);
