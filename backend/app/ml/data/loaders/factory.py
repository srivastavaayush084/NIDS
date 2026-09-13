from typing import Dict, List, Optional, Type
from backend.app.ml.data.loaders.base_loader import BaseDatasetLoader
from backend.app.ml.data.loaders.nsl_kdd_loader import NSLKDDLoader
from backend.app.ml.data.loaders.cicids_loader import CICIDSLoader
from backend.app.ml.data.loaders.unsw_nb15_loader import UNSWNB15Loader
from backend.app.ml.data.loaders.synthetic_loader import SyntheticSampleLoader

_LOADER_REGISTRY: Dict[str, Type[BaseDatasetLoader]] = {
    "nsl_kdd": NSLKDDLoader,
    "nsl-kdd": NSLKDDLoader,
    "cicids2017": CICIDSLoader,
    "cicids_2017": CICIDSLoader,
    "cicids": CICIDSLoader,
    "unsw_nb15": UNSWNB15Loader,
    "unsw-nb15": UNSWNB15Loader,
    "unsw": UNSWNB15Loader,
    "synthetic": SyntheticSampleLoader,
    "sample": SyntheticSampleLoader,
}


def get_dataset_loader(dataset_name: str, **kwargs) -> BaseDatasetLoader:
    """
    Factory function to instantiate the appropriate Dataset Loader.

    Args:
        dataset_name (str): Identifier for dataset ('nsl_kdd', 'cicids2017', 'unsw_nb15', 'synthetic').
        **kwargs: Additional parameters passed to the loader constructor (e.g. raw_dir).

    Returns:
        BaseDatasetLoader: Instantiated loader instance.
    """
    key = dataset_name.lower().strip()
    if key not in _LOADER_REGISTRY:
        available = list(set(_LOADER_REGISTRY.keys()))
        raise ValueError(f"Unsupported dataset loader '{dataset_name}'. Available options: {available}")
    loader_cls = _LOADER_REGISTRY[key]
    return loader_cls(**kwargs)


def list_supported_datasets() -> List[str]:
    """Returns a unique list of canonical supported dataset names."""
    return ["nsl_kdd", "cicids2017", "unsw_nb15", "synthetic"]


def register_dataset_loader(name: str, loader_class: Type[BaseDatasetLoader]) -> None:
    """Register a custom dataset loader into the factory registry."""
    _LOADER_REGISTRY[name.lower().strip()] = loader_class
