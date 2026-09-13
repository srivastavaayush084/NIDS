from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
from backend.app.core.logging import logger


@dataclass
class SequenceWindow:
    """Metadata container for a single sliding sequence window."""
    sequence_index: int
    start_row_idx: int
    end_row_idx: int  # exclusive
    length: int
    label_binary: Optional[int] = None
    label_category: Optional[str] = None


class SequenceBuilder:
    """
    Transforms 2D preprocessed tabular network records into 3D sequential sliding windows
    for temporal deep learning models (e.g. LSTM Autoencoder).

    Strictly preserves row/event ordering without cross-split leakage.
    """

    def __init__(
        self,
        sequence_length: int = 10,
        stride: int = 1,
        label_aggregation: str = "any",
    ):
        """
        Args:
            sequence_length: Number of consecutive time steps per sequence window (T).
            stride: Step size between consecutive sliding windows (default: 1).
            label_aggregation: Rule for aggregating record-level labels to sequence level:
                               - 'any': 1 if any record in window is attack (default)
                               - 'last': Label of the final record in the window
                               - 'majority': 1 if >50% of records in window are attacks
        """
        if sequence_length < 1:
            raise ValueError(f"sequence_length must be >= 1, got {sequence_length}")
        if stride < 1:
            raise ValueError(f"stride must be >= 1, got {stride}")
        if label_aggregation not in ("any", "last", "majority"):
            raise ValueError(f"Unknown label_aggregation: '{label_aggregation}'. Must be 'any', 'last', or 'majority'.")

        self.sequence_length = sequence_length
        self.stride = stride
        self.label_aggregation = label_aggregation

    def build_sequences(
        self,
        X: Union[np.ndarray, pd.DataFrame],
        y_binary: Optional[Union[np.ndarray, pd.Series]] = None,
        y_category: Optional[Union[np.ndarray, pd.Series]] = None,
        raise_if_insufficient: bool = False,
    ) -> Tuple[np.ndarray, Optional[np.ndarray], Optional[np.ndarray], List[SequenceWindow]]:
        """
        Generate 3D sliding sequence windows from 2D tabular features.

        Args:
            X: 2D feature matrix of shape (N_records, N_features).
            y_binary: Optional binary record labels (0 = Normal, 1 = Attack).
            y_category: Optional multi-class attack category labels.
            raise_if_insufficient: If True, raises ValueError when records < sequence_length;
                                  otherwise returns empty 3D array.

        Returns:
            Tuple of:
            - X_seq: 3D numpy array of shape (N_sequences, sequence_length, N_features)
            - y_seq_binary: 1D numpy array of shape (N_sequences,) or None
            - y_seq_category: 1D numpy array of shape (N_sequences,) or None
            - window_metadata: List of SequenceWindow metadata descriptors
        """
        if isinstance(X, pd.DataFrame):
            X_arr = X.to_numpy(dtype=np.float32)
        elif isinstance(X, np.ndarray):
            X_arr = X.astype(np.float32)
        else:
            raise TypeError(f"Expected pd.DataFrame or np.ndarray, got {type(X)}")

        if X_arr.ndim != 2:
            raise ValueError(f"Expected 2D feature matrix (N_records, N_features), got shape {X_arr.shape}")

        n_records, n_features = X_arr.shape

        # Handle insufficient records
        if n_records < self.sequence_length:
            msg = (
                f"Insufficient records ({n_records}) to construct sequence of length {self.sequence_length}."
            )
            if raise_if_insufficient:
                raise ValueError(msg)
            logger.warning(msg + " Returning empty sequence tensor.")
            empty_seq = np.empty((0, self.sequence_length, n_features), dtype=np.float32)
            return empty_seq, None, None, []

        # Convert label inputs to numpy if provided
        y_bin_arr = None
        if y_binary is not None:
            if isinstance(y_binary, pd.Series):
                y_bin_arr = y_binary.to_numpy(dtype=int)
            else:
                y_bin_arr = np.asarray(y_binary, dtype=int)
            if len(y_bin_arr) != n_records:
                raise ValueError(f"y_binary length ({len(y_bin_arr)}) does not match X rows ({n_records})")

        y_cat_arr = None
        if y_category is not None:
            if isinstance(y_category, pd.Series):
                y_cat_arr = y_category.astype(str).to_numpy()
            else:
                y_cat_arr = np.asarray(y_category, dtype=str)
            if len(y_cat_arr) != n_records:
                raise ValueError(f"y_category length ({len(y_cat_arr)}) does not match X rows ({n_records})")

        # Sliding window construction
        seq_list = []
        seq_bin_labels = [] if y_bin_arr is not None else None
        seq_cat_labels = [] if y_cat_arr is not None else None
        windows: List[SequenceWindow] = []

        seq_idx = 0
        for start_idx in range(0, n_records - self.sequence_length + 1, self.stride):
            end_idx = start_idx + self.sequence_length
            window_slice = X_arr[start_idx:end_idx, :]
            seq_list.append(window_slice)

            # Aggregate binary label
            bin_label = None
            if y_bin_arr is not None:
                sub_bin = y_bin_arr[start_idx:end_idx]
                if self.label_aggregation == "any":
                    bin_label = int(np.any(sub_bin == 1))
                elif self.label_aggregation == "last":
                    bin_label = int(sub_bin[-1])
                elif self.label_aggregation == "majority":
                    bin_label = int(np.mean(sub_bin == 1) >= 0.5)
                seq_bin_labels.append(bin_label)

            # Aggregate category label
            cat_label = None
            if y_cat_arr is not None:
                sub_cat = y_cat_arr[start_idx:end_idx]
                # If binary indicates attack (or any attack in sub_cat), pick non-normal category
                attack_cats = [c for c in sub_cat if c.lower() != "normal"]
                if attack_cats:
                    # Pick most frequent attack category in window
                    vals, counts = np.unique(attack_cats, return_counts=True)
                    cat_label = str(vals[np.argmax(counts)])
                else:
                    cat_label = "normal"
                seq_cat_labels.append(cat_label)

            windows.append(
                SequenceWindow(
                    sequence_index=seq_idx,
                    start_row_idx=start_idx,
                    end_row_idx=end_idx,
                    length=self.sequence_length,
                    label_binary=bin_label,
                    label_category=cat_label,
                )
            )
            seq_idx += 1

        X_seq = np.stack(seq_list, axis=0).astype(np.float32)
        y_seq_bin = np.array(seq_bin_labels, dtype=int) if seq_bin_labels is not None else None
        y_seq_cat = np.array(seq_cat_labels, dtype=object) if seq_cat_labels is not None else None

        logger.debug(
            f"Built {len(X_seq)} sequences (seq_len={self.sequence_length}, stride={self.stride}, features={n_features}) "
            f"from {n_records} tabular records."
        )
        return X_seq, y_seq_bin, y_seq_cat, windows
