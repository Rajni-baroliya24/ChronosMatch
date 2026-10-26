import os
import pytest


@pytest.fixture
def native_book():
    try:
        from lowlatency._native import NativeBook
    except ImportError:
        if os.environ.get('CHRONOS_REQUIRE_NATIVE') == '1':
            pytest.fail('Native extension must be compiled for the low-latency CI job')
        pytest.skip('Build with python setup_lowlatency.py build_ext --inplace')
    return NativeBook
