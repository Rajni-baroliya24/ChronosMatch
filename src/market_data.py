"""Akash module: fixed-width binary order messages with memoryview parsing.

Wire format (network byte order, 34 bytes):
  uint64 order_id; 8-byte ASCII symbol (NUL padded); uint8 side (1 BUY/2 SELL);
  uint64 price_ticks; uint32 quantity; uint64 timestamp.

unpack_from(memoryview) avoids making a separate bytes slice. Constructing an
Order still allocates a Python object: this is NOT end-to-end zero-copy.
"""
import struct
from .models import Order

MESSAGE = struct.Struct('!Q8sBQIQ')
MESSAGE_SIZE = MESSAGE.size
_SIDE_TO_WIRE = {'BUY': 1, 'SELL': 2}
_WIRE_TO_SIDE = {1: 'BUY', 2: 'SELL'}


def encode_order(order: Order) -> bytes:
    try:
        return MESSAGE.pack(order.order_id, order.symbol.encode('ascii'),
                            _SIDE_TO_WIRE[order.side], order.price,
                            order.quantity, order.timestamp)
    except (struct.error, OverflowError) as exc:
        raise ValueError('order fields exceed wire-format limits') from exc


def decode_order(buffer: bytes | bytearray | memoryview, offset: int = 0) -> Order:
    view = memoryview(buffer)
    if offset < 0 or len(view) - offset < MESSAGE_SIZE:
        raise ValueError('incomplete order message')
    order_id, symbol_bytes, side_code, price, quantity, timestamp = MESSAGE.unpack_from(view, offset)
    if side_code not in _WIRE_TO_SIDE:
        raise ValueError('invalid wire side')
    try:
        symbol = symbol_bytes.rstrip(b'\x00').decode('ascii')
    except UnicodeDecodeError as exc:
        raise ValueError('invalid symbol encoding') from exc
    return Order(order_id, symbol, _WIRE_TO_SIDE[side_code], price, quantity, timestamp)


def iter_orders(buffer: bytes | bytearray | memoryview):
    view = memoryview(buffer)
    if len(view) % MESSAGE_SIZE:
        raise ValueError('message stream has trailing bytes')
    for offset in range(0, len(view), MESSAGE_SIZE):
        yield decode_order(view, offset)
