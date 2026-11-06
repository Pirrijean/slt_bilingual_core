# LSC Linguistic Annotation Guidelines & Tier Conventions
**SLT Bilingual Core — Colombian Sign Language**  
**Version:** 1.0.0 (Phase 3A)  
**Standard Format:** ELAN (.eaf v3.0)  

---

## 1. Principles of Linguistic Annotation for LSC

Sign languages are multidimensional, visual-spatial natural languages with simultaneous manual and non-manual components. LSC annotation in SLT must avoid reducing sentences to strings of isolated spoken words:
1. **Semi-Open Temporal Intervals:** All annotations are defined on semi-open intervals $[t_{\text{start}}, t_{\text{end}})$ measured in nanoseconds ($t_{\text{ns}} = t_{\text{ms}} \times 10^6$).
2. **Tier Simultaneity:** Non-manual facial expressions, torso shifts, and manual signs can overlap temporally.
3. **Glossing vs. Translation:**
   - Glosses (`sign_gloss`) are linguistic reference labels for lexical signs (in uppercase, e.g. `HOLA`, `POR-FAVOR`), not literal target language translations.
   - Sentential translations (`translation_es`, `translation_en`) attach to the communicative utterance tier (`utterance`), capturing idiom, grammar, and pragmatics.

---

## 2. Standard Tiers Architecture

| Tier ID | Level | Alignment Type | Parent Tier | Description |
|---|---|---|---|---|
| `utterance` | Utterance | Time Interval | None | Complete communicative discourse unit. |
| `translation_es` | Translation | Reference | `utterance` | Natural Colombian Spanish translation. |
| `translation_en` | Translation | Reference | `utterance` | Natural US English translation. |
| `sign_token` | Sign | Time Interval | `utterance` | Physical duration of the sign token (stroke + hold). |
| `sign_gloss` | Lexical | Reference | `sign_token` | Standardized uppercase gloss identifier. |
| `lexical_entry` | Lexical | Reference | `sign_token` | ID linked to `corpus/lsc/lexicon/lexical_entries.json`. |
| `left_handshape` | Manual | Time Interval | `utterance` | Left hand anatomical configuration. |
| `right_handshape` | Manual | Time Interval | `utterance` | Right hand anatomical configuration. |
| `hand_movement` | Manual | Time Interval | `utterance` | Trajectory and path features (linear, circular, repeat). |
| `hand_orientation` | Manual | Time Interval | `utterance` | Palm and finger direction relative to torso. |
| `hand_location` | Manual | Time Interval | `utterance` | Spatial locus (neutral space, chest, chin, forehead). |
| `facial_nonmanual` | Non-manual | Time Interval | `utterance` | Eyebrow movement, squinting, mouthing. |
| `head_movement` | Non-manual | Time Interval | `utterance` | Head nod, shake, tilt, thrust. |
| `eye_gaze` | Non-manual | Time Interval | `utterance` | Gaze direction (addressee, hand locus, abstract). |
| `body_posture` | Non-manual | Time Interval | `utterance` | Torso lean or rotation indicating role shift. |

---

## 3. Boundary Precision Standards

Annotators must mark boundary precision in `boundary_quality`:
- `exact`: Video frame rate and lighting allow unambiguous identification of sign stroke initiation and completion within $\pm 1$ frame ($< 33\text{ ms}$).
- `approximate`: Coarticulation, transition blending, or minor motion blur causes uncertainty within $\pm 3$ frames.
- `unverified`: Automatic or initial draft annotation requiring human adjudication.
