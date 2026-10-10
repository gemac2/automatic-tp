import time
from binance.client import Client
from decimal import Decimal, ROUND_DOWN
import os
from dotenv import load_dotenv

symbol = '' 
take_profit = 0  # Valor en porcentaje
state = False
price_position = 0
order_id = ''

# Carga de variables de entorno
load_dotenv()
api_key = os.getenv('BINANCE_API_KEY')
api_secret = os.getenv('BINANCE_SECRET_KEY')

client = Client(api_key, api_secret)

def sync_time():
    """Sincroniza el reloj local con el servidor de Binance para evitar errores -1021."""
    try:
        server_time = client.get_server_time()
        client.timestamp_offset = server_time['serverTime'] - int(time.time() * 1000)
        print(f"🕒 Reloj sincronizado. Offset: {client.timestamp_offset} ms")
    except Exception as e:
        print(f"⚠️ No se pudo sincronizar el tiempo: {e}")

sync_time()

def search_ticks():
    ticks = []
    try:
        list_ticks = client.futures_symbol_ticker()
    except Exception as e:
        print(f"Error al obtener tickers: {e}")
        return ticks

    for tick in list_ticks:
        if not tick['symbol'].endswith('USDT') or tick['symbol'] == "USDCUSDT":
            continue
        ticks.append(tick['symbol'])

    return ticks

def set_price_for_exchanges(currency_name, buyback_price):
    if currency_name in ["BTCUSDT", "NMRUSDT", "TRBUSDT", "NEOUSDT"]:
        return "{:.1f}".format(buyback_price)
    elif currency_name in ["ETHUSDT", "UNFIUSDT", "METISUSDT", "ZECUSDT", "CLANKERUSDT"]:
        return "{:.2f}".format(buyback_price)
    elif currency_name in ["LPTUSDT", "OGUSDT", "VVVUSDT", "QTUMUSDT", "ASRUSDT", "LINKUSDT", "ETHFIUSDT", "ENSUSDT", "AUCTIONUSDT", "EOSUSDT", "ALICEUSDT", "UNIUSDT", "FILUSDT", "UMAUSDT", "OMNIUSDT", "IOUSDT", "AVAXUSDT", "ORDIUSDT", "ARUSDT", "ZROUSDT", "ZENUSDT", "BONDUSDT", "SOLUSDT", "BALUSDT", "NEARUSDT", "SCRUSDT", "XTZUSDT", "ORCAUSDT", "RENDERUSDT"]:
        return "{:.3f}".format(buyback_price)
    elif currency_name in ["AMBUSDT", "XVGUSDT", "DOLOUSDT", "NOTUSDT", "JASMYUSDT", "KEYUSDT", "TLMUSDT", "CKBUSDT", "HOTUSDT", "INJUSDT", "MEWUSDT", "TURBOUSDT", "REEFUSDT", "HMSTRUSDT"]:
        return "{:.6f}".format(buyback_price)
    elif currency_name in ["1000FLOKIUSDT", "VETUSDT", "STMXUSDT", "LINAUSDT", "OMUSDT", "KASUSDT", "1000RATSUSDT", "RIFUSDT", "1000LUNCUSDT", "CFXUSDT", "ONGUSDT", "TOKENUSDT", "ASTRUSDT", "ALTUSDT", "ORBSUSDT", "TUSDT", "ALPACAUSDT", "SUNUSDT", "VIDTUSDT", "QUICKUSDT", "GALAUSDT", "FIOUSDT", "WOOUSDT", "CELRUSDT"]:
        return "{:.5f}".format(buyback_price)
    elif currency_name in ["LEVERUSDT", "1000PEPEUSDT", "IOSTUSDT", "VTHOUSDT", "SPELLUSDT", "1000SATSUSDT", "DOGSUSDT", "1MBABYDOGEUSDT"]:
        return "{:.7f}".format(buyback_price)
    else:
        return "{:.4f}".format(buyback_price)

def qty_step(symbol, price):
    futures_ticks = search_ticks()
    if symbol not in futures_ticks:
        print(f"Error: El símbolo {symbol} no existe en Binance Futures.")
        return None
    
    return set_price_for_exchanges(symbol, price)

def cancel_all_orders(symbol):
    """Cancela todas las órdenes pendientes de un símbolo."""
    try:
        regular_orders = client.futures_get_open_orders(symbol=symbol)
        try:
            algo_orders = client.futures_get_open_algo_orders(symbol=symbol)
        except Exception:
            algo_orders = []

        total = len(regular_orders) + len(algo_orders)

        if total == 0:
            print(f"ℹ️ No hay órdenes pendientes para {symbol}")
            return

        print(f"🔍 Se encontraron {total} orden(es) pendiente(s) para {symbol}")

        for order in regular_orders:
            client.futures_cancel_order(symbol=symbol, orderId=order['orderId'])
            order_type = order.get('type') or order.get('origType', 'N/A')
            print(f"   ✅ Cancelada orden {order['orderId']} ({order['side']} {order_type})")

        for order in algo_orders:
            client.futures_cancel_algo_order(symbol=symbol, algoId=order['algoId'])
            order_type = order.get('algoType') or order.get('type', 'N/A')
            print(f"   ✅ Cancelada orden algo {order['algoId']} ({order['side']} {order_type})")

        print(f"🎯 Todas las órdenes pendientes de {symbol} fueron canceladas.")

    except Exception as e:
        print(f"❌ Error al cancelar órdenes: {e}")

def cancel_take_profit(symbol, orderid):
    global order_id
    try:
        orders = client.futures_get_open_orders(symbol=symbol)
        order_ids = [order['orderId'] for order in orders]
        if orderid in order_ids:
            print('CANCELANDO TAKE PROFIT PREVIO...')
            client.futures_cancel_order(symbol=symbol, orderId=orderid)
        else:
            print('La orden ya fue ejecutada o cancelada.')
            order_id = ''
    except Exception as e:
        print(f"Error al cancelar la orden de take profit: {e}")

def set_take_profit(symbol, price, position_side, qty):
    formatted_price = qty_step(symbol, price)
    side = 'SELL' if position_side == 'LONG' else 'BUY'
    
    # Binance exige cantidades positivas para el parámetro quantity
    qty = abs(qty)

    order = client.futures_create_order(
        symbol=symbol,
        side=side,
        positionSide=position_side,
        type="LIMIT",
        timeInForce="GTC",
        quantity=qty,
        price=formatted_price,
    )

    return order['orderId']

while True:
    try:
        if state:
            positions = client.futures_position_information(symbol=symbol)

            long_pos = next((p for p in positions if p['positionSide'] == 'LONG'), None)
            short_pos = next((p for p in positions if p['positionSide'] == 'SHORT'), None)

            has_long = long_pos and float(long_pos['entryPrice']) > 0.0 and float(long_pos['positionAmt']) != 0.0
            has_short = short_pos and float(short_pos['entryPrice']) > 0.0 and float(short_pos['positionAmt']) != 0.0

            # 🚨 ESCENARIO 1: COBERTURA ACTIVADA (LONG y SHORT simultáneos)
            if has_long and has_short:
                print(f"⚠️ ¡COBERTURA ACTIVADA EN {symbol}! Canceling Take Profit and stopping bot...")
                cancel_all_orders(symbol)
                state = False
                price_position = 0
                order_id = ''
                continue

            # 🚨 ESCENARIO 2: POSICIÓN CERRADA (Se tocó TP o se cerró manualmente)
            if not has_long and not has_short:
                print(f"✅ Posición cerrada en {symbol}. Limpiando órdenes pendientes...")
                cancel_all_orders(symbol)
                state = False
                price_position = 0
                order_id = ''
                continue

            # 🟢 ESCENARIO 3: SOLO UNA POSICIÓN ACTIVA
            active_pos = long_pos if has_long else short_pos
            entry_price = float(active_pos['entryPrice'])
            qty = float(active_pos['positionAmt'])
            side = active_pos['positionSide']

            # Cálculo de Take Profit
            if side == 'LONG':
                take_price = entry_price * (1 + (take_profit / 100))
            else:
                take_price = entry_price * (1 - (take_profit / 100))

            if take_price <= 0:
                print('EL TAKE PROFIT ES MENOR O IGUAL A CERO')
            else:
                if price_position != entry_price:
                    if order_id != '':
                        cancel_take_profit(symbol, order_id)

                    print('ESTABLECIENDO NUEVO TAKE PROFIT...')
                    order_id = set_take_profit(symbol, take_price, side, qty)
                    price_position = entry_price
                    print(f'✅ Take Profit colocado correctamente en {take_price}')

        else:
            tick = input('INGRESA EL TICKER (ej. BTC, ETH): ').strip().upper()
            if tick:
                symbol = tick + 'USDT'
                take_profit = float(input('INGRESA EL PORCENTAJE DE TAKE PROFIT (%): '))
                
                positions = client.futures_position_information(symbol=symbol)
                long_pos = next((p for p in positions if p['positionSide'] == 'LONG'), None)
                short_pos = next((p for p in positions if p['positionSide'] == 'SHORT'), None)

                has_long = long_pos and float(long_pos['entryPrice']) > 0.0 and float(long_pos['positionAmt']) != 0.0
                has_short = short_pos and float(short_pos['entryPrice']) > 0.0 and float(short_pos['positionAmt']) != 0.0

                if has_long and has_short:
                    print(f'⚠️ Ambas posiciones están abiertas en {symbol}. La cobertura ya fue activada.')
                elif has_long or has_short:
                    print(f'🟢 POSICIÓN ENCONTRADA EN {symbol}. Iniciando monitoreo...')
                    state = True
                else:
                    print(f'❌ No hay posiciones abiertas en {symbol}')
            else:
                print('⚠️ El ticker ingresado no es válido.')

    except Exception as e:
        print(f"❌ Error en la ejecución: {e}")
        if '-1021' in str(e):
            sync_time()
        time.sleep(5)

    time.sleep(1)