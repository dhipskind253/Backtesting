from AlgorithmImports import *

class RangeBreakoutWithSuperTrend(QCAlgorithm):
    def Initialize(self):
        # Set the start and end dates for the backtest
        self.SetStartDate(2023, 1, 1)
        self.SetEndDate(2024, 1, 1)
        
        # Set the initial capital
        self.SetCash(100000)
        
        # Choose your stock (you can add more using self.AddEquity)
        self.symbol = self.AddEquity("SPY", Resolution.Minute).Symbol
        
        # Set resolution to minute to capture 1-minute data
        self.SetTimeZone(TimeZones.NewYork)
        
        # SuperTrend settings
        self.superTrendPeriod = 7
        self.superTrendMultiplier = 3.0
        self.superTrend = SuperTrend(self.superTrendPeriod, self.superTrendMultiplier)
        self.RegisterIndicator(self.symbol, self.superTrend, Resolution.Minute)
        
        # Variables to hold range high and low
        self.rangeHigh = None
        self.rangeLow = None
        self.rangeSet = False
        self.firstTradeDone = False
        
        # Schedule the range to be calculated after 30 minutes
        self.Schedule.On(self.DateRules.EveryDay(self.symbol), 
                         self.TimeRules.AfterMarketOpen(self.symbol, 30), 
                         self.SetRange)
        
        # Track price crossing over the range for buying/selling
        self.Schedule.On(self.DateRules.EveryDay(self.symbol), 
                         self.TimeRules.Every(TimeSpan.FromMinutes(1)), 
                         self.CheckForTrade)

    def SetRange(self):
        """ Set the range after the first 30 minutes """
        history = self.History(self.symbol, 30, Resolution.Minute)
        if not history.empty:
            self.rangeHigh = max(history["high"])
            self.rangeLow = min(history["low"])
            self.rangeSet = True
            self.firstTradeDone = False
            self.Debug(f"Range set: High={self.rangeHigh}, Low={self.rangeLow}")

    def CheckForTrade(self):
        """ Check for breakout above or below the range """
        if not self.rangeSet:
            return
        
        current_price = self.Securities[self.symbol].Price
        supertrend_signal = self.superTrend.Current.Value
        invested = self.Portfolio[self.symbol].Invested
        
        # Check for a long position
        if not invested and current_price > self.rangeHigh and not self.firstTradeDone:
            self.SetHoldings(self.symbol, 1)
            self.firstTradeDone = True
            self.Debug(f"Bought at {current_price}")
        
        # Check for a short position
        elif not invested and current_price < self.rangeLow and not self.firstTradeDone:
            self.SetHoldings(self.symbol, -1)
            self.firstTradeDone = True
            self.Debug(f"Shorted at {current_price}")

        # Close long if SuperTrend gives a sell signal
        elif invested and self.Portfolio[self.symbol].IsLong and supertrend_signal < current_price:
            self.Liquidate(self.symbol)
            self.Debug(f"Closed long at {current_price} due to SuperTrend")

        # Close short if SuperTrend gives a buy signal
        elif invested and self.Portfolio[self.symbol].IsShort and supertrend_signal > current_price:
            self.Liquidate(self.symbol)
            self.Debug(f"Closed short at {current_price} due to SuperTrend")
            
    def OnEndOfDay(self, symbol):
        """ Reset range and positions at the end of the trading day """
        self.rangeSet = False

# SuperTrend indicator class
class SuperTrend(PythonIndicator):
    def __init__(self, period, multiplier):
        self.period = period
        self.multiplier = multiplier
        self.trueRange = AverageTrueRange(period)
        self.basicUpperBand = RollingWindow[float](period)
        self.basicLowerBand = RollingWindow[float](period)
        self.finalUpperBand = 0
        self.finalLowerBand = 0
        self.isLong = True
        self.Current = IndicatorDataPoint(0, 0)

    def Update(self, input):
        """ Calculate SuperTrend value """
        atr = self.trueRange.Update(input)
        self.basicUpperBand.Add(input.Price + self.multiplier * atr)
        self.basicLowerBand.Add(input.Price - self.multiplier * atr)
        
        if self.isLong:
            self.finalUpperBand = min(self.basicUpperBand)
            if input.Price < self.finalUpperBand:
                self.isLong = False
        else:
            self.finalLowerBand = max(self.basicLowerBand)
            if input.Price > self.finalLowerBand:
                self.isLong = True
        
        self.Current = IndicatorDataPoint(input.EndTime, 
                                          self.finalUpperBand if self.isLong else self.finalLowerBand)
        return True
