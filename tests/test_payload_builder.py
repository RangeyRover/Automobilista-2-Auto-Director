import pytest
from dashboard.payload_builder import PayloadBuilder

def test_payload_builder_initialisation():
    """T052: Verify PayloadBuilder can be imported and initialized."""
    class MockBridge:
        pass
    builder = PayloadBuilder(MockBridge())
    assert hasattr(builder, 'parse_packets')
