# SLT Bilingual Core: Architecture Document

```
                                  [ WEBCAM ]
                                       │
                                       ▼ (OpenCV CAP_DSHOW, 30 FPS)
                          [ CameraWorker (QThread) ]
                                       │
                                       ▼
                       [ MediaPipe HandLandmarker ]
                      (21 Keypoints 2D/3D in meters)
                                       │
                                       ▼
                         [ LandmarkExtractor 106-D ]
            (Translation & scale normalization + angles + apertures)
                                       │
                                       ▼
                           [ SLTClassifier (k-NN) ]
                (Pure NumPy inference < 1 ms + Outlier Rejection)
                                       │
                                       ▼
                           [ PredictionFilter ]
                 (Sliding window quorum + Debounce state machine)
                                       │
                                       ▼ (SIGN_CONFIRMED Event)
                       [ BilingualTranslator / Lexicon ]
                  (Grammar SVO, Idiomatic phrases, Fingerspelling)
                       │                              │
                       ▼                              ▼
             [ Spanish Text Subtitle ]     [ English Text Subtitle ]
                       │                              │
                       ▼                              ▼
                 [ PySide6 UI ]              [ SpeechEngine ]
            (VideoWidget, Subtitles)        (SAPI5 / pyttsx3 async)
```

## Module Responsibilities
- `slt.vision`: Raw camera acquisition, MediaPipe Tasks hand tracking, drawing utilities, and 106-D geometric feature extraction.
- `slt.recognition`: Lightweight pure-NumPy classification, temporal stability filtering, dataset metrics, and model training.
- `slt.language`: Semantic lexicon, grammatical sentence construction, fingerspelling assembly, and bilingual gloss accumulation.
- `slt.audio`: Asynchronous speech synthesis queue, Windows SAPI5 voice engine, and platform adapters.
- `slt.camera`: Dedicated background thread (`CameraWorker`) for non-blocking camera capture and vision pipelines.
- `slt.gui`: Modern minimalist PySide6 desktop interface with telemetry HUD, subtitle displays, controls, and sign guide drawer.
