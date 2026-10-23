from __future__ import annotations

import json
from pathlib import Path

from ..core.model import GameState
from .encoding import ACTION_SIZE, FEATURE_SIZE, action_index, encode_state


class NumpyPolicyValueNet:
    """Small policy/value MLP for a reproducible CPU training baseline."""

    def __init__(self, hidden: int = 32, seed: int = 0):
        try:
            import numpy as np
        except ImportError as exc:  # pragma: no cover - exercised without train extra
            raise RuntimeError("Install the training extra: pip install -e .[train]") from exc
        self.np = np
        rng = np.random.default_rng(seed)
        scale = 0.02
        self.w1 = rng.normal(0, scale, (FEATURE_SIZE, hidden)).astype("float32")
        self.b1 = np.zeros(hidden, dtype="float32")
        self.wp = rng.normal(0, scale, (hidden, ACTION_SIZE)).astype("float32")
        self.bp = np.zeros(ACTION_SIZE, dtype="float32")
        self.wv = rng.normal(0, scale, (hidden, 1)).astype("float32")
        self.bv = np.zeros(1, dtype="float32")

    def train_jsonl(self, path: str | Path, epochs: int = 1, learning_rate: float = 1e-3,
                    limit: int | None = None) -> dict[str, float]:
        np = self.np
        rows = []
        with Path(path).open(encoding="utf-8") as stream:
            for line in stream:
                if line.strip():
                    rows.append(json.loads(line))
                if limit and len(rows) >= limit:
                    break
        if not rows:
            raise ValueError("training dataset is empty")
        x = np.asarray([encode_state(GameState.from_dict(row["state"])) for row in rows], dtype="float32")
        actions = np.asarray([row["action"] for row in rows], dtype="int64")
        targets = np.asarray([row["value"] for row in rows], dtype="float32")[:, None]
        policy_loss = value_loss = 0.0
        for _ in range(max(1, epochs)):
            hidden = np.tanh(x @ self.w1 + self.b1)
            logits = hidden @ self.wp + self.bp
            logits -= logits.max(axis=1, keepdims=True)
            probabilities = np.exp(logits)
            probabilities /= probabilities.sum(axis=1, keepdims=True)
            policy_loss = float(-np.log(probabilities[np.arange(len(rows)), actions] + 1e-9).mean())
            values = np.tanh(hidden @ self.wv + self.bv)
            value_loss = float(((values - targets) ** 2).mean())
            grad_logits = probabilities
            grad_logits[np.arange(len(rows)), actions] -= 1
            grad_logits /= len(rows)
            grad_values = 2 * (values - targets) * (1 - values * values) / len(rows)
            grad_hidden = grad_logits @ self.wp.T + grad_values @ self.wv.T
            grad_hidden *= 1 - hidden * hidden
            self.wp -= learning_rate * (hidden.T @ grad_logits)
            self.bp -= learning_rate * grad_logits.sum(axis=0)
            self.wv -= learning_rate * (hidden.T @ grad_values)
            self.bv -= learning_rate * grad_values.sum(axis=0)
            self.w1 -= learning_rate * (x.T @ grad_hidden)
            self.b1 -= learning_rate * grad_hidden.sum(axis=0)
        return {"samples": float(len(rows)), "policy_loss": policy_loss,
                "value_loss": value_loss, "loss": policy_loss + value_loss}

    def save(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        self.np.savez_compressed(target, schema=1, w1=self.w1, b1=self.b1,
                                 wp=self.wp, bp=self.bp, wv=self.wv, bv=self.bv)

    @classmethod
    def load(cls, path: str | Path) -> "NumpyPolicyValueNet":
        model = cls(hidden=1)
        data = model.np.load(Path(path))
        if int(data["schema"]) != 1:
            raise ValueError("unsupported policy/value schema")
        model.w1 = data["w1"].astype("float32")
        model.b1 = data["b1"].astype("float32")
        model.wp = data["wp"].astype("float32")
        model.bp = data["bp"].astype("float32")
        model.wv = data["wv"].astype("float32")
        model.bv = data["bv"].astype("float32")
        return model

    def evaluate_state(self, state: GameState) -> tuple[object, float]:
        np = self.np
        x = np.asarray([encode_state(state)], dtype="float32")
        hidden = np.tanh(x @ self.w1 + self.b1)
        logits = (hidden @ self.wp + self.bp)[0]
        value = float(np.tanh(hidden @ self.wv + self.bv)[0, 0])
        return logits, value

    def move_score(self, state: GameState, move) -> float:
        logits, _ = self.evaluate_state(state)
        return float(logits[action_index(move)])
