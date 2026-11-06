# Model Card: SLT Bilingual Core 1.0.0

## 1. Model Details
- **Model Name:** SLT Bilingual Core Custom Recognizer
- **Version:** 1.0.0
- **Type:** Weighted k-NN & Geometric Prototype Classifier with Distance/Margin Unknown Rejection
- **Input Dimension:** 106 normalized anatomical features (63 3D coordinates + 15 joint angles + 10 fingertip pairwise distances + 5 wrist-to-tip distances + 3 palm unit normal vectors + 10 finger apertures)
- **Output:** Categorical prediction across 19 classes (including `_NADA_` rejection state) with confidence and stability metrics
- **Developer:** SLT Bilingual Core AI Team (`jp.ninor1@uniandes.edu.co`)
- **License:** MIT

## 2. Intended Use
- **Primary Use:** Real-time sign language posture recognition and bilingual translation (Spanish / English) from standard RGB webcams.
- **Target Vocabulary:** 19 defined lexical classes encompassing courtesy greetings, essential requests, communicative expressions, pronouns, verbs, and fingerspelled vowels.
- **Out-of-Scope:** Continuous uncontrolled sign language with non-manual facial grammatical inflections, body movements outside upper torso/hand frame, or unconstrained dictionaries beyond the 19 supported classes.

## 3. Training & Evaluation Data
- **Training Data:** 2,660 augmented anatomical landmark samples across 4 distinct participant partitions.
- **Evaluation Data:** 665 independent hold-out test samples from a 5th participant never seen during training or threshold tuning.
- **Augmentation Techniques:** 3D rotational perturbations ($\pm 14^\circ$), scale jittering ($0.90\times - 1.12\times$), translation shifts, sensor joint Gaussian noise ($\sigma = 0.008$), and controlled bilateral horizontal mirroring for left-hand invariance.

## 4. Quantitative Performance
Evaluated on the independent hold-out test set:
- **Balanced Accuracy:** 92.48%
- **Macro F1-Score:** 92.20%
- **Macro Precision:** 93.18%
- **Macro Recall:** 92.48%
- **Inference Latency:** 0.93 ms per sample on CPU (~1,070 classifications/second)

## 5. Supported Classes (19 Total)
1. `_NADA_` (Reposo / Ausencia / Rechazo de gestos desconocidos)
2. `HOLA`
3. `GRACIAS`
4. `POR_FAVOR`
5. `SI`
6. `NO`
7. `AYUDA`
8. `AGUA`
9. `COMIDA`
10. `ESTAR_BIEN`
11. `TE_QUIERO`
12. `YO`
13. `TU`
14. `QUERER`
15. `A`
16. `E`
17. `I`
18. `O`
19. `U`

## 6. Limitations & Considerations
- **Lighting & Camera Quality:** Extreme underexposure or severe motion blur degrades MediaPipe HandLandmarker keypoint precision.
- **Extreme Occlusion:** When more than 3 fingers are fully occluded behind the palm, keypoints may jitter.
- **Single vs Dual Hand:** Gestures requiring two hands (such as `AYUDA`) evaluate the dominant upper hand with palm proximity context.
