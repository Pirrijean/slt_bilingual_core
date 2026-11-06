# Technology Provenance & Intellectual Property Matrix

This document explicitly delineates third-party software and scientific foundations from original proprietary developments in **SLT Bilingual Core**.

---

## 1. Technology Provenance Matrix

| Component | Upstream Origin / Foundation | SLT Original Development | Intellectual Property & Nature |
| :--- | :--- | :--- | :--- |
| **Camera Acquisition** | OpenCV (`cv2.VideoCapture`) | `slt.capture` thread-safe worker | Wrapper & lifecycle orchestration |
| **Anatomical Perception** | Google MediaPipe (`HandLandmarker`) | `slt.perception` task integration & drawing | Custom overlay aesthetics, coordinate decoupling |
| **Feature Extraction** | Geometric & Trigonometric Foundations | `slt.recognition` 106-D descriptor | **Original SLT Algorithm**: scale, translation & posture invariance |
| **Temporal Interaction** | AutoNav HMI State Machine (CC BY 4.0) | `slt.interaction` FSM & `SignEvent` | **Original SLT Architecture**: adapted for linguistic events |
| **Linguistic Engine** | Generative Grammar & Frame Semantics | `slt.language` `SemanticFrame` & realizers | **Original SLT Development**: deterministic SVO rules & pro-drop syntax |
| **Speech Output** | Microsoft Windows SAPI5 COM API | `slt.speech` non-blocking worker queue | Thread-safe COM queue & voice switcher |
| **User Interface** | Qt6 / PySide6 GUI toolkit | `slt.ui` Communication Workspace & Timeline | **Original SLT Design**: Sign Timeline, Cleanmeter telemetry, custom theme |
| **Dataset & Weights** | Synthetic / Seed landmark collection | Stratified multi-participant augmented dataset | **Original SLT Model**: 92.48% balanced accuracy |

---

## 2. Scientific Attributions

1. **AutoNav Study**:
   - Citation: *Teleoperation system for multiple robots with intuitive hand recognition interface*, Sci Rep 14, 29815 (2024). [https://doi.org/10.1038/s41598-024-80898-x](https://doi.org/10.1038/s41598-024-80898-x).
   - License: Creative Commons Attribution 4.0 International (CC BY 4.0).
   - Adaptation: Concept of hand state transitions and hysteresis adapted to sign language event generation (`SignEvent`).

2. **MediaPipe Hand Landmarker**:
   - Provider: Google LLC.
   - License: Apache License 2.0.
   - Use: 21 3D anatomical keypoint perception.
