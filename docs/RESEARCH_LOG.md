# SLT Research Log

Chronological record of scientific inquiries, architectural insights, and design iterations for **SLT Bilingual Core**.

---

## Entry 01: Analysis of AutoNav State Transitions (HMI)
- **Reference**: *Teleoperation system for multiple robots with intuitive hand recognition interface*, Scientific Reports 14, 29815 (Dec 2024). DOI: [10.1038/s41598-024-80898-x](https://doi.org/10.1038/s41598-024-80898-x). (Licensed under CC BY 4.0).
- **Key Insight**: The AutoNav system avoids treating each video frame as an independent robotic command by enforcing state transitions (open hand, closed hand, gesture confirmation) mediated by hysteresis.
- **SLT Adaptation**: We adapt this HMI principle to sign language processing. Instead of frame-by-frame text emitting, SLT defines a discrete 5-state automaton (`IDLE`, `TRACKING`, `CANDIDATE`, `CONFIRMED`, `WAITING_RELEASE`) that emits discrete `SignEvent` occurrences only when temporal stability is proven.

---

## Entry 02: OpusClip & Spinex Interface Analysis
- **References**: OpusClip (Content-centric workflow); Spinex (Visual hierarchy and contrast control).
- **Key Insight**: Deaf and hearing users need uninterrupted communication. Traditional machine learning dashboards clutter the viewport with dozens of debug gauges.
- **SLT Adaptation**: Restructured interface into 3 tiers: Level 1 (Communication), Level 2 (Assistance drawer), and Level 3 (Discreet diagnostics). Centralized user focus on the Perception Stage, the Sign Timeline, and large bilingual subtitles.

---

## Entry 03: Cleanmeter Telemetry Paradigm
- **Reference**: Cleanmeter (Minimalistic Real-Time System Monitor).
- **Key Insight**: High-density gauges produce visual fatigue. A discreet, single-line technical strip at the footer conveys all essential hardware/model health indicators without competing with conversational content.
- **SLT Adaptation**: Designed the single-line footer status indicator displaying Camera, FPS, Latency, Hands detected, and Model Status.

---

## Entry 04: Geometric Invariance & Feature Representation
- **Hypothesis**: Raw $(x, y, z)$ coordinates fail across different hand sizes and distances from camera.
- **Resolution**: Implemented wrist-centered, middle-metacarpal scaled normalized coordinates, augmented by 15 joint flexion angles and 10 interdigital distances. Mathematical tests verify exact scale and translation invariance ($< 10^{-6}$ drift under translation and scaling).
