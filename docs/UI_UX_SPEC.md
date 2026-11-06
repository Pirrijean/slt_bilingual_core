# SLT UI/UX Specification

> **Identity**: *SLT Bilingual Core · Communication Workspace*  
> **Inspirations**: Cleanmeter (unobtrusive telemetry), OpusClip (content focus), Spinex (visual hierarchy).

---

## 1. Visual Identity & Color System

The interface uses an original, focused color palette avoiding chaotic multi-colored accents:

| Token | Hex | Role | Usage |
| :--- | :--- | :--- | :--- |
| **Graphite** | `#101820` | Base Surface | Deep canvas background, window framing |
| **Slate** | `#1B303B` | Container Surface | Cards, camera stage border, control backgrounds |
| **Teal** | `#42BFB0` | Primary Brand Accent | Active status, anatomical skeleton, primary actions, highlights |
| **Mist** | `#ECF2F3` | Primary Typography | Subtitles, labels, readable translation text |
| **Subtle Gray** | `#8899A6` | Secondary Text | Metadata, timestamps, inactive icons |
| **Warning Amber**| `#F59E0B` | Candidate State | Unconfirmed gesture state in timeline |
| **Success Emerald**| `#10B981` | Confirmed State | Confirmed sign event in timeline |

---

## 2. Three Levels of User Interaction

To prevent overwhelming deaf users or hearing interlocutors with developer telemetry:

### Level 1: Communication (Default Workspace)
- **Perception Stage**: Live camera stream with clean anatomical landmark overlay (Teal lines and dots).
- **Sign Timeline**: Horizontal chronological ribbon showing recognized sign chips with timestamp chips (`00:01.2`) and status indicators.
- **Bilingual Subtitles Card**: Large, high-contrast, dyslexia-friendly display of Spanish and English translations.
- **Audio Controls**: One-click vocalization button and target language switch.

### Level 2: Assistance (Contextual Drawer)
- Slides in from the right when toggled (or via `F1`).
- Contains the 19 visual sign cards with postural descriptions.
- Quick phrase accumulation clear (`Ctrl+L`) and backspace (`Backspace`).

### Level 3: Diagnostics (Discreet Cleanmeter Bar)
- Positioned unobtrusively at the bottom edge.
- Compact single-line telemetry:
  `CAM 01 · 30 FPS · 32 ms · 1 HAND · MODEL v1.0.0 · ENGINE READY`
- Detailed performance breakdown accessible on demand without cluttering the main conversation area.

---

## 3. The Sign Timeline Component

The **Sign Timeline** is a proprietary visual element that transforms raw recognition into an interactive narrative:
- Displays sequence of confirmed `SignEvent` items chronologically.
- Shows execution duration (e.g., `0.8s`).
- Allows clicking on a chip to remove a misrecognized sign.
- Provides immediate visual feedback when a candidate sign is reaching quorum (amber pulse -> teal confirmation).
