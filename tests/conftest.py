import pytest

from azt.sandbox import build_world


@pytest.fixture
def w():
    return build_world()
