import time
from datetime import datetime
import pytz
import MetaTrader5 as mt5

# ==============================================================================
# JUSTMARKETS DEMO ACCOUNT CREDENTIALS
# ==============================================================================
ACCOUNT_NUMBER = 1100528266  # <--- Apna JustMarkets Demo Account Number yahan likhein
PASSWORD = "@Admin009"  # <--- Apna Password yahan likhein
SERVER = "JustMarkets-Demo2"  # <--- Apna Server Name yahan likhein
SYMBOL = "XAUUSD"  # Gold Symbol Name (e.g., XAUUSD / XAUUSD.c)

# ==============================================================================
# RISK & STRATEGY INPUTS (Matches Trade_With_Alee_V11)
# ==============================================================================
FIXED_LOT_SIZE = 0.35  # Lot Size
RISK_REWARD_RATIO = 2.0  # Risk to Reward 1:2
EXTRA_SL_POINTS = 100.0  # SL Buffer Points
MAX_DAILY_TRADES = 7  # Max daily trade count

ASIA_START_HOUR = 0
ASIA_END_HOUR = 8
TRADE_START_HOUR = 9
TRADE_END_HOUR = 21

# Tracker Variables
daily_trade_count = 0
last_trade_day = None
asia_high = None
asia_low = None


def connect_mt5():
  if not mt5.initialize():
    print(f'MT5 Initialization Failed: {mt5.last_error()}')
    return False

  authorized = mt5.login(ACCOUNT_NUMBER, password=PASSWORD, server=SERVER)
  if authorized:
    print('Successfully Connected to JustMarkets Account!')
    return True
  else:
    print(f'Login Failed: {mt5.last_error()}')
    return False


def get_asia_high_low():
  global asia_high, asia_low
  rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_H1, 0, 24)
  if rates is None or len(rates) == 0:
    return

  highs = [
      r['high']
      for r in rates
      if ASIA_START_HOUR
      <= datetime.fromtimestamp(r['time'], tz=pytz.utc).hour
      < ASIA_END_HOUR
  ]
  lows = [
      r['low']
      for r in rates
      if ASIA_START_HOUR
      <= datetime.fromtimestamp(r['time'], tz=pytz.utc).hour
      < ASIA_END_HOUR
  ]

  if highs and lows:
    asia_high = max(highs)
    asia_low = min(lows)
    print(f'Asian Range Calculated -> High: {asia_high}, Low: {asia_low}')


def run_bot():
  global daily_trade_count, last_trade_day, asia_high, asia_low

  if not connect_mt5():
    return

  print('Bot is active and searching for Asian Sweeps 24/7...')

  while True:
    now_utc = datetime.now(pytz.utc)
    today = now_utc.date()

    # Midnight Reset
    if last_trade_day != today:
      last_trade_day = today
      daily_trade_count = 0
      asia_high = None
      asia_low = None

    if daily_trade_count >= MAX_DAILY_TRADES:
      time.sleep(60)
      continue

    # Get Asian Range
    if now_utc.hour >= ASIA_END_HOUR and asia_high is None:
      get_asia_high_low()

    # Execute inside Trade Window
    if (
        asia_high is not None
        and TRADE_START_HOUR <= now_utc.hour < TRADE_END_HOUR
    ):
      rates_m5 = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M5, 0, 2)
      if rates_m5 is not None and len(rates_m5) >= 2:
        prev_bar = rates_m5[0]
        ask = mt5.symbol_info_tick(SYMBOL).ask
        bid = mt5.symbol_info_tick(SYMBOL).bid
        point = mt5.symbol_info(SYMBOL).point

        # Bullish Sweep (Buy Signal)
        if prev_bar['low'] < asia_low and prev_bar['close'] > asia_low:
          sl = prev_bar['low'] - (EXTRA_SL_POINTS * point)
          risk = ask - sl
          tp = ask + (risk * RISK_REWARD_RATIO)

          request = {
              'action': mt5.TRADE_ACTION_DEAL,
              'symbol': SYMBOL,
              'volume': FIXED_LOT_SIZE,
              'type': mt5.ORDER_TYPE_BUY,
              'price': ask,
              'sl': sl,
              'tp': tp,
              'magic': 776655,
              'comment': 'Render_Asian_Sweep_BUY',
              'type_time': mt5.ORDER_TIME_GTC,
              'type_filling': mt5.ORDER_FILLING_IOC,
          }
          result = mt5.order_send(request)
          if result.retcode == mt5.TRADE_RETCODE_DONE:
            print('BUY Order Executed Successfully!')
            daily_trade_count += 1

        # Bearish Sweep (Sell Signal)
        elif prev_bar['high'] > asia_high and prev_bar['close'] < asia_high:
          sl = prev_bar['high'] + (EXTRA_SL_POINTS * point)
          risk = sl - bid
          tp = bid - (risk * RISK_REWARD_RATIO)

          request = {
              'action': mt5.TRADE_ACTION_DEAL,
              'symbol': SYMBOL,
              'volume': FIXED_LOT_SIZE,
              'type': mt5.ORDER_TYPE_SELL,
              'price': bid,
              'sl': sl,
              'tp': tp,
              'magic': 776655,
              'comment': 'Render_Asian_Sweep_SELL',
              'type_time': mt5.ORDER_TIME_GTC,
              'type_filling': mt5.ORDER_FILLING_IOC,
          }
          result = mt5.order_send(request)
          if result.retcode == mt5.TRADE_RETCODE_DONE:
            print('SELL Order Executed Successfully!')
            daily_trade_count += 1

    time.sleep(10)  # Check every 10 seconds


if __name__ == '__main__':
  run_bot()
