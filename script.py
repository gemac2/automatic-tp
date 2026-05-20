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
    elif currency_name in ["ETHUSDT", "UNFIUSDT", "METISUSDT", "ZECUSDT", "CLANKERUSDT"]:
        price = "{:.2f}".format(buyback_price)
    elif currency_name in ["LPTUSDT", "OGUSDT", "QTUMUSDT",  "ASRUSDT", "LINKUSDT", "ETHFIUSDT", "ENSUSDT", "AUCTIONUSDT", "EOSUSDT", "ALICEUSDT", "UNIUSDT", "FILUSDT", "UMAUSDT", "OMNIUSDT", "IOUSDT", "AVAXUSDT", "ORDIUSDT", "ARUSDT", "ZROUSDT", "ZENUSDT", "BONDUSDT", "SOLUSDT", "BALUSDT", "NEARUSDT", "SCRUSDT", "XTZUSDT", "ORCAUSDT", "RENDERUSDT"]:
        price = "{:.3f}".format(buyback_price)
    elif currency_name in ["AMBUSDT", "XVGUSDT", "VVVUSDT", "DOLOUSDT", "NOTUSDT", "JASMYUSDT", "KEYUSDT", "TLMUSDT", "CKBUSDT", "HOTUSDT", "INJUSDT", "MEWUSDT", "TURBOUSDT", "REEFUSDT", "HMSTRUSDT"]:
        price = "{:.6f}".format(buyback_price)
    elif currency_name in ["1000FLOKIUSDT", "VETUSDT", "STMXUSDT", "1000FLOKIUSDT", "LINAUSDT", "OMUSDT", "KASUSDT", "1000RATSUSDT", "RIFUSDT", "1000LUNCUSDT", "CFXUSDT", "ONGUSDT", "1000RATSUSDT", "1000LUNCUSDT", "TOKENUSDT", "ASTRUSDT", "OMUSDT", "ALTUSDT", "ORBSUSDT", "TUSDT", "ALPACAUSDT", "SUNUSDT", "VIDTUSDT", "QUICKUSDT", "GALAUSDT", "FIOUSDT", "WOOUSDT", "CELRUSDT"]:
        price = "{:.5f}".format(buyback_price)
    elif currency_name in ["LEVERUSDT", "1000PEPEUSDT", "SPELLUSDT", "1000SATSUSDT", "DOGSUSDT", "1MBABYDOGEUSDT"]:
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
    """Cancela todas las órdenes pendientes (futuros) de un símbolo."""
    try:
        # Órdenes regulares (limit, stop, etc.)
        regular_orders = client.futures_get_open_orders(symbol=symbol)
        # Órdenes algo (TWAP, VP, etc.)
        try:
            algo_orders = client.futures_get_open_algo_orders(symbol=symbol)
        except Exception:
            algo_orders = []

        total = len(regular_orders) + len(algo_orders)

        if total == 0:
            print(f"ℹ️  No hay órdenes pendientes para {symbol}")
            return

        print(f"🔍 Se encontraron {total} órden(es) pendiente(s) para {symbol}")

        for order in regular_orders:
            client.futures_cancel_order(symbol=symbol, orderId=order['orderId'])
            order_type = order.get('type') or order.get('origType', 'N/A')
            print(f"   ✅ Cancelada orden {order['orderId']} ({order['side']} {order_type})")

        for order in algo_orders:
            client.futures_cancel_algo_order(symbol=symbol, algoId=order['algoId'])
            order_type = order.get('algoType') or order.get('type', 'N/A')
            print(f"   ✅ Cancelada orden algo {order['algoId']} ({order['side']} {order_type})")

        print(f"\n🎯 Todas las órdenes pendientes de {symbol} fueron canceladas.")

    except Exception as e:
        print(f"❌ Error al cancelar órdenes: {e}")

def cancel_take_profit(symbol, orderid):
    global order_id
    try:
        orders = client.futures_get_open_orders(symbol=symbol)
        order_ids = [order['orderId'] for order in orders]
        if orderid in order_ids:
            print('CANCELING TAKE PROFIT')
            client.futures_cancel_order(symbol=symbol, orderId=orderid)
        else:
            print('Order already executed or canceled.')
            order_id = ''
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
    
    order = client.futures_create_order(
        symbol=symbol,
        side=side,
        positionSide=position_side,
        type="LIMIT",
        timeInForce="GTC",
        quantity=qty,
        price=price,
    )

    return order['orderId']

while True:
    try:
        if state:
            positions = client.futures_position_information(symbol=symbol)

            # Buscar LONG y SHORT de forma segura
            long_pos = next((p for p in positions if p['positionSide'] == 'LONG'), None)
            short_pos = next((p for p in positions if p['positionSide'] == 'SHORT'), None)

            # Verificar si la posición ya se cerró
            if (not long_pos or float(long_pos['entryPrice']) == 0.0) and \
               (not short_pos or float(short_pos['entryPrice']) == 0.0):
                print(f"No hay posiciones abiertas para {symbol}")
                cancel_all_orders(symbol)
                state = False
                price_position = 0
                order_id = ''
                break

            # Determinar la posición activa
            active_pos = long_pos if long_pos and float(long_pos['entryPrice']) != 0.0 else short_pos
            entry_price = float(active_pos['entryPrice'])
            qty = float(active_pos['positionAmt'])
            side = active_pos['positionSide']

            # Calcular precio de take profit
            if side == 'LONG':
                take_price = ((entry_price * take_profit)/100) + entry_price
            else:
                take_price = entry_price - ((entry_price * take_profit)/100)

            if take_price <= 0:
                print('YOUR TAKE PROFIT IS NOT POSSIBLE, IT IS BELOW ZERO')
            else:
                if price_position != entry_price:
                    if order_id != '':
                        cancel_take_profit(symbol, order_id)

                    print('MODIFYING TAKE PROFIT')
                    order_id = set_take_profit(symbol, take_price, side, qty)
                    price_position = entry_price
                    print('TAKE PROFIT ORDER WAS SUCCESS')

        else:
            tick = input('ENTER THE TICK YOU WANT TO TRADE: ').upper()
            if tick != '':
                symbol = tick + 'USDT'
                take_profit = float(input('ENTER THE PERCENTAGE YOU WANT TO TAKE PROFITS: '))
                positions = client.futures_position_information(symbol=symbol)
                long_pos = next((p for p in positions if p['positionSide'] == 'LONG'), None)
                short_pos = next((p for p in positions if p['positionSide'] == 'SHORT'), None)

                if (long_pos and float(long_pos['entryPrice']) != 0.0) or \
                   (short_pos and float(short_pos['entryPrice']) != 0.0):
                    print('OPEN POSITION IN ' + symbol)
                    state = True
                else:
                    print('THERE IS NO OPEN POSITION IN ' + symbol)
            else:
                print('THE ENTERED DATA IS NOT VALID')

    except Exception as e:
        print(f"Error: {e}")
        time.sleep(5)
    time.sleep(1)
