import pytest

from edd_harness.adapter import Capture, invoke_adapter
from edd_harness.errors import EddContractError


def test_serializable_output_is_captured_verbatim():
    cap = invoke_adapter(lambda i: {"votes": ["GREEN"], "n": i}, 3)
    assert isinstance(cap, Capture)
    assert cap.output == {"votes": ["GREEN"], "n": 3}
    assert cap.duration_s >= 0.0


def test_non_serializable_output_raises_contract_error():
    class Rich:
        pass

    with pytest.raises(EddContractError):
        invoke_adapter(lambda i: {"obj": Rich()}, None)


def test_non_mapping_output_raises_contract_error():
    with pytest.raises(EddContractError):
        invoke_adapter(lambda i: [1, 2, 3], None)


def test_adapter_exception_propagates():
    def boom(i):
        raise RuntimeError("adapter failed")

    with pytest.raises(RuntimeError):
        invoke_adapter(boom, None)
