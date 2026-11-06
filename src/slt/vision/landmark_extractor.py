"""Geometric 106-dimensional hand feature extractor."""
from __future__ import annotations
import numpy as np

WRIST = 0
THUMB_CMC, THUMB_MCP, THUMB_IP, THUMB_TIP = 1, 2, 3, 4
INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP = 5, 6, 7, 8
MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP = 9, 10, 11, 12
RING_MCP, RING_PIP, RING_DIP, RING_TIP = 13, 14, 15, 16
PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP = 17, 18, 19, 20

FINGER_CHAINS = [
    [0, 1, 2, 3, 4],
    [0, 5, 6, 7, 8],
    [0, 9, 10, 11, 12],
    [0, 13, 14, 15, 16],
    [0, 17, 18, 19, 20],
]

TIPS = [4, 8, 12, 16, 20]
MCPS = [2, 5, 9, 13, 17]

TIP_PAIRS = [
    (4, 8), (4, 12), (4, 16), (4, 20),
    (8, 12), (8, 16), (8, 20),
    (12, 16), (12, 20),
    (16, 20)
]

def joint_angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """Calculate the interior joint angle in radians between segments (b - a) and (c - b)."""
    v1 = a - b
    v2 = c - b
    norm_v1 = np.linalg.norm(v1)
    norm_v2 = np.linalg.norm(v2)
    if norm_v1 < 1e-7 or norm_v2 < 1e-7:
        return 0.0
    cosine = np.dot(v1, v2) / (norm_v1 * norm_v2)
    cosine = np.clip(cosine, -1.0, 1.0)
    return float(np.arccos(cosine))

def normalize_landmarks(points: np.ndarray, handedness: str = "Right", mirror_left: bool = True) -> np.ndarray:
    """
    Translate wrist to origin (0,0,0) and scale by palm reference width.
    If mirror_left is True and handedness is 'Left', mirror across the X-axis
    so left and right hands share the same canonical frame.
    """
    pts = np.asarray(points, dtype=np.float32).copy()
    if pts.shape != (21, 3):
        raise ValueError(f"Se esperaban (21, 3), se recibió {pts.shape}")

    # 1. Translate wrist to origin
    origin = pts[WRIST].copy()
    normalized = pts - origin

    # 2. Mirror left hand across X axis if requested
    if mirror_left and handedness.lower() == "left":
        normalized[:, 0] = -normalized[:, 0]

    # 3. Palm reference scale (average of wrist-middle and index-pinky distance)
    palm_width = np.linalg.norm(normalized[INDEX_MCP] - normalized[PINKY_MCP])
    palm_len = np.linalg.norm(normalized[MIDDLE_MCP] - normalized[WRIST])
    scale = 0.5 * (palm_width + palm_len)
    if scale < 1e-6:
        scale = 1.0

    normalized /= scale
    return normalized

def extract_features(points: np.ndarray, handedness: str = "Right", mirror_left: bool = True) -> np.ndarray:
    """
    Extract exact 106-dimensional normalized geometric feature vector:
      - 63: Normalized 3D coordinates (21 x 3)
      - 15: Joint flexion angles (5 fingers x 3 joints)
      - 10: Pairwise Euclidean distances between all 5 finger tips
      -  5: Euclidean distances from finger tips to wrist origin
      -  3: Unit normal vector of the palm plane (Nx, Ny, Nz)
      - 10: Finger apertures (5 to respective MCP, 5 to palm center middle MCP)
      Total = 106 features
    """
    norm = normalize_landmarks(points, handedness=handedness, mirror_left=mirror_left)

    # 1. Coordinates (63)
    coords = norm.ravel()

    # 2. Angles (15)
    angles = []
    for chain in FINGER_CHAINS:
        for i in range(1, 4):
            ang = joint_angle(norm[chain[i - 1]], norm[chain[i]], norm[chain[i + 1]])
            angles.append(ang)
    angles = np.array(angles, dtype=np.float32)

    # 3. Distances between finger tips (10)
    tip_distances = []
    for t1, t2 in TIP_PAIRS:
        d = np.linalg.norm(norm[t1] - norm[t2])
        tip_distances.append(d)
    tip_distances = np.array(tip_distances, dtype=np.float32)

    # 4. Distances from tips to wrist (5)
    wrist_distances = np.array([np.linalg.norm(norm[t]) for t in TIPS], dtype=np.float32)

    # 5. Palm normal vector (3)
    v_index = norm[INDEX_MCP] - norm[WRIST]
    v_pinky = norm[PINKY_MCP] - norm[WRIST]
    palm_normal = np.cross(v_index, v_pinky)
    p_norm = np.linalg.norm(palm_normal)
    if p_norm > 1e-7:
        palm_normal /= p_norm
    else:
        palm_normal = np.array([0.0, 0.0, 1.0], dtype=np.float32)

    # 6. Finger apertures (10)
    # 5 distances from tip to its own MCP
    mcp_distances = np.array([np.linalg.norm(norm[t] - norm[m]) for t, m in zip(TIPS, MCPS)], dtype=np.float32)
    # 5 distances from tip to central middle MCP (landmark 9)
    center_distances = np.array([np.linalg.norm(norm[t] - norm[MIDDLE_MCP]) for t in TIPS], dtype=np.float32)
    apertures = np.concatenate([mcp_distances, center_distances])

    # Assemble full 106-D feature vector
    features = np.concatenate([
        coords,           # 63
        angles,           # 15
        tip_distances,    # 10
        wrist_distances,  #  5
        palm_normal,      #  3
        apertures         # 10
    ]).astype(np.float32)

    if features.shape[0] != 106:
        raise ValueError(f"Vector de características debe tener dimensión 106, pero tiene {features.shape[0]}")

    return features
