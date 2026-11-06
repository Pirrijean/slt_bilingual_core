# SLT Bilingual Core: Architecture Blueprint

> **Philosophy**: *Construir sobre hombros de gigantes, pero desarrollar una solución propia.*

The SLT Bilingual Core is structured as an original **Human-Machine Communication Workspace** designed for deaf and hard-of-hearing individuals. Rather than a fragile collection of glued libraries or a naive frame-by-frame classifier, SLT is built on a clean, decoupled, event-driven architecture.

---

## 1. Architectural Layers & Separation of Concerns

```
+------------------------------------------------------------------+
|                        PERCEPTION LAYER                          |
|             (OpenCV Capture + MediaPipe HandLandmarker)          |
+---------------------------------+--------------------------------+
                                  | Raw 21 3D Landmarks (Normalized)
                                  v
+------------------------------------------------------------------+
|                        RECOGNITION LAYER                         |
|   (Geometric Descriptor + SignRecognizer Protocol / SLT-KNN)     |
+---------------------------------+--------------------------------+
                                  | Discrete Predictions (label, conf, dist)
                                  v
+------------------------------------------------------------------+
|                      SLT INTERACTION ENGINE                      |
| (Finite State Machine: IDLE -> TRACKING -> CANDIDATE -> CONFIRM) |
|           Emits: SignEvent (SIGN_CONFIRMED, SIGN_RELEASED)       |
+------------------+------------------------------+----------------+
                   | SignEvent                    | SignEvent
                   v                              v
+----------------------------------+   +---------------------------+
|          LANGUAGE ENGINE         |   |    SIGN TIMELINE & HUD    |
| (SemanticFrame + SVO Realizers)  |   | (Visual sequence tracker) |
+------------------+---------------+   +---------------------------+
                   | Bilingually Realized Text (ES/EN)
                   v
+----------------------------------+-------------------------------+
|                       OUTPUT DISPATCH                            |
|    +-----------------------------+-----------------------------+ |
|    |      COMMUNICATION UI       |      SPEECH SYNTHESIS       | |
|    | (High-Contrast Subtitles)   | (Non-blocking SAPI5 Queue)  | |
|    +-----------------------------+-----------------------------+ |
+------------------------------------------------------------------+
```

---

## 2. Component Responsibilities (Compact Architecture)

| Module | Core Responsibility | Upstream Dependency | Downstream Output |
| :--- | :--- | :--- | :--- |
| `slt.capture` | Camera acquisition, frame timestamping, device selection | OpenCV VideoCapture | Thread-safe frame stream |
| `slt.perception` | Anatomical perception, palm detection, landmark isolation | MediaPipe Tasks (`HandLandmarker`) | `HandDetectionResult` with 21 coordinates per hand |
| `slt.recognition` | Feature extraction (106-D invariant geometry) & classification | `SignRecognizer` Protocol | Frame prediction tuple `(gloss, confidence, is_valid)` |
| `slt.interaction` | Temporal state decoding, hysteresis, debounce, timeline tracking | Discrete frame predictions | `SignEvent` stream (`SIGN_CONFIRMED`, `SIGN_RELEASED`) |
| `slt.language` | Lexicon lookup, `SemanticFrame` abstraction, bilingual syntax rules | Confirmed `SignEvent` sequence | Natural Spanish and English translated text |
| `slt.speech` | Asynchronous speech synthesis for translated utterances | Language Engine string | Multithreaded SAPI5 audio playback |
| `slt.application` | Master orchestrator coordinating pipelines and event subscriptions | Worker threads | Central event dispatcher |
| `slt.ui` | Visual Communication Workspace, Sign Timeline, HUD telemetry | Application state & events | PySide6 Desktop GUI |

---

## 3. Communication Pattern: Event Stream Decoupling

No component directly commands another component. Instead:
1. `perception` produces landmarks without knowing what sign is being performed.
2. `recognition` computes geometric descriptors and scores candidates without knowing sentence context.
3. `interaction` monitors temporal stability and emits **`SignEvent`** objects.
4. `language` listens to `SignEvent` occurrences, builds an abstract semantic representation (**`SemanticFrame`**), and generates target texts.
5. `ui` and `speech` render and vocalize the resulting linguistic state.

This ensures any single component (such as swapping the classifier from k-NN to an ONNX model, or porting the UI) can be modified without altering the rest of the application.
