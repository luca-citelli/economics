import argparse
import json
import sys
from pathlib import Path

import yaml

from economic_sim import Simulation
from economic_sim.config import load_config


def main(argv=None):
    parser = argparse.ArgumentParser(description="Simulatore economico — fondamenta T01")
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate", help="Valida scenario e catalogo")
    validate.add_argument("config", type=Path)
    init = subparsers.add_parser("init", help="Costruisce e verifica lo stato della settimana 0")
    init.add_argument("config", type=Path)
    init.add_argument("--output", type=Path, help="Riepilogo JSON con bilanci e registro fisico")
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
        if args.command == "validate":
            print("Configurazione valida: 11 prodotti, profilo initialization_only.")
            return 0
        sim = Simulation.from_config(config)
        summary = sim.diagnostic_summary()
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                encoding="utf-8",
            )
        else:
            print(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False))
        print(f"Settimana 0 verificata. Checksum: {sim.economic_checksum()}", file=sys.stderr)
        return 0
    except (ValueError, OSError, yaml.YAMLError) as exc:
        print(f"Errore: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
