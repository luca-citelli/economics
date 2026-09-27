import copy

import numpy as np

# Mappa versionata; aggiunte future non spostano gli stream esistenti.
STREAMS = {
    "people": 1,
    "endowments": 2,
    "ownership": 3,
    "labor": 10,
    "credit": 11,
    "goods": 12,
    "resources": 13,
    "bonds": 14,
    "equity": 15,
}


class RandomStreams:
    def __init__(self, seed: int):
        self._streams = {
            name: np.random.Generator(np.random.PCG64(np.random.SeedSequence([seed, number])))
            for name, number in STREAMS.items()
        }

    def __getitem__(self, name: str):
        return self._streams[name]

    def states(self):
        return {
            name: copy.deepcopy(rng.bit_generator.state)
            for name, rng in sorted(self._streams.items())
        }

    def restore(self, states):
        if set(states) != set(STREAMS):
            raise ValueError("Stream RNG incompatibili")
        staged = {}
        for name, state in states.items():
            rng = np.random.Generator(np.random.PCG64())
            rng.bit_generator.state = copy.deepcopy(state)
            staged[name] = rng
        self._streams = staged


def truncated_nonnegative_normal(rng, mean, std, count):
    if std == 0:
        return np.full(count, mean, dtype=np.float64)
    values = rng.normal(mean, std, count)
    # Vera normale troncata: rejection sampling, non clipping con massa a zero.
    while (negative := values < 0).any():
        values[negative] = rng.normal(mean, std, int(negative.sum()))
    return values
