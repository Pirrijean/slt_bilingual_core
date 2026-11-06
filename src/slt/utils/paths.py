"""Project paths helper."""
from pathlib import Path

# __file__ is src/slt/utils/paths.py -> parents: [0: utils, 1: slt, 2: src, 3: root]
ROOT_DIR = Path(__file__).resolve().parents[3]
CONFIG_DIR = ROOT_DIR / "config"
MODELS_DIR = ROOT_DIR / "models"
DATA_DIR = ROOT_DIR / "data"
LOGS_DIR = ROOT_DIR / "logs"

LEXICON_PATH = CONFIG_DIR / "lexicon.json"
CLASSES_PATH = CONFIG_DIR / "classes.json"
SETTINGS_PATH = CONFIG_DIR / "settings.json"

HAND_LANDMARKER_TASK = MODELS_DIR / "hand_landmarker.task"
HAND_LANDMARKER_MODEL = HAND_LANDMARKER_TASK
SLT_MODEL_PATH = MODELS_DIR / "slt_model.npz"
DEFAULT_MODEL_PATH = SLT_MODEL_PATH
MODEL_METADATA_PATH = MODELS_DIR / "model_metadata.json"
DEFAULT_LEXICON_PATH = LEXICON_PATH
