# distutils: language = c++
# cython: language_level=3, boundscheck=False, wraparound=False, initializedcheck=False
"""Native limit matcher. No Python objects are used in _submit/_match loops.

C++ maps/deques may allocate native memory. This is not an allocation-free or
hard-real-time engine. Python-facing wrappers run with the GIL as usual.
"""
from libc.stdint cimport uint8_t, uint32_t, uint64_t, int64_t
from libc.stdlib cimport calloc, free
from libcpp.map cimport map as cppmap
from libcpp.deque cimport deque as cppdeque
from libcpp.unordered_map cimport unordered_map
from cython.operator cimport dereference as deref, predecrement as dec

cdef struct OrderC:
    uint64_t id
    uint64_t quantity
    int64_t price
    uint32_t symbol
    uint8_t side

cdef struct TradeC:
    uint64_t id
    uint64_t buy_id
    uint64_t sell_id
    uint32_t symbol
    int64_t price
    uint64_t quantity
    uint64_t entered

cdef uint64_t load64(const unsigned char* p) noexcept nogil:
    cdef uint64_t value = 0
    cdef int j
    for j in range(8):
        value |= (<uint64_t>p[j]) << (8*j)
    return value

cdef void store64(unsigned char* p, uint64_t value) noexcept nogil:
    cdef int j
    for j in range(8):
        p[j] = <unsigned char>(value >> (8*j))

cdef class NativeBook:
    cdef OrderC* pool
    cdef TradeC* executions
    cdef uint64_t count, capacity, emitted, next_trade, last_entered
    cdef uint64_t cleared_levels
    cdef bint busy
    cdef cppmap[uint64_t, cppdeque[uint64_t]] bids, asks
    cdef unordered_map[uint64_t, uint64_t] ids

    def __cinit__(self, uint64_t capacity=100000):
        if capacity < 1 or capacity > 10000000:
            raise ValueError("Native capacity must be between 1 and 10,000,000")
        self.capacity = capacity
        self.pool = <OrderC*>calloc(capacity, sizeof(OrderC))
        self.executions = <TradeC*>calloc(capacity, sizeof(TradeC))
        if self.pool == NULL or self.executions == NULL:
            raise MemoryError()
        self.next_trade = 1
        self.ids.reserve(capacity)

    def __dealloc__(self):
        free(self.pool)
        free(self.executions)

    cdef int _match(self, cppmap[uint64_t, cppdeque[uint64_t]]& opposite,
                     OrderC* incoming, uint64_t entered) except -1 nogil:
        cdef cppmap[uint64_t, cppdeque[uint64_t]].iterator it
        cdef uint64_t base = (<uint64_t>incoming.symbol) << 48
        cdef uint64_t end = (<uint64_t>(incoming.symbol + 1)) << 48
        cdef uint64_t key, index, quantity
        cdef OrderC* resting
        cdef TradeC* trade
        while incoming.quantity:
            if incoming.side == 1:
                it = opposite.lower_bound(base)
                if it == opposite.end():
                    break
                key = deref(it).first
                if key >= end or <int64_t>(key - base) > incoming.price:
                    break
            else:
                it = opposite.lower_bound(end)
                if it == opposite.begin():
                    break
                dec(it)
                key = deref(it).first
                if key < base or <int64_t>(key - base) < incoming.price:
                    break
            index = deref(it).second.front()
            resting = &self.pool[index]
            quantity = min(incoming.quantity, resting.quantity)
            trade = &self.executions[self.emitted]
            trade.id = self.next_trade
            self.next_trade += 1
            trade.buy_id = incoming.id if incoming.side == 1 else resting.id
            trade.sell_id = resting.id if incoming.side == 1 else incoming.id
            trade.symbol = incoming.symbol
            trade.price = resting.price
            trade.quantity = quantity
            trade.entered = entered
            self.emitted += 1
            incoming.quantity -= quantity
            resting.quantity -= quantity
            if not resting.quantity:
                deref(it).second.pop_front()
                if deref(it).second.empty():
                    opposite.erase(it)
                    self.cleared_levels += 1
        return 0

    cdef int _submit(self, const unsigned char* p) except -99 nogil:
        cdef uint64_t oid = load64(p)
        cdef uint32_t symbol = <uint32_t>(p[8] | (<uint32_t>p[9] << 8)
            | (<uint32_t>p[10] << 16) | (<uint32_t>p[11] << 24))
        cdef uint8_t side = p[12]
        cdef int64_t price = <int64_t>load64(p + 16)
        cdef uint64_t quantity = load64(p + 24)
        cdef uint64_t entered = load64(p + 32)
        cdef OrderC* incoming
        cdef uint64_t key
        if not oid or oid >= (1ULL << 63) or symbol >= 4 or side < 1 or side > 2 or price <= 0 or price >= (1LL << 48) or not quantity or quantity >= (1ULL << 32) or entered >= (1ULL << 63):
            return -1
        if self.ids.count(oid):
            return -2
        if self.count >= self.capacity:
            return -3
        self.emitted = 0
        self.cleared_levels = 0
        self.last_entered = entered
        incoming = &self.pool[self.count]
        incoming.id, incoming.symbol, incoming.side = oid, symbol, side
        incoming.price, incoming.quantity = price, quantity
        self.ids[oid] = self.count
        if side == 1:
            self._match(self.asks, incoming, entered)
        else:
            self._match(self.bids, incoming, entered)
        if incoming.quantity:
            key = ((<uint64_t>symbol) << 48) | <uint64_t>price
            if side == 1:
                self.bids[key].push_back(self.count)
            else:
                self.asks[key].push_back(self.count)
        self.count += 1
        return 0

    def submit(self, const unsigned char[::1] slot):
        cdef int result
        if slot.shape[0] != 40:
            raise ValueError("Native order record must be 40 bytes")
        if self.busy:
            raise RuntimeError("Use one thread per NativeBook")
        self.busy = True
        try:
            with nogil:
                result = self._submit(&slot[0])
        finally:
            self.busy = False
        if result == -1:
            raise ValueError("Invalid native order")
        if result == -2:
            raise ValueError("Duplicate global order ID")
        if result == -3:
            raise ValueError("Native capacity exhausted; start a new run")
        return self.emitted

    def write_trade(self, uint64_t index, unsigned char[::1] target, uint64_t completed_ns):
        cdef TradeC* t
        cdef unsigned char* p
        cdef int j
        if self.busy:
            raise RuntimeError("Use one thread per NativeBook")
        if index >= self.emitted or target.shape[0] != 64:
            raise ValueError("Invalid trade index or record size")
        t = &self.executions[index]
        p = &target[0]
        # Keep the GIL during this small export so another Python thread cannot
        # replace the execution array between the busy check and the copy.
        store64(p, t.id)
        store64(p + 8, t.buy_id)
        store64(p + 16, t.sell_id)
        for j in range(4):
            p[24+j] = <unsigned char>(t.symbol >> (8*j))
            p[28+j] = 0
        store64(p + 32, <uint64_t>t.price)
        store64(p + 40, t.quantity)
        store64(p + 48, t.entered)
        store64(p + 56, completed_ns)

    def remaining(self, uint64_t oid):
        if self.busy:
            raise RuntimeError("Use one thread per NativeBook")
        if not self.ids.count(oid):
            return 0
        return self.pool[self.ids[oid]].quantity

    def quote(self, uint32_t symbol=0):
        cdef uint64_t base, end, bid = 0, ask = 0, bqty = 0, aqty = 0, index
        cdef cppmap[uint64_t, cppdeque[uint64_t]].iterator it
        if self.busy:
            raise RuntimeError("Use one thread per NativeBook")
        if symbol >= 4:
            raise ValueError("Unknown symbol")
        base, end = (<uint64_t>symbol) << 48, (<uint64_t>(symbol+1)) << 48
        it = self.bids.lower_bound(end)
        if it != self.bids.begin():
            dec(it)
            if deref(it).first >= base:
                bid = deref(it).first - base
                for index in deref(it).second:
                    bqty += self.pool[index].quantity
        it = self.asks.lower_bound(base)
        if it != self.asks.end() and deref(it).first < end:
            ask = deref(it).first - base
            for index in deref(it).second:
                aqty += self.pool[index].quantity
        return bid, bqty, ask, aqty

    @property
    def order_count(self):
        return self.count

    @property
    def levels_cleared(self):
        return self.cleared_levels
