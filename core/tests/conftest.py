import numpy as np
import pytest

import mechy_core as mc


@pytest.fixture
def arm():
    return mc.default_arm()


@pytest.fixture
def motors():
    return mc.default_motors()


@pytest.fixture
def rng():
    return np.random.default_rng(0)
