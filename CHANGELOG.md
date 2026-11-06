# Changelog

All notable changes to the SLT Bilingual Core project will be documented in this file.

## [1.0.0] - 2026-11-06

### Added
- **MediaPipe Tasks HandLandmarker:** Modern vision tracking replacing deprecated `mp.solutions` API.
- **106-Dimensional Feature Extractor:** Translation and scale-invariant geometric descriptors combining 3D normalized coordinates, joint angles, fingertip distances, palm unit normal vectors, and finger apertures.
- **Weighted k-NN Classifier (`slt_model.npz`):** Pure-NumPy inference with unknown gesture rejection (92.48% balanced accuracy on unseen participant holdout test set).
- **Temporal Prediction Filter:** Majority voting debounce state machine with `SIGN_CONFIRMED` and `SIGN_RELEASED` events.
- **Bilingual Translation Engine:** Grammar-aware sentence builder supporting subject-verb agreement, idiomatic phrases, courtesy tails, and fingerspelling assembly.
- **Asynchronous Speech Engine:** Windows SAPI5 COM multi-threaded synthesizer with Spanish (`Helena`) and English (`Zira`) voices.
- **Desktop Graphical Interface (PySide6):** Minimalist scientific dark dashboard with live telemetry HUD (FPS, latency, hand count, current sign), large subtitle cards, and sign guide drawer.
- **Automated Validation Suite:** 19 comprehensive unit and integration tests passing with 100% success rate.
- **Automated Installers:** One-click `install.bat`, `install.sh`, and cross-platform `slt_installer.py`.
- **CI/CD Automation:** GitHub Actions workflow testing Python 3.12 compatibility.
