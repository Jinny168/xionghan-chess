"""Local self-play and optional NumPy policy/value training pipeline."""

from .encoding import ACTION_SIZE, FEATURE_SIZE, action_index, encode_state

__all__ = ["ACTION_SIZE", "FEATURE_SIZE", "action_index", "encode_state"]
