"""Metrics/report helpers; reporting stays outside native matching."""
from array import array
import platform
from statistics import median
import sys


def distribution(samples):
    if not samples:
        return {'samples': 0, 'median_us': None, 'p95_us': None, 'p99_us': None, 'max_us': None}
    ordered = sorted(samples)
    return {'samples': len(samples), 'median_us': round(median(ordered) / 1000, 3),
            'p95_us': round(ordered[int(.95 * (len(ordered) - 1))] / 1000, 3),
            'p99_us': round(ordered[int(.99 * (len(ordered) - 1))] / 1000, 3),
            'max_us': round(ordered[-1] / 1000, 3)}


def environment():
    return {'python': sys.version, 'platform': platform.platform(), 'machine': platform.machine(),
            'processor': platform.processor(), 'clock': 'time.perf_counter_ns'}


def save_samples(path, native, pipeline):
    """Two little-endian u64 columns, native-call ns then pipeline ns per order."""
    records = array('Q')
    for a, b in zip(native, pipeline):
        records.extend((a, b))
    if sys.byteorder != 'little':
        records.byteswap()
    with open(path, 'xb') as stream:
        records.tofile(stream)
