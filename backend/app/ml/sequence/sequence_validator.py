from typing import Any, Tuple, Union
import numpy as np
import pandas as pd


def validate_sequence_data(
    X_seq: Union[np.ndarray, Any],
    expected_seq_len: int,
    expected_feat_dim: int,
    allow_single_sequence: bool = False,
) -> np.ndarray:
    """
    Validate 3D sequence array dimensions, numerical integrity, and absence of NaNs/Infs.

    Args:
        X_seq: Input sequence array of shape (N_samples, sequence_length, feature_dim)
               or (sequence_length, feature_dim) if allow_single_sequence=True.
        expected_seq_len: Expected number of timesteps per sequence window.
        expected_feat_dim: Expected number of feature dimensions per timestep.
        allow_single_sequence: Whether a single 2D sequence (T, D) is accepted and reshaped to (1, T, D).

    Returns:
        Validated 3D float32 numpy array of shape (N, T, D).

    Raises:
        TypeError: If input cannot be converted to a NumPy array.
        ValueError: If shape is invalid, contains NaNs/Infs, or dimensions do not match.
    """
    if not isinstance(X_seq, np.ndarray):
        try:
            X_seq = np.asarray(X_seq, dtype=np.float32)
        except Exception as e:
            raise TypeError(f"Could not convert input of type {type(X_seq)} to np.ndarray: {e}")

    arr = X_seq.astype(np.float32)

    # If 2D single sequence allowed, adapt length and feature dimensions if needed, then expand to (1, T, D)
    if arr.ndim == 2:
        if allow_single_sequence:
            # Adapt timesteps
            if arr.shape[0] > expected_seq_len:
                arr = arr[-expected_seq_len:]
            elif arr.shape[0] < expected_seq_len:
                pad_steps = expected_seq_len - arr.shape[0]
                arr = np.pad(arr, ((pad_steps, 0), (0, 0)), mode="constant", constant_values=0.0)

            # Adapt feature dimension
            if expected_feat_dim and arr.shape[1] < expected_feat_dim:
                pad_feats = expected_feat_dim - arr.shape[1]
                arr = np.pad(arr, ((0, 0), (0, pad_feats)), mode="constant", constant_values=0.0)
            elif expected_feat_dim and arr.shape[1] > expected_feat_dim:
                arr = arr[:, :expected_feat_dim]

            arr = np.expand_dims(arr, axis=0)
        else:
            raise ValueError(
                f"Expected 3D sequence tensor (N_samples, seq_len={expected_seq_len}, feat_dim={expected_feat_dim}), "
                f"got 2D array of shape {arr.shape}."
            )

    if arr.ndim != 3:
        raise ValueError(
            f"Expected 3D sequence tensor of shape (N, seq_len, feat_dim), got array with {arr.ndim} dimensions (shape={arr.shape})."
        )

    if arr.shape[0] == 0:
        raise ValueError("Sequence tensor is empty (0 sequences provided).")

    if arr.shape[1] != expected_seq_len:
        raise ValueError(
            f"Sequence length mismatch: Expected timesteps={expected_seq_len}, but got {arr.shape[1]}."
        )

    if arr.shape[2] != expected_feat_dim:
        raise ValueError(
            f"Feature dimension mismatch: Expected features={expected_feat_dim}, but got {arr.shape[2]}."
        )

    if np.isnan(arr).any() or np.isinf(arr).any():
        raise ValueError("Sequence tensor contains NaN or infinite values.")

    return np.ascontiguousarray(arr)
