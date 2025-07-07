import time
from binance.client import Client
import os
from dotenv import load_dotenv

# Configuración
TAKE_PROFIT_PERCENTAGE = 4  # 4% de TP

# Cargar claves API
load_dotenv()
api_key = os.getenv('BINANCE_API_KEY')
api_secret = os.getenv('BINANCE_SECRET_KEY')

client = Client(api_key, api_secret)

def get_open_positions():
    """ Obtiene todas las posiciones abiertas en Binance Futures """
    try:
        positions = client.futures_position_information()
        open_positions = [pos for pos in positions if float(pos['positionAmt']) != 0.0]
        return open_positions
    except Exception as e:
        print(f"Error al obtener posiciones abiertas: {e}")
        return []

def has_hedging(symbol, positions):
    """ Verifica si hay posiciones LONG y SHORT abiertas en el mismo par """
    long_exists = any(pos['symbol'] == symbol and pos['positionSide'] == 'LONG' and float(pos['positionAmt']) > 0 for pos in positions)
    short_exists = any(pos['symbol'] == symbol and pos['positionSide'] == 'SHORT' and float(pos['positionAmt']) < 0 for pos in positions)
    
    return long_exists and short_exists

def set_price_for_exchanges(currency_name, buyback_price):
    """ Ajusta la precisión del precio según el par """
    if currency_name in ["BTCUSDT", "NMRUSDT", "TRBUSDT", "NEOUSDT"]:
        return "{:.1f}".format(buyback_price)
    elif currency_name in ["ETHUSDT", "UNFIUSDT", "METISUSDT", "ZECUSDT"]:
        return "{:.2f}".format(buyback_price)
    elif currency_name in ["LPTUSDT", "LINKUSDT", "ETHFIUSDT", "ENSUSDT", "AUCTIONUSDT", "EOSUSDT", "ALICEUSDT", "UNIUSDT", "FILUSDT", "UMAUSDT", "OMNIUSDT", "IOUSDT", "AVAXUSDT", "ORDIUSDT", "ARUSDT", "ZROUSDT", "ZENUSDT", "BONDUSDT", "SOLUSDT", "BALUSDT", "NEARUSDT", "SCRUSDT", "XTZUSDT", "MEUSDT"]:
        return "{:.3f}".format(buyback_price)
    elif currency_name in ["AMBUSDT", "XVGUSDT", "NOTUSDT", "JASMYUSDT", "KEYUSDT", "TLMUSDT", "CKBUSDT", "HOTUSDT", "INJUSDT", "MEWUSDT", "TURBOUSDT", "REEFUSDT", "HMSTRUSDT"]:
        return "{:.6f}".format(buyback_price)
    elif currency_name in ["1000FLOKIUSDT", "VETUSDT", "STMXUSDT", "LINAUSDT", "OMUSDT", "KASUSDT", "RIFUSDT", "CFXUSDT", "ONGUSDT", "TOKENUSDT", "ASTRUSDT", "OMUSDT", "ALTUSDT", "ORBSUSDT", "TUSDT", "ALPACAUSDT", "SUNUSDT", "VIDTUSDT", "QUICKUSDT", "GALAUSDT", "FIOUSDT", "WOOUSDT", "CELRUSDT"]:
        return "{:.5f}".format(buyback_price)
    elif currency_name in ["LEVERUSDT", "1000PEPEUSDT", "SPELLUSDT", "1000SATSUSDT", "DOGSUSDT", "1MBABYDOGEUSDT"]:
        return "{:.7f}".format(buyback_price)
    else:
        return "{:.4f}".format(buyback_price)

def set_take_profit(symbol, price, position_side, qty):
    """ Coloca una orden de take profit si no hay cobertura """
    price = set_price_for_exchanges(symbol, price)
    side = 'SELL' if position_side == 'LONG' else 'BUY'
    
    try:
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
    except Exception as e:
        print(f"Error al colocar TP en {symbol}: {e}")
        return None

def cancel_all_orders(symbol):
    """ Cancela todas las órdenes pendientes de un símbolo """
    try:
        orders = client.futures_get_open_orders(symbol=symbol)
        for order in orders:
            client.futures_cancel_order(symbol=symbol, orderId=order['orderId'])
        print(f"Órdenes pendientes de {symbol} canceladas.")
    except Exception as e:
        print(f"Error al cancelar órdenes: {e}")

# Bucle principal
while True:
    try:
        open_positions = get_open_positions()

        if open_positions:
            print(f"Se encontraron {len(open_positions)} posiciones abiertas.")
            checked_symbols = set()

            for position in open_positions:
                symbol = position['symbol']
                
                # Evita repetir el chequeo para un símbolo si ya se verificó
                if symbol in checked_symbols:
                    continue
                checked_symbols.add(symbol)

                # Si hay una cobertura abierta en este par, NO colocar TP
                if has_hedging(symbol, open_positions):
                    print(f"Se detectó cobertura en {symbol}. No se colocará Take Profit.")
                    continue

                # Buscar la posición actual sin cobertura
                entry_price = float(position['entryPrice'])
                position_side = position['positionSide']
                qty = abs(float(position['positionAmt']))  # Asegurar que sea positivo
                
                if position_side == 'LONG':
                    take_price = entry_price * (1 + TAKE_PROFIT_PERCENTAGE / 100)
                else:
                    take_price = entry_price * (1 - TAKE_PROFIT_PERCENTAGE / 100)
                
                if take_price > 0:
                    print(f"Colocando Take Profit en {symbol}: {take_price}")
                    order_id = set_take_profit(symbol, take_price, position_side, qty)
                    if order_id:
                        print(f"Orden TP colocada en {symbol} con ID {order_id}")
                else:
                    print(f"No es posible colocar un TP en {symbol}, precio negativo.")
                
                time.sleep(3)
                updated_positions = get_open_positions()

                # Cancelar órdenes pendientes si un TP fue tomado y la posición desapareció
                for checked_symbol in checked_symbols:
                    still_open = any(pos['symbol'] == checked_symbol for pos in updated_positions)
                    if not still_open:
                        print(f"Posición en {checked_symbol} cerrada, cancelando órdenes pendientes...")
                        cancel_all_orders(checked_symbol)

        else:
            print("No hay posiciones abiertas, esperando...")

    except Exception as e:
        print(f"Error: {e}")

    time.sleep(5)  # Evitar consultas excesivas a Binance
