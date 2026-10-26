import mmap
import multiprocessing as mp
import pytest
from lowlatency.audit import run_audit
from lowlatency.protocol import ORDER, pack_order
from lowlatency.ring import MappedRing


@pytest.fixture
def ring(tmp_path):
    bus = MappedRing(tmp_path / 'test.mmap', 2, ORDER.size, mp.get_context('spawn'))
    yield bus
    bus.close()


def test_wraparound_and_exact_capacity(ring):
    for group in range(10):
        for index in (group * 2 + 1, group * 2 + 2):
            with ring.write() as slot:
                assert isinstance(slot.obj, mmap.mmap)
                pack_order(slot, index, 0, 1, 10000, index, 42)
        with pytest.raises(TimeoutError, match='full'):
            with ring.write(timeout=.001):
                pass
        for index in (group * 2 + 1, group * 2 + 2):
            with ring.read() as slot:
                assert ORDER.unpack_from(slot) == (index, 0, 1, 10000, index, 42)
    assert ring.counts() == {'written': 20, 'read': 20, 'pending': 0}


def test_empty_read_has_no_side_effect(ring):
    with pytest.raises(TimeoutError, match='empty'):
        with ring.read(timeout=.001):
            pass
    assert ring.counts() == {'written': 0, 'read': 0, 'pending': 0}


def test_failed_write_is_not_published_and_failed_read_can_retry(ring):
    with pytest.raises(ValueError):
        with ring.write() as slot:
            pack_order(slot, 0, 0, 1, 100, 1, 1)
    assert ring.counts()['pending'] == 0
    with ring.write() as slot:
        pack_order(slot, 1, 0, 1, 100, 1, 1)
    with pytest.raises(RuntimeError):
        with ring.read() as slot:
            raise RuntimeError('consumer rejected the record')
    with ring.read() as slot:
        assert ORDER.unpack_from(slot)[0] == 1
    assert ring.counts()['pending'] == 0


def test_existing_file_is_never_overwritten(tmp_path):
    path = tmp_path / 'existing'
    path.write_bytes(b'keep')
    with pytest.raises(FileExistsError):
        MappedRing(path, 2, ORDER.size, mp.get_context('spawn'))
    assert path.read_bytes() == b'keep'


@pytest.mark.parametrize('capacity', [1, 3, 64])
def test_spawned_process_delivery_and_queue_comparison(tmp_path, capacity):
    report = run_audit(301, capacity, tmp_path, compare_queue=capacity == 3)
    assert report['mmap']['orders_verified'] == 301
    assert report['mmap']['checksum'] == 301 * 302 // 2
    if capacity == 3:
        assert report['queue_baseline']['orders_verified'] == 301


@pytest.mark.parametrize('capacity,size', [(0, 40), (2, 0), (1048577, 40)])
def test_invalid_ring_configuration(tmp_path, capacity, size):
    with pytest.raises(ValueError):
        MappedRing(tmp_path / 'invalid', capacity, size, mp.get_context('spawn'))
