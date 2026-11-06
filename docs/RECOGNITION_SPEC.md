# SLT Recognition Specification

> **Methodological Principle**: *Perception provides anatomical points; SLT Recognition provides proprietary geometric representations and invariant decision boundaries.*

---

## 1. Unified Interface: `SignRecognizer` Protocol

To allow seamless experimentation without refactoring upstream pipelines, all classifiers in SLT adhere to the standard `SignRecognizer` protocol:

```python
from typing import Protocol, Dict, Any, Tuple
import numpy as np

class SignRecognizer(Protocol):
    """Protocol for SLT gesture and sign classifiers."""
    
    def predict(self, features: np.ndarray) -> Tuple[str, float, bool]:
        """
        Classify a feature vector.
        
        Args:
            features: 1D array of geometric features.
            
        Returns:
            Tuple of:
            - gloss (str): Predicted sign label (e.g., 'HOLA', 'AGUA', '_NADA_').
            - confidence (float): Confidence score in [0.0, 1.0].
            - is_valid (bool): True if prediction exceeds threshold and is not an outlier.
        """
        ...
        
    def load(self, model_path: str) -> None:
        """Load serialized model weights and hyperparameters."""
        ...
```

---

## 2. Geometric Representations

SLT analyzes three distinct representations:

### A. Normalized Cartesian Geometry (63 features)
- Coordinates $\mathbf{P}_i = (x_i, y_i, z_i)$ for $i \in \{0, \dots, 20\}$.
- **Translation Invariance**: Centered at the wrist:
  $$\mathbf{P}'_i = \mathbf{P}_i - \mathbf{P}_0$$
- **Scale Invariance**: Normalized by palm scale factor $S = \|\mathbf{P}_9 - \mathbf{P}_0\|_2$ (distance from wrist to middle MCP):
  $$\hat{\mathbf{P}}_i = \frac{\mathbf{P}'_i}{S}$$

### B. Articular & Inter-segment Geometry (43 features)
1. **Joint Flexion Angles (15 features)**: 3 articulation angles per digit (MCP, PIP, DIP) computed via vector dot product:
   $$\theta = \arccos\left(\frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\|_2 \|\mathbf{v}\|_2 + \epsilon}\right)$$
2. **Pairwise Fingertip Distances (10 features)**: Euclidean distance between all 5 finger tips $\binom{5}{2} = 10$.
3. **Tip-to-Wrist Distances (5 features)**: Normalized span of each finger tip to landmark 0.
4. **Palm Plane Unit Normal (3 features)**: Normal vector to the triangle formed by wrist (0), index MCP (5), and pinky MCP (17):
   $$\mathbf{n} = \frac{(\mathbf{P}_5 - \mathbf{P}_0) \times (\mathbf{P}_{17} - \mathbf{P}_0)}{\|(\mathbf{P}_5 - \mathbf{P}_0) \times (\mathbf{P}_{17} - \mathbf{P}_0)\|_2}$$
5. **Digital Apertures (10 features)**: Euclidean distance from each tip to its respective MCP base (5) and to the palm center (landmark 9) (5).

### C. Hybrid Representation (Production Baseline: 106 Features)
The production model concatenates Representation A (63) and Representation B (43), providing an exact **106-dimensional normalized descriptor** that is robust to translation, scale, and camera perspective shifts.

---

## 3. Rejection of Unknowns & Rest Postures (`_NADA_`)

A sign language system must not classify idle hands, transitions, or random gestures as active signs.
SLT employs a dual-threshold rejection mechanism:
1. **Outlier Distance Threshold**: If minimum Euclidean distance to known clusters exceeds $d_{max} = 1.35$, classify as `_NADA_`.
2. **Margin Ratio**: If $\frac{d_1}{d_2} > 0.88$ (ambiguity between top two candidate classes), mark candidate as unconfirmed.

---

## 4. Evaluation Protocol

- **Validation Scheme**: Leave-One-Group-Out (LOGO) cross-validation across distinct signers/participants to prevent synthetic data leakage.
- **Production Performance Target**:
  - Balanced Accuracy $\ge 90\%$ (Current benchmark: **92.48%**).
  - Inference Latency $\le 2.0\text{ ms}$ (Current benchmark: **0.93 ms**).
