"""Bounded, synchronized single-producer/single-consumer mmap ring.

Pass this object only while spawning child processes from the same supervisor.
Order/trade payloads aren't sent through multiprocessing queues or pipes.
The semaphores are intentional: this implementation is safe, not lock-free.
"""
from contextlib import contextmanager
import mmap
from pathlib import Path
from struct import Struct

HEADER = Struct("<8sII")
COUNTER = Struct("<Q")
MAGIC = b"CMRING01"
DATA_OFFSET = 4096
READ_OFFSET, WRITE_OFFSET = 64, 128


class MappedRing:
    def __init__(self, path, capacity, record_size, context):
        if not isinstance(capacity, int) or not 1 <= capacity <= 1_048_576:
            raise ValueError("capacity must be between 1 and 1,048,576")
        if not isinstance(record_size, int) or not 1 <= record_size <= 4096:
            raise ValueError("record_size must be between 1 and 4096")
        self.path = str(Path(path).resolve())
        self.capacity, self.record_size = capacity, record_size
        self.read_lock = context.Lock()
        self.write_lock = context.Lock()
        self.free = context.BoundedSemaphore(capacity)
        self.ready = context.BoundedSemaphore(capacity)
        # BoundedSemaphore starts full. Only free slots are initially available.
        for _ in range(capacity):
            self.ready.acquire()
        self._file = self._map = None
        self._validated = False
        size = DATA_OFFSET + capacity * record_size
        with open(self.path, "xb") as stream:
            stream.truncate(size)
        self._open()
        HEADER.pack_into(self._map, 0, MAGIC, capacity, record_size)
        COUNTER.pack_into(self._map, READ_OFFSET, 0)
        COUNTER.pack_into(self._map, WRITE_OFFSET, 0)
        # Touch mapped pages before the workload; this isn't a real-time guarantee.
        for offset in range(DATA_OFFSET, size, 4096):
            self._map[offset] = 0
        self._validated = True

    def __getstate__(self):
        state = self.__dict__.copy()
        state['_file'] = state['_map'] = None
        state['_validated'] = False
        return state

    def _open(self):
        if self._map is None:
            self._file = open(self.path, 'r+b', buffering=0)
            self._map = mmap.mmap(self._file.fileno(), 0, access=mmap.ACCESS_WRITE)

    def attach(self):
        self._open()
        if not self._validated:
            if HEADER.unpack_from(self._map) != (MAGIC, self.capacity, self.record_size):
                raise ValueError("Ring header does not match its configuration")
            self._validated = True
        return self

    @contextmanager
    def _slot(self, writing, timeout):
        self.attach()
        acquired = self.free if writing else self.ready
        published = self.ready if writing else self.free
        if not acquired.acquire(timeout=timeout):
            raise TimeoutError("Ring full" if writing else "Ring empty")
        counter = WRITE_OFFSET if writing else READ_OFFSET
        counter_lock = self.write_lock if writing else self.read_lock
        # Only this endpoint changes its own cursor (the SPSC contract).
        # Observers take the locks used for commits below.
        index = COUNTER.unpack_from(self._map, counter)[0]
        offset = DATA_OFFSET + index % self.capacity * self.record_size
        view = memoryview(self._map)[offset:offset + self.record_size]
        try:
            yield view
        except BaseException:
            acquired.release()
            raise
        else:
            with counter_lock:
                COUNTER.pack_into(self._map, counter, index + 1)
            published.release()
        finally:
            view.release()

    def write(self, timeout=10):
        return self._slot(True, timeout)

    def read(self, timeout=10):
        return self._slot(False, timeout)

    def counts(self):
        self.attach()
        with self.read_lock:
            with self.write_lock:
                read = COUNTER.unpack_from(self._map, READ_OFFSET)[0]
                written = COUNTER.unpack_from(self._map, WRITE_OFFSET)[0]
        return {'written': written, 'read': read, 'pending': written - read}

    def close(self):
        self._validated = False
        if self._map is not None:
            self._map.close()
            self._map = None
        if self._file is not None:
            self._file.close()
            self._file = None
