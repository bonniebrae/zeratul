from spreadtrigger import *

md = TirggerMarketData();
md.load('cu1107.txt', 'cu1108.txt');
fe = VariableFeeStructure();
fe.percentValue = 0.0002;
strategy = EMATrigger();
strategy.setMarketData(md);
strategy.setFeeStructure(fe);
strategy.run();
strategy.dump();
#strategy.plotProfits();
