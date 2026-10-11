from __future__ import annotations

import json

import pytest

from xionghan_chess.core.game import Game
from xionghan_chess.core.model import Move, Position
from xionghan_chess.training.encoding import ACTION_SIZE, FEATURE_SIZE, action_index, encode_state
from xionghan_chess.training.selfplay import append_jsonl, collect_game


def test_training_encoding_and_action_ids_are_stable():
    game = Game("traditional")
    encoded = encode_state(game.state)
    assert len(encoded) == FEATURE_SIZE
    assert set(encoded) <= {-1.0, 0.0, 1.0}
    index = action_index(Move(Position(0, 0), Position(12, 12)))
    assert 0 <= index < ACTION_SIZE
    assert index == 168


def test_selfplay_writes_versioned_local_jsonl(tmp_path):
    samples = collect_game(simulations=1, max_plies=2, seed=4)
    assert len(samples) == 2
    assert all(item["schema"] == 1 for item in samples)
    target = tmp_path / "samples.jsonl"
    assert append_jsonl(target, samples) == 2
    loaded = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines()]
    assert loaded == samples


def test_numpy_policy_value_training_smoke(tmp_path):
    pytest.importorskip("numpy")
    from xionghan_chess.training.network import NumpyPolicyValueNet

    samples = collect_game(simulations=1, max_plies=1, seed=8)
    dataset = tmp_path / "samples.jsonl"
    append_jsonl(dataset, samples)
    network = NumpyPolicyValueNet(hidden=4, seed=2)
    metrics = network.train_jsonl(dataset, epochs=1)
    model = tmp_path / "model.npz"
    network.save(model)
    assert metrics["samples"] == 1
    assert metrics["loss"] > 0
    assert model.exists()
