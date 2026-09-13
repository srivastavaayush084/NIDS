import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from backend.app.core.logging import logger
from backend.app.ml.data.utils.data_utils import ensure_dir, save_metadata, load_metadata
from backend.app.ml.sequence.sequence_validator import validate_sequence_data


class LSTMAutoencoderNetwork(nn.Module):
    """
    Configurable PyTorch LSTM Autoencoder for Sequential Network Traffic Anomaly Detection.
    Encodes temporal event windows (B, T, D) into a compressed latent bottleneck (B, Z)
    and reconstructs the sequence (B, T, D) to measure temporal reconstruction fidelity.
    """

    def __init__(
        self,
        input_dim: int,
        seq_len: int,
        encoder_units: int = 64,
        latent_dim: int = 16,
        decoder_units: int = 64,
        num_layers: int = 1,
        dropout_rate: float = 0.1,
    ):
        super().__init__()
        self.input_dim = input_dim
        self.seq_len = seq_len
        self.encoder_units = encoder_units
        self.latent_dim = latent_dim
        self.decoder_units = decoder_units
        self.num_layers = num_layers
        self.dropout_rate = dropout_rate

        # 1. Encoder LSTM
        lstm_dropout = dropout_rate if num_layers > 1 else 0.0
        self.encoder_lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=encoder_units,
            num_layers=num_layers,
            batch_first=True,
            dropout=lstm_dropout,
        )
        self.encoder_dropout = nn.Dropout(dropout_rate) if dropout_rate > 0.0 else nn.Identity()
        self.encoder_linear = nn.Linear(encoder_units, latent_dim)

        # 2. Decoder LSTM
        self.decoder_lstm = nn.LSTM(
            input_size=latent_dim,
            hidden_size=decoder_units,
            num_layers=num_layers,
            batch_first=True,
            dropout=lstm_dropout,
        )
        self.decoder_dropout = nn.Dropout(dropout_rate) if dropout_rate > 0.0 else nn.Identity()
        # TimeDistributed Linear layer
        self.output_dense = nn.Linear(decoder_units, input_dim)

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        """
        Compress sequential tensor (B, T, D) into latent bottleneck vector (B, Z).
        Takes the final hidden state or final sequence step output.
        """
        out, (hn, cn) = self.encoder_lstm(x)
        # Use final timestep output
        final_step = out[:, -1, :]
        final_step = self.encoder_dropout(final_step)
        latent = self.encoder_linear(final_step)
        return latent

    def decode(self, z: torch.Tensor) -> torch.Tensor:
        """
        Reconstruct sequence (B, T, D) by repeating latent code across seq_len timesteps
        and passing through Decoder LSTM and TimeDistributed output layer.
        """
        # Repeat latent code across all time steps: (B, T, Z)
        z_repeated = z.unsqueeze(1).repeat(1, self.seq_len, 1)
        out, _ = self.decoder_lstm(z_repeated)
        out = self.decoder_dropout(out)
        # Apply output dense projection to every timestep: (B, T, D)
        reconstruction = self.output_dense(out)
        return reconstruction

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Full forward sequential reconstruction pass."""
        z = self.encode(x)
        return self.decode(z)


class LSTMAutoencoderDetector:
    """
    Production Deep Learning LSTM Autoencoder Anomaly Detector for sequential flow analysis.
    Learns normal temporal transitions across sliding event windows.
    Computes per-sequence Mean Squared Error (MSE) and transforms it into
    a normalized application anomaly score (0.0 to 100.0).
    """

    def __init__(
        self,
        input_dim: Optional[int] = None,
        seq_len: int = 10,
        sequence_length: Optional[int] = None,
        encoder_units: int = 64,
        latent_dim: int = 16,
        decoder_units: int = 64,
        num_layers: int = 1,
        dropout_rate: float = 0.1,
        dropout: Optional[float] = None,
        learning_rate: float = 0.001,
        batch_size: int = 32,
        epochs: int = 40,
        early_stopping_patience: int = 8,
        random_seed: int = 42,
        device: Optional[str] = None,
        threshold_percentile: float = 95.0,
        anomaly_threshold: Optional[float] = None,
    ):
        self.input_dim = input_dim
        self.seq_len = sequence_length or seq_len
        self.encoder_units = encoder_units
        self.latent_dim = latent_dim
        self.decoder_units = decoder_units
        self.num_layers = num_layers
        self.dropout_rate = dropout if dropout is not None else dropout_rate
        self.learning_rate = learning_rate
        self.batch_size = batch_size
        self.epochs = epochs
        self.early_stopping_patience = early_stopping_patience
        self.random_seed = random_seed
        self.threshold_percentile = threshold_percentile

        if device is None or str(device).lower() == "auto":
            dev_str = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            dev_str = str(device)
        self.device = torch.device(dev_str)

        self.network: Optional[LSTMAutoencoderNetwork] = None
        self.is_trained: bool = False
        self.feature_names_: List[str] = []
        self.reconstruction_threshold: float = anomaly_threshold if anomaly_threshold is not None else 0.5
        self.threshold_strategy: str = "percentile_normal_val"

        # Empirical calibration bounds on reconstruction MSE for 0-100 scaling
        self.mse_min_: float = 0.0
        self.mse_max_: float = 1.0

        # Training history
        self.history_: Dict[str, List[float]] = {"train_loss": [], "val_loss": []}

    @property
    def feature_count_(self) -> int:
        """Return total number of input features per timestep."""
        return len(self.feature_names_) if self.feature_names_ else (self.input_dim or 0)

    @property
    def sequence_length(self) -> int:
        """Alias for seq_len."""
        return self.seq_len

    @property
    def optimal_threshold_(self) -> float:
        """Return calibrated decision threshold in raw sequence MSE."""
        return self.reconstruction_threshold

    @property
    def optimal_score_threshold_(self) -> float:
        """Return calibrated decision threshold transformed to 0-100 score."""
        denom = max(1e-7, self.mse_max_ - self.mse_min_)
        score = 100.0 * (self.reconstruction_threshold - self.mse_min_) / denom
        return float(np.clip(score, 0.0, 100.0))

    @property
    def anomaly_threshold(self) -> float:
        """Alias for reconstruction threshold."""
        return self.reconstruction_threshold

    @property
    def training_history_(self) -> Dict[str, List[float]]:
        """Alias for history dictionary."""
        return self.history_

    def _set_seeds(self) -> None:
        """Set deterministic seeds across PyTorch and NumPy."""
        torch.manual_seed(self.random_seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(self.random_seed)
        np.random.seed(self.random_seed)

    def _build_network(self, input_dim: int, seq_len: int) -> None:
        """Instantiate the PyTorch LSTM autoencoder network."""
        self._set_seeds()
        self.input_dim = input_dim
        self.seq_len = seq_len
        self.network = LSTMAutoencoderNetwork(
            input_dim=input_dim,
            seq_len=seq_len,
            encoder_units=self.encoder_units,
            latent_dim=self.latent_dim,
            decoder_units=self.decoder_units,
            num_layers=self.num_layers,
            dropout_rate=self.dropout_rate,
        ).to(self.device)

    def train(
        self,
        X_seq_train: np.ndarray,
        X_seq_val: Optional[np.ndarray] = None,
        feature_names: Optional[List[str]] = None,
    ) -> "LSTMAutoencoderDetector":
        """
        Train LSTM Autoencoder on normal baseline network sequences.
        Uses Adam optimizer with MSE loss and validation early stopping.
        """
        if feature_names:
            self.feature_names_ = list(feature_names)

        input_dim = X_seq_train.shape[2] if X_seq_train.ndim == 3 else (self.input_dim or 10)
        seq_len = X_seq_train.shape[1] if X_seq_train.ndim == 3 else self.seq_len

        # Validate training sequence data
        X_train_arr = validate_sequence_data(
            X_seq_train,
            expected_seq_len=seq_len,
            expected_feat_dim=input_dim,
        )

        self._build_network(input_dim=input_dim, seq_len=seq_len)
        logger.info(
            f"Training LSTM Autoencoder on device={self.device}: sequences={X_train_arr.shape[0]}, "
            f"seq_len={seq_len}, input_dim={input_dim}, latent_dim={self.latent_dim}, "
            f"encoder_units={self.encoder_units}, decoder_units={self.decoder_units}, "
            f"lr={self.learning_rate}, max_epochs={self.epochs}, batch_size={self.batch_size}"
        )

        train_tensor = torch.from_numpy(X_train_arr).float()
        train_dataset = TensorDataset(train_tensor, train_tensor)
        train_loader = DataLoader(
            train_dataset,
            batch_size=min(self.batch_size, len(train_dataset)),
            shuffle=True,
        )

        val_tensor: Optional[torch.Tensor] = None
        if X_seq_val is not None and len(X_seq_val) > 0:
            X_val_arr = validate_sequence_data(
                X_seq_val,
                expected_seq_len=seq_len,
                expected_feat_dim=input_dim,
            )
            val_tensor = torch.from_numpy(X_val_arr).float().to(self.device)

        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(self.network.parameters(), lr=self.learning_rate)

        best_val_loss = float("inf")
        patience_counter = 0
        best_state = None
        self.history_ = {"train_loss": [], "val_loss": []}

        self.network.train()
        for epoch in range(1, self.epochs + 1):
            epoch_train_losses = []
            for batch_x, _ in train_loader:
                batch_x = batch_x.to(self.device)
                optimizer.zero_grad()
                reconstructed = self.network(batch_x)
                loss = criterion(reconstructed, batch_x)
                loss.backward()
                optimizer.step()
                epoch_train_losses.append(loss.item())

            avg_train_loss = float(np.mean(epoch_train_losses))
            self.history_["train_loss"].append(avg_train_loss)

            # Validation step
            avg_val_loss = avg_train_loss
            if val_tensor is not None:
                self.network.eval()
                with torch.no_grad():
                    val_recon = self.network(val_tensor)
                    avg_val_loss = float(criterion(val_recon, val_tensor).item())
                self.network.train()
                self.history_["val_loss"].append(avg_val_loss)

                # Early stopping check
                if avg_val_loss < best_val_loss:
                    best_val_loss = avg_val_loss
                    best_state = {k: v.cpu().clone() for k, v in self.network.state_dict().items()}
                    patience_counter = 0
                else:
                    patience_counter += 1
                    if patience_counter >= self.early_stopping_patience:
                        logger.info(f"Early stopping triggered at epoch {epoch}/{self.epochs}")
                        break

            if epoch % 10 == 0 or epoch == 1:
                logger.debug(f"Epoch {epoch:03d}/{self.epochs:03d} - Train Loss: {avg_train_loss:.6f} - Val Loss: {avg_val_loss:.6f}")

        # Restore best model weights
        if best_state is not None:
            self.network.load_state_dict({k: v.to(self.device) for k, v in best_state.items()})

        self.is_trained = True
        self.network.eval()

        # Calibration on training baseline sequences
        train_errors = self.compute_reconstruction_error(X_train_arr)
        self.mse_min_ = float(np.percentile(train_errors, 1))
        self.mse_max_ = float(np.percentile(train_errors, 99)) + 0.1

        logger.info(
            f"LSTM Autoencoder training complete. Baseline train error MSE: min={self.mse_min_:.6f}, max={self.mse_max_:.6f}"
        )
        return self

    def compute_reconstruction_error(self, X_seq: Union[np.ndarray, Any]) -> np.ndarray:
        """
        Compute per-sequence Mean Squared Error (MSE):
            MSE(S, S_hat) = 1/(T * D) * sum_{t=1}^T sum_{j=1}^D (S_{t, j} - S_hat_{t, j})^2
        """
        if not self.is_trained or self.network is None:
            raise RuntimeError("Model is not trained.")

        X_arr = validate_sequence_data(
            X_seq,
            expected_seq_len=self.seq_len,
            expected_feat_dim=self.input_dim or X_seq.shape[2],
            allow_single_sequence=True,
        )

        self.network.eval()
        with torch.no_grad():
            x_tensor = torch.from_numpy(X_arr).float().to(self.device)
            x_recon = self.network(x_tensor)
            diff = (x_tensor - x_recon).cpu().numpy()
            # Mean across time steps (axis 1) and feature dimensions (axis 2)
            seq_mse = np.mean(diff ** 2, axis=(1, 2))

        return seq_mse.astype(np.float32)

    def compute_timestep_errors(self, X_seq: Union[np.ndarray, Any]) -> np.ndarray:
        """
        Compute per-timestep Mean Squared Error:
            MSE_t = 1/D * sum_{j=1}^D (S_{t, j} - S_hat_{t, j})^2  -> shape (N_sequences, seq_len)
        """
        if not self.is_trained or self.network is None:
            raise RuntimeError("Model is not trained.")

        X_arr = validate_sequence_data(
            X_seq,
            expected_seq_len=self.seq_len,
            expected_feat_dim=self.input_dim or X_seq.shape[2],
            allow_single_sequence=True,
        )

        self.network.eval()
        with torch.no_grad():
            x_tensor = torch.from_numpy(X_arr).float().to(self.device)
            x_recon = self.network(x_tensor)
            diff = (x_tensor - x_recon).cpu().numpy()
            # Mean across feature dimensions (axis 2)
            timestep_mse = np.mean(diff ** 2, axis=2)

        return timestep_mse.astype(np.float32)

    def calibrate_threshold_and_bounds(
        self,
        X_val_normal_seq: np.ndarray,
        X_val_attack_seq: Optional[np.ndarray] = None,
        strategy: str = "percentile",
        percentile: float = 95.0,
    ) -> float:
        """
        Calibrate sequence reconstruction error decision threshold and 0-100 normalization bounds
        strictly on validation sequence data.
        """
        val_norm_errors = self.compute_reconstruction_error(X_val_normal_seq)
        self.threshold_strategy = f"percentile_{percentile:.1f}_normal_val"

        if strategy == "percentile":
            self.reconstruction_threshold = float(np.percentile(val_norm_errors, percentile))
        else:
            self.reconstruction_threshold = float(np.mean(val_norm_errors) + 2.0 * np.std(val_norm_errors))

        # Calibrate score bounds
        self.mse_min_ = float(np.percentile(val_norm_errors, 1))
        if X_val_attack_seq is not None and len(X_val_attack_seq) > 0:
            val_att_errors = self.compute_reconstruction_error(X_val_attack_seq)
            self.mse_max_ = float(np.percentile(val_att_errors, 90))
        else:
            self.mse_max_ = float(np.percentile(val_norm_errors, 99)) * 2.5 + 0.05

        if self.mse_max_ <= self.mse_min_:
            self.mse_max_ = self.mse_min_ + 1.0

        logger.info(
            f"LSTM Autoencoder Calibrated: Threshold={self.reconstruction_threshold:.6f} "
            f"(Strategy: {self.threshold_strategy}), Bounds=[{self.mse_min_:.6f}, {self.mse_max_:.6f}]"
        )
        return self.reconstruction_threshold

    def compute_anomaly_scores(self, X_seq: Union[np.ndarray, Any]) -> np.ndarray:
        """
        Transform raw sequence reconstruction errors (MSE) into normalized application anomaly scores (0.0 to 100.0).
        """
        raw_errors = self.compute_reconstruction_error(X_seq)
        denom = max(1e-7, self.mse_max_ - self.mse_min_)
        normalized = 100.0 * (raw_errors - self.mse_min_) / denom
        normalized = np.clip(normalized, 0.0, 100.0)
        return np.round(normalized, 2)

    def predict_binary(self, X_seq: Union[np.ndarray, Any], threshold: Optional[float] = None) -> np.ndarray:
        """Predict binary indicator: 0 = Normal, 1 = Anomaly based on sequence reconstruction threshold."""
        thresh = threshold if threshold is not None else self.reconstruction_threshold
        raw_errors = self.compute_reconstruction_error(X_seq)
        return (raw_errors >= thresh).astype(int)

    def determine_threshold(
        self,
        X_val_seq: np.ndarray,
        strategy: str = "percentile",
        percentile: float = 95.0,
    ) -> float:
        """Convenience method to determine and set threshold on validation sequences."""
        return self.calibrate_threshold_and_bounds(X_val_seq, strategy=strategy, percentile=percentile)

    def get_params(self) -> Dict[str, Any]:
        """Return model hyperparameter dictionary."""
        return {
            "input_dim": self.input_dim,
            "seq_len": self.seq_len,
            "encoder_units": self.encoder_units,
            "latent_dim": self.latent_dim,
            "decoder_units": self.decoder_units,
            "num_layers": self.num_layers,
            "dropout_rate": self.dropout_rate,
            "learning_rate": self.learning_rate,
            "batch_size": self.batch_size,
            "epochs": self.epochs,
            "early_stopping_patience": self.early_stopping_patience,
            "random_seed": self.random_seed,
            "threshold_percentile": self.threshold_percentile,
            "reconstruction_threshold": self.reconstruction_threshold,
            "threshold_strategy": self.threshold_strategy,
            "mse_min": self.mse_min_,
            "mse_max": self.mse_max_,
            "feature_count": len(self.feature_names_),
        }

    def save(self, file_path: Union[str, Path]) -> Path:
        """Serialize model weights and architecture configuration to disk."""
        if not self.is_trained or self.network is None:
            raise RuntimeError("Cannot save an unfitted LSTMAutoencoderDetector.")

        path = Path(file_path)
        ensure_dir(path.parent)

        payload = {
            "model_type": "lstm_autoencoder",
            "state_dict": self.network.state_dict(),
            "params": self.get_params(),
            "feature_names": self.feature_names_,
            "reconstruction_threshold": self.reconstruction_threshold,
            "threshold_strategy": self.threshold_strategy,
            "mse_min": self.mse_min_,
            "mse_max": self.mse_max_,
            "history": self.history_,
        }

        torch.save(payload, str(path))
        logger.info(f"Saved LSTM Autoencoder weights and configuration to: {path}")
        return path

    @classmethod
    def load(cls, file_path: Union[str, Path], device: Optional[str] = None) -> "LSTMAutoencoderDetector":
        """Load trained LSTM Autoencoder checkpoint and restore inference state."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"LSTM Autoencoder artifact not found at {path}")

        payload = torch.load(str(path), map_location="cpu", weights_only=False)
        params = payload["params"]

        detector = cls(
            input_dim=params["input_dim"],
            seq_len=params["seq_len"],
            encoder_units=params["encoder_units"],
            latent_dim=params["latent_dim"],
            decoder_units=params["decoder_units"],
            num_layers=params["num_layers"],
            dropout_rate=params["dropout_rate"],
            learning_rate=params["learning_rate"],
            batch_size=params["batch_size"],
            epochs=params["epochs"],
            early_stopping_patience=params["early_stopping_patience"],
            random_seed=params["random_seed"],
            threshold_percentile=params["threshold_percentile"],
            anomaly_threshold=payload["reconstruction_threshold"],
            device=device,
        )

        detector._build_network(input_dim=params["input_dim"], seq_len=params["seq_len"])
        detector.network.load_state_dict(payload["state_dict"])
        detector.network.to(detector.device)
        detector.network.eval()

        detector.is_trained = True
        detector.feature_names_ = payload.get("feature_names", [])
        detector.reconstruction_threshold = payload.get("reconstruction_threshold", 0.5)
        detector.threshold_strategy = payload.get("threshold_strategy", "percentile_normal_val")
        detector.mse_min_ = payload.get("mse_min", 0.0)
        detector.mse_max_ = payload.get("mse_max", 1.0)
        detector.history_ = payload.get("history", {"train_loss": [], "val_loss": []})

        logger.info(
            f"Loaded LSTMAutoencoderDetector from {path} (input_dim={detector.input_dim}, "
            f"seq_len={detector.seq_len}, latent_dim={detector.latent_dim}, threshold={detector.reconstruction_threshold:.6f})"
        )
        return detector
