"""Recognition package for SLT."""
from .classifier import SLTClassifier
from .prediction_filter import PredictionFilter, FilterEvent
from .trainer import train_slt_model
from .metrics import compute_confusion_matrix, compute_metrics
