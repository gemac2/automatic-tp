import time
from binance.client import Client
from decimal import Decimal, ROUND_DOWN
import os
from dotenv import load_dotenv

symbol = ''  # You can adjust the symbol as per your needs
take_profit = 0  # Percentage value
state = False
price_position = 0
order_id = ''

# Binance API Key and Secret Key
load_dotenv()
api_key = os.getenv('BINANCE_API_KEY')
api_secret = os.getenv('BINANCE_SECRET_KEY')

client = Client(api_key, api_secret)

def search_ticks():
    ticks = []
    try:
        list_ticks = client.futures_symbol_ticker()
    except Exception as e:
        print(f"Error while getting ticks: {e}")
        return ticks

    for tick in list_ticks:
        if tick['symbol'][-4:] != 'USDT':
            continue
        if tick['symbol'] == "USDCUSDT":
            continue
        ticks.append(tick['symbol'])

    return ticks

def set_price_for_exchanges(currency_name, buyback_price):
    price = ""
    if currency_name in ["BTCUSDT", "NMRUSDT", "TRBUSDT", "NEOUSDT"]:
        price = "{:.1f}".format(buyback_price)
    elif currency_name in ["ETHUSDT", "UNFIUSDT", "METISUSDT"]:
        price = "{:.2f}".format(buyback_price)
    elif currency_name in ["LPTUSDT", "LINKUSDT", "ETHFIUSDT", "ENSUSDT", "AUCTIONUSDT", "EOSUSDT", "ALICEUSDT", "UNIUSDT", "FILUSDT", "UMAUSDT", "OMNIUSDT", "IOUSDT", "AVAXUSDT", "ORDIUSDT", "ARUSDT", "ZROUSDT", "ZENUSDT", "BONDUSDT"]:
        price = "{:.3f}".format(buyback_price)
    elif currency_name in ["AMBUSDT", "GALAUSDT", "XRPUSDT", "XVGUSDT", "NOTUSDT", "JASMYUSDT", "KEYUSDT", "TLMUSDT", "CKBUSDT", "HOTUSDT", "INJUSDT", "MEWUSDT", "TURBOUSDT"]:
        price = "{:.6f}".format(buyback_price)
    elif currency_name in ["1000FLOKIUSDT", "VETUSDT", "STMXUSDT", "1000FLOKIUSDT", "LINAUSDT", "OMUSDT", "KASUSDT", "1000RATSUSDT", "RIFUSDT", "1000LUNCUSDT", "CFXUSDT", "ONGUSDT", "1000RATSUSDT", "1000LUNCUSDT", "TOKENUSDT", "ASTRUSDT", "OMUSDT", "ALTUSDT"]:
        price = "{:.5f}".format(buyback_price)
    elif currency_name in ["LEVERUSDT", "1000PEPEUSDT", "SPELLUSDT", "1000SATSUSDT"]:
        price = "{:.7f}".format(buyback_price)
    else:
        price = "{:.4f}".format(buyback_price)
    
    return price
    

def qty_step(symbol, price):
    futures_ticks = search_ticks()
    if symbol not in futures_ticks:
        print(f"Error: Symbol {symbol} not found in futures ticks.")
        return None
    
    symbol_info = client.futures_exchange_info()
    for info in symbol_info['symbols']:
        if info['symbol'] == symbol:
            step_size = float(info['filters'][2]['stepSize'])
            qty = (float(price) / step_size) * step_size
            format_price = set_price_for_exchanges(symbol, qty)
            return format_price
    return None

def cancel_all_orders(symbol):
    try:
        orders = client.futures_get_open_orders(symbol=symbol)
        for order in orders:
            client.futures_cancel_order(symbol=symbol, orderId=order['orderId'])
        print(f"All pending orders for {symbol} have been canceled.")
    except Exception as e:
        print(f"Error while canceling orders: {e}")

def cancel_take_profit(symbol, orderid):
    try:
        # Check if the order still exists before attempting to cancel it
        orders = client.futures_get_open_orders(symbol=symbol)
        order_ids = [order['orderId'] for order in orders]
        if orderid in order_ids:
            print('CANCELING TAKE PROFIT')
            client.futures_cancel_order(symbol=symbol, orderId=orderid)
        else:
            print('Order already executed or canceled, no need to cancel again.')
    except Exception as e:
        print(f"Error while canceling take profit order: {e}")


def set_take_profit(symbol, price, position_side, qty):
    price = qty_step(symbol, price)
    side = ""

    if position_side == 'LONG':
        side = 'SELL'
    else:
        side = 'BUY'
        qty = qty * -1
    

    # PLACE TAKE PROFIT ORDER
    order = client.futures_create_order(
        symbol=symbol,
        side=side,
        positionSide=position_side,
        type="LIMIT",
        timeInForce="GTC",
        quantity=qty,
        price=price,
    )

    order_id = order['orderId']

    return order_id

while True:
    try:
        if state:
            # Open Positions
            positions = client.futures_position_information(symbol=symbol)
            if float(positions[0]['entryPrice']) != 0.0 or float(positions[1]['entryPrice']) != 0.0:
                entry_price = float(positions[0]['entryPrice'])
                if entry_price == 0.0:
                    entry_price = float(positions[1]['entryPrice'])
                take_price = 0
                if positions[0]['positionSide'] == 'LONG' and float(positions[0]['entryPrice']) != 0.0:
                    take_price = ((entry_price * take_profit)/100)+entry_price
                else:
                    take_price = entry_price-((entry_price * take_profit)/100)

                if take_price < 0:
                    print('YOUR TAKE PROFIT IS NOT POSSIBLE, IT IS BELOW ZERO')
                else:
                    # Place take profit
                    if price_position != entry_price:
                        print(isinstance(order_id, str))
                        if order_id != '':
                            cancel_take_profit(symbol, order_id)

                        print('MODIFYING TAKE PROFIT')
                        side = positions[0]['positionSide']
                        qty = float(positions[0]['positionAmt'])
                        if qty == 0.0 :
                           qty = float(positions[1]['positionAmt'])
                           side = positions[1]['positionSide']
                        order_id = set_take_profit(symbol, take_price, side, qty)
                        price_position = entry_price
                        print('TAKE PROFIT ORDER WAS SUCCESS')
            else:
                print('THERE IS NO OPEN POSITION IN ' + symbol)
                state = False
                price_position = 0
                order_id = ''
                cancel_all_orders(symbol)
                break

        else:
            tick = input('ENTER THE TICK YOU WANT TO TRADE: ').upper()
            if tick != '':
                symbol = tick + 'USDT'
                take_profit = float(input('ENTER THE PERCENTAGE YOU WANT TO TAKE PROFITS: '))
                if take_profit != '':
                    # Open Positions
                    positions = client.futures_position_information(symbol=symbol)
                    if float(positions[0]['entryPrice']) != 0.0 or float(positions[1]['entryPrice']) != 0.0:
                        print('OPEN POSITION IN ' + symbol)
                        state = True
                    else:
                        print('THERE IS NO OPEN POSITION IN ' + symbol)
                else:
                    print('THE ENTERED DATA IS NOT VALID')
            else:
                print('THE ENTERED DATA IS NOT VALID')

    except Exception as e:
        print(f"Error: {e}")
        time.sleep(5)
    time.sleep(1)