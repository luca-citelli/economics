from copy import deepcopy

import pytest
from pydantic import ValidationError

from economic_sim.config import Catalog, Config, load_config
from economic_sim.money import money, weekly_rate


@pytest.mark.parametrize(
    "path,value,match",
    [
        (("simulation", "initial_population"), 0, "initial_population"),
        (("simulation", "seed"), True, "seed"),
        (("simulation", "initial_banks"), 1, "initial_banks"),
        (("simulation", "weeks_per_year"), 53, "weeks_per_year"),
        (("simulation", "government_count"), 2, "government_count"),
        (("simulation", "country_count"), True, "country_count"),
        (("simulation", "currency"), "EUR", "currency"),
        (("features", "demographics"), True, "demographics"),
        (("features", "demographics"), 0, "demographics"),
        (("central_bank", "reserve_rate"), 0.08, "reserve_rate <="),
        (("central_bank", "emergency_rate"), -1.0, "greater than -1"),
        (("central_bank", "policy_rate"), float("nan"), "finite"),
        (("people", "initial_deposit"), 1000.0, "mai float"),
        (("people", "reservation_wage"), "0.0000001", "greater than 0"),
        (("people", "propensity_max"), -0.1, "propensity_max"),
        (("government", "bond_annual_rate"), 0.04, "Extra inputs"),
        (("government", "spending_weights"), {"food": 0.2}, "sommare a 1"),
        (("simulation", "initial_population"), 10, "Forza lavoro"),
        (("execution", "phases"), {"labor_wages": True}, "disattivate"),
    ],
)
def test_invalid_configuration(config, path, value, match):
    data = config.model_dump()
    data[path[0]][path[1]] = value
    with pytest.raises(ValidationError, match=match):
        Config.model_validate(data)


def test_catalog_rejects_missing_duplicate_and_broken_supply_chain(config):
    data = config.catalog.model_dump()
    for products in (data["products"][:-1], [*data["products"][:-1], data["products"][0]]):
        with pytest.raises(ValidationError, match="11 prodotti"):
            Catalog(schema_version=1, products=products)
    data = deepcopy(data)
    data["products"][8]["initial_inputs"]["wholesale_energy"] = 0.0
    with pytest.raises(ValidationError, match="Scorte di input"):
        Catalog.model_validate(data)
    data = config.catalog.model_dump()
    del data["products"][6]["recipe"]["metals"]
    del data["products"][6]["initial_inputs"]["metals"]
    with pytest.raises(ValidationError, match="lusso deve usare metalli"):
        Catalog.model_validate(data)


def test_yaml_duplicate_fields_rejected(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text("schema_version: 1\nschema_version: 1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicata"):
        load_config(path)


def test_money_and_rates():
    assert money("0.0000015") == money("0.000002")
    assert money("0.0000025") == money("0.000002")
    for invalid in (0.1, True, "NaN", "Infinity"):
        with pytest.raises(ValueError):
            money(invalid)
    for annual in (0.0, 0.05, -0.02):
        assert (1 + weekly_rate(annual)) ** 52 == pytest.approx(1 + annual)
    with pytest.raises(ValueError):
        weekly_rate(-1.0)
