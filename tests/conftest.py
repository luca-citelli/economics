from pathlib import Path

import pytest

from economic_sim import Simulation
from economic_sim.config import Config, load_config

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def config():
    return load_config(ROOT / "configs/base.yaml")


@pytest.fixture
def sim(config):
    return Simulation.from_config(config)


@pytest.fixture
def real_config():
    data = load_config(ROOT / "configs/t02.yaml").model_dump()
    data["simulation"].update(initial_population=100, companies_per_product=2)
    return Config.model_validate(data)


@pytest.fixture
def real_sim(real_config):
    return Simulation.from_config(real_config)
