from pathlib import Path

import pytest

from economic_sim import Simulation
from economic_sim.config import load_config

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def config():
    return load_config(ROOT / "configs/base.yaml")


@pytest.fixture
def sim(config):
    return Simulation.from_config(config)
