"""Root conftest for the entire test suite."""

import pytest

pytestmark = pytest.mark.asyncio(auto=True)
