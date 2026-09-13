from backend.app.ml.models.lstm_autoencoder import (
    LSTMAutoencoderDetector,
    LSTMAutoencoderNetwork,
)

# Backwards-compatibility alias
LSTMDetector = LSTMAutoencoderDetector

__all__ = ["LSTMAutoencoderDetector", "LSTMAutoencoderNetwork", "LSTMDetector"]
