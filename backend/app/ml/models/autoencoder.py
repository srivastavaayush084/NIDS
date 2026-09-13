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


class DenseAutoencoderNetwork(nn.Module):
    """
    Configurable PyTorch Dense Autoencoder for Network Traffic Anomaly Detection.
    Symmetrically compresses high-dimensional network flow representations into a bottleneck
    latent space and reconstructs normal traffic patterns with low reconstruction error.
    """

    def __init__(
        self,
        input_dim: int,
        hidden_dims: Optional[List[int]] = None,
        latent_dim: int = 8,
        activation: str = "relu",
        dropout_rate: float = 0.0,
        dropout: Optional[float] = None,
        encoder_layers: Optional[List[int]] = None,
        decoder_layers: Optional[List[int]] = None,
    ):
        super().__init__()
        self.input_dim = input_dim
        self.latent_dim = latent_dim
        self.activation_name = activation.lower()
        self.dropout_rate = dropout if dropout is not None else dropout_rate

        if encoder_layers is not None:
            self.encoder_dims = encoder_layers
        elif hidden_dims is not None:
            self.encoder_dims = hidden_dims
        else:
            self.encoder_dims = [64, 32]

        if decoder_layers is not None:
            self.decoder_dims = decoder_layers
        elif hidden_dims is not None:
            self.decoder_dims = list(reversed(hidden_dims))
        else:
            self.decoder_dims = list(reversed(self.encoder_dims))

        act_cls = {
            "relu": nn.ReLU,
            "leaky_relu": nn.LeakyReLU,
            "elu": nn.ELU,
            "tanh": nn.Tanh,
            "gelu": nn.GELU,
        }.get(self.activation_name, nn.ReLU)

        # 1. Build Encoder
        enc_mods: List[nn.Module] = []
        in_features = input_dim
        for h_dim in self.encoder_dims:
            enc_mods.append(nn.Linear(in_features, h_dim))
            enc_mods.append(act_cls())
            if self.dropout_rate > 0.0:
                enc_mods.append(nn.Dropout(self.dropout_rate))
            in_features = h_dim
        enc_mods.append(nn.Linear(in_features, latent_dim))
        self.encoder = nn.Sequential(*enc_mods)

        # 2. Build Decoder
        dec_mods: List[nn.Module] = []
        in_features = latent_dim
        for h_dim in self.decoder_dims:
            dec_mods.append(nn.Linear(in_features, h_dim))
            dec_mods.append(act_cls())
            if self.dropout_rate > 0.0:
                dec_mods.append(nn.Dropout(self.dropout_rate))
            in_features = h_dim
        dec_mods.append(nn.Linear(in_features, input_dim))
        self.decoder = nn.Sequential(*dec_mods)

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        """Compress input tensor into bottleneck latent representation."""
        return self.encoder(x)

    def decode(self, z: torch.Tensor) -> torch.Tensor:
        """Reconstruct input tensor from latent code."""
        return self.decoder(z)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Full forward reconstruction pass."""
        z = self.encode(x)
        return self.decode(z)


class AutoencoderDetector:
    """
    Production Deep Learning Autoencoder Anomaly Detector.
    Learns topological reconstruction manifolds of normal network traffic.
    Computes per-sample Mean Squared Error (MSE) and transforms it into
    a normalized application-level anomaly score (0.0 to 100.0).
    """

    def __init__(
        self,
        input_dim: Optional[int] = None,
        hidden_dims: Optional[List[int]] = None,
        latent_dim: int = 8,
        activation: str = "relu",
        dropout_rate: float = 0.0,
        dropout: Optional[float] = None,
        encoder_layers: Optional[List[int]] = None,
        decoder_layers: Optional[List[int]] = None,
        learning_rate: float = 0.001,
        batch_size: int = 64,
        epochs: int = 50,
        early_stopping_patience: int = 10,
        random_seed: int = 42,
        device: Optional[str] = None,
        threshold_percentile: float = 95.0,
        anomaly_threshold: Optional[float] = None,
    ):
        self.input_dim = input_dim
        self.hidden_dims = hidden_dims if hidden_dims is not None else [64, 32]
        self.encoder_layers = encoder_layers
        self.decoder_layers = decoder_layers
        self.latent_dim = latent_dim
        self.activation = activation
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
        self.network: Optional[DenseAutoencoderNetwork] = None
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
        """Return total number of input features."""
        return len(self.feature_names_) if self.feature_names_ else (self.input_dim or 0)

    @property
    def optimal_threshold_(self) -> float:
        """Return calibrated decision threshold in raw MSE."""
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

    def determine_threshold(
        self,
        X_val: Union[np.ndarray, pd.DataFrame],
        strategy: str = "percentile",
        percentile: float = 95.0,
    ) -> float:
        """Convenience method to determine and set threshold on validation data."""
        return self.calibrate_threshold_and_bounds(X_val, strategy=strategy, percentile=percentile)

    def _set_seeds(self) -> None:
        """Set deterministic seeds across PyTorch and NumPy."""
        torch.manual_seed(self.random_seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(self.random_seed)
        np.random.seed(self.random_seed)

    def _build_network(self, input_dim: int) -> None:
        """Instantiate the PyTorch dense autoencoder network."""
        self._set_seeds()
        self.input_dim = input_dim
        self.network = DenseAutoencoderNetwork(
            input_dim=input_dim,
            hidden_dims=self.hidden_dims,
            latent_dim=self.latent_dim,
            activation=self.activation,
            dropout_rate=self.dropout_rate,
            encoder_layers=self.encoder_layers,
            decoder_layers=self.decoder_layers,
        ).to(self.device)

    def _ensure_numpy(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        """Convert input data to 2D contiguous float32 numpy array and validate."""
        if isinstance(X, pd.DataFrame):
            if not self.feature_names_ and not self.is_trained:
                self.feature_names_ = list(X.columns)
            arr = X.to_numpy(dtype=np.float32).copy()
        elif isinstance(X, np.ndarray):
            arr = X.astype(np.float32).copy()
        else:
            raise TypeError(f"Expected pd.DataFrame or np.ndarray, got {type(X)}")

        if arr.ndim == 1:
            arr = arr.reshape(1, -1)

        if np.isnan(arr).any() or np.isinf(arr).any():
            raise ValueError("Input array contains NaN or infinite values.")

        return np.ascontiguousarray(arr)

    def train(
        self,
        X_train: Union[np.ndarray, pd.DataFrame],
        X_val: Optional[Union[np.ndarray, pd.DataFrame]] = None,
        feature_names: Optional[List[str]] = None,
    ) -> "AutoencoderDetector":
        """
        Train Autoencoder on normal baseline network traffic.
        Uses Adam optimizer with MSE loss and validation early stopping.
        """
        X_train_arr = self._ensure_numpy(X_train)
        input_dim = X_train_arr.shape[1]

        if feature_names:
            self.feature_names_ = list(feature_names)
        elif isinstance(X_train, pd.DataFrame):
            self.feature_names_ = list(X_train.columns)

        self._build_network(input_dim)
        logger.info(
            f"Training Autoencoder on device={self.device}: samples={X_train_arr.shape[0]}, "
            f"input_dim={input_dim}, latent_dim={self.latent_dim}, hidden_dims={self.hidden_dims}, "
            f"lr={self.learning_rate}, max_epochs={self.epochs}, batch_size={self.batch_size}"
        )

        # Prepare PyTorch Datasets & Loaders
        train_tensor = torch.from_numpy(X_train_arr).float()
        train_dataset = TensorDataset(train_tensor, train_tensor)
        train_loader = DataLoader(
            train_dataset,
            batch_size=min(self.batch_size, len(train_dataset)),
            shuffle=True,
        )

        val_tensor: Optional[torch.Tensor] = None
        if X_val is not None and len(X_val) > 0:
            X_val_arr = self._ensure_numpy(X_val)
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

        # Restore best model weights if early stopping was tracked
        if best_state is not None:
            self.network.load_state_dict({k: v.to(self.device) for k, v in best_state.items()})

        self.is_trained = True
        self.network.eval()

        # Compute training reconstruction errors for initial calibration
        train_errors = self.compute_reconstruction_error(X_train_arr)
        self.mse_min_ = float(np.percentile(train_errors, 1))
        self.mse_max_ = float(np.percentile(train_errors, 99)) + 0.1

        logger.info(
            f"Autoencoder training complete. Baseline train error MSE: min={self.mse_min_:.6f}, max={self.mse_max_:.6f}"
        )
        return self

    def compute_reconstruction_error(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        """
        Compute per-sample Mean Squared Error (MSE) reconstruction loss:
            MSE(x, x_hat) = 1/D * sum((x_j - x_hat_j)^2)
        """
        if not self.is_trained or self.network is None:
            raise RuntimeError("Model is not trained.")

        X_arr = self._ensure_numpy(X)
        self.network.eval()

        with torch.no_grad():
            x_tensor = torch.from_numpy(X_arr).float().to(self.device)
            x_recon = self.network(x_tensor)
            # Compute elementwise squared difference and mean over feature dimension
            diff = (x_tensor - x_recon).cpu().numpy()
            sample_mse = np.mean(diff ** 2, axis=1)

        return sample_mse.astype(np.float32)

    def calibrate_threshold_and_bounds(
        self,
        X_val_normal: Union[np.ndarray, pd.DataFrame],
        X_val_attack: Optional[Union[np.ndarray, pd.DataFrame]] = None,
        strategy: str = "percentile",
        percentile: float = 95.0,
    ) -> float:
        """
        Calibrate reconstruction error decision threshold and 0-100 normalization bounds
        strictly on validation data.
        """
        val_norm_errors = self.compute_reconstruction_error(X_val_normal)
        self.threshold_strategy = f"percentile_{percentile:.1f}_normal_val"

        # Determine decision threshold
        if strategy == "percentile":
            self.reconstruction_threshold = float(np.percentile(val_norm_errors, percentile))
        else:
            # Fallback 3-sigma / mean + 2*std
            self.reconstruction_threshold = float(np.mean(val_norm_errors) + 2.0 * np.std(val_norm_errors))

        # Calibrate score scaling bounds
        self.mse_min_ = float(np.percentile(val_norm_errors, 1))
        if X_val_attack is not None and len(X_val_attack) > 0:
            val_att_errors = self.compute_reconstruction_error(X_val_attack)
            self.mse_max_ = float(np.percentile(val_att_errors, 90))
        else:
            self.mse_max_ = float(np.percentile(val_norm_errors, 99)) * 2.5 + 0.05

        if self.mse_max_ <= self.mse_min_:
            self.mse_max_ = self.mse_min_ + 1.0

        logger.info(
            f"Autoencoder Calibrated: Threshold={self.reconstruction_threshold:.6f} "
            f"(Strategy: {self.threshold_strategy}), Bounds=[{self.mse_min_:.6f}, {self.mse_max_:.6f}]"
        )
        return self.reconstruction_threshold

    def compute_anomaly_scores(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        """
        Transform raw reconstruction errors (MSE) into normalized application anomaly scores (0.0 to 100.0).
        Higher score = higher anomaly likelihood.
        """
        raw_errors = self.compute_reconstruction_error(X)
        denom = max(1e-7, self.mse_max_ - self.mse_min_)
        normalized = 100.0 * (raw_errors - self.mse_min_) / denom
        normalized = np.clip(normalized, 0.0, 100.0)
        return np.round(normalized, 2)

    def predict_binary(self, X: Union[np.ndarray, pd.DataFrame], threshold: Optional[float] = None) -> np.ndarray:
        """Predict binary indicator: 0 = Normal, 1 = Anomaly based on reconstruction threshold."""
        thresh = threshold if threshold is not None else self.reconstruction_threshold
        raw_errors = self.compute_reconstruction_error(X)
        return (raw_errors >= thresh).astype(int)

    def get_params(self) -> Dict[str, Any]:
        """Return model hyperparameter dictionary."""
        return {
            "input_dim": self.input_dim,
            "hidden_dims": self.hidden_dims,
            "latent_dim": self.latent_dim,
            "activation": self.activation,
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
        """
        Serialize model weights and architecture state to disk using torch.save.
        """
        if not self.is_trained or self.network is None:
            raise RuntimeError("Cannot save an unfitted AutoencoderDetector.")

        path = Path(file_path)
        ensure_dir(path.parent)

        payload = {
            "model_type": "autoencoder",
            "state_dict": self.network.state_dict(),
            "params": self.get_params(),
            "feature_names": self.feature_names_,
            "history": self.history_,
        }
        torch.save(payload, path)
        logger.info(f"Saved Autoencoder weights and configuration to: {path}")
        return path

    @classmethod
    def load(cls, file_path: Union[str, Path], device: Optional[str] = None) -> "AutoencoderDetector":
        """
        Load trained AutoencoderDetector from saved PyTorch checkpoint.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Autoencoder artifact not found at: {path}")

        map_location = torch.device(
            device if device else ("cuda" if torch.cuda.is_available() else "cpu")
        )
        payload = torch.load(path, map_location=map_location, weights_only=False)

        params = payload.get("params", {})
        detector = cls(
            input_dim=params.get("input_dim"),
            hidden_dims=params.get("hidden_dims", [64, 32]),
            latent_dim=params.get("latent_dim", 8),
            activation=params.get("activation", "relu"),
            dropout_rate=params.get("dropout_rate", 0.0),
            learning_rate=params.get("learning_rate", 0.001),
            batch_size=params.get("batch_size", 64),
            epochs=params.get("epochs", 50),
            random_seed=params.get("random_seed", 42),
            device=str(map_location),
        )

        detector.feature_names_ = payload.get("feature_names", [])
        detector.reconstruction_threshold = params.get("reconstruction_threshold", 0.5)
        detector.threshold_strategy = params.get("threshold_strategy", "percentile")
        detector.mse_min_ = params.get("mse_min", 0.0)
        detector.mse_max_ = params.get("mse_max", 1.0)
        detector.history_ = payload.get("history", {})

        # Reconstruct network and load state_dict
        detector._build_network(params["input_dim"])
        detector.network.load_state_dict(payload["state_dict"])
        detector.network.eval()
        detector.is_trained = True

        logger.info(
            f"Loaded AutoencoderDetector from {path} (input_dim={detector.input_dim}, "
            f"latent_dim={detector.latent_dim}, threshold={detector.reconstruction_threshold:.6f})"
        )
        return detector
