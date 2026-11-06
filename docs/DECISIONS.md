# Architecture Decision Records (ADR) - SLT Bilingual Core

This document records the key architectural decisions, rationale, and consequences for the SLT Bilingual Core platform.

---

## ADR-001: Independent SLT Core (`slt_core`)
- **Status:** Approved
- **Context:** The system needs automated CI validation across Windows, Linux, and macOS without requiring physical webcams, GUI servers, or heavy machine learning dependencies during unit tests.
- **Decision:** The core pipeline (`slt_core`) is implemented as a lightweight, pure-Python architecture with typed contracts, zero mandatory runtime GUI/C++ perception dependencies, and full testability via mock components.
- **Consequences:** Tests run in seconds across any platform. GUI and MediaPipe can be developed, updated, or swapped in subsequent phases without refactoring the foundational contracts.

---

## ADR-002: Sovereign Sign Language Profiles
- **Status:** Approved
- **Context:** Treating sign languages as dialects of a shared classifier by simply toggling an output language string is linguistically invalid and prevents international scaling.
- **Decision:** Each sign language (e.g., LSC, ASL) is registered as an independent linguistic product with its own manifest, vocabulary, kinematic model, and grammatical rules.
- **Consequences:** The system cleanly separates input sign languages from target spoken/written languages (`es-CO`, `en-US`), allowing any sign language to translate into multiple locales via a common semantic interface.

---

## ADR-003: Source-Relative Nanosecond Timestamps
- **Status:** Approved
- **Context:** Live webcams and local video files have completely different clock domains (system monotonic time vs. presentation timestamps $PTS \times time\_base$).
- **Decision:** Every `FramePacket` specifies an integer timestamp in nanoseconds relative to its `source_id`. Clocks across different sources are never mixed or compared.
- **Consequences:** Exact synchronization for offline video analysis without timing jitter, and seamless multi-camera capability.

---

## ADR-004: Invariant Typed Data Contracts
- **Status:** Approved
- **Context:** Passing loose dictionaries between perception, recognition, and translation leads to runtime typing bugs and unvalidated assumptions.
- **Decision:** All inter-layer communication uses frozen, slotted dataclasses (`FramePacket`, `Landmark`, `HandObservation`, `PerceptionFrame`, `RecognitionHypothesis`, `SignEvent`, `TranslationOutput`). Strict validation is enforced on initialization.
- **Consequences:** Low memory overhead, fast field access, immutability, and zero unhandled invalid states reaching downstream engines.

---

## ADR-005: Cross-Platform Hardware Abstraction
- **Status:** Approved
- **Context:** OpenCV backend flags (like `CAP_DSHOW`) and Windows COM SAPI5 break on Linux and macOS.
- **Decision:** Platform-specific services (camera device enumeration, speech synthesis, user directories) are isolated behind abstract protocols in `src/slt/platform/`.
- **Consequences:** Core components never import platform-specific modules directly.

---

## ADR-006: Decoupled Temporal Decoder
- **Status:** Approved
- **Context:** A static frame classifier alone cannot translate continuous sign language containing movement epenthesis and transitional holds.
- **Decision:** The classification of static configurations and the temporal sequencing of continuous gestures are handled by distinct components (`RecognitionBackend` vs. `TemporalDecoder`).
- **Consequences:** We can upgrade from geometric hysteresis decoders to deep sequence models without altering the pipeline architecture.

---

## ADR-007: Rigorous Translation Output Validation
- **Status:** Approved
- **Context:** A translation backend could silently omit a requested language or return outputs belonging to a different sign language profile.
- **Decision:** `CorePipeline` strictly validates that translation outputs cover all requested target locales without duplicates, match the current profile ID, and reference only valid event IDs.
- **Consequences:** Guaranteed bilingual consistency across all emitted messages.

---

## ADR-008: Non-Blocking Speech Synthesis Dispatch
- **Status:** Approved
- **Context:** Calling blocking speech synthesizers (`runAndWait()`) freezes the UI and drops incoming camera frames.
- **Decision:** Speech requests are enqueued asynchronously to a background worker maintaining a dedicated message queue.
- **Consequences:** Smooth UI rendering and uninterrupted visual perception during audio playback.
