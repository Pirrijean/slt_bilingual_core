# SLT Evaluation Protocol & Data Partitioning Specification
**SLT Bilingual Core — Colombian Sign Language**  
**Version:** 1.0.0 (Phase 3A)  

---

## 1. The Signer-Independent Imperative

A pervasive flaw in historical sign language recognition research is evaluating classifiers on random frame splits or random video splits where the same participants appear in both training and test sets. This produces inflated accuracies (often $>95\%$) that drop by $20\text{--}40\%$ when deployed on unseen deaf signers, because models learn individual idiosyncratic signer anatomy and clothing rather than sign phonology.

In SLT Bilingual Core:
1. **Signer-Independent (SI) Partitioning is Mandatory:** No participant (`signer_id`) observed in the training split may ever appear in validation or test splits.
2. **Zero Frame-Level Splitting:** Random splitting of consecutive video frames is strictly forbidden.
3. **Augmentation Lineage Rule:** Any augmented or perturbed derivative of a recording must be allocated to the exact same split as its parent recording (`slt_corpus.splits.validate_no_augmentation_leakage`).

---

## 2. Partitioning Dimensions

| Evaluation Protocol | Grouping Criterion | Target Generalization Hypothesis |
|---|---|---|
| **Signer-Independent (SI)** | Disjoint by `signer_id` | Generalizes across anatomical hand sizes, signing speeds, and personal variants. |
| **Sentence-Disjoint (SD)** | Disjoint by communicative prompt | Generalizes to novel grammatical combinations and unobserved discourse sentences. |
| **Domain-Shift (DS)** | Disjoint by capture environment / camera | Generalizes to unseen lighting, sensor noise, and background conditions. |

---

## 3. Metrics for Downstream Recognition (Phase 4)

When recognition models are trained in future phases, performance will be benchmarked on:
- **Isolated Sign Recognition:**
  - Macro-F1 across all vocabulary classes.
  - Per-signer accuracy variance (reporting standard deviation across test signers).
  - Outlier rejection accuracy on non-sign gestures (`_NADA_`).
- **Continuous Sign Recognition:**
  - Word Error Rate (WER): $\text{WER} = \frac{S + D + I}{N}$ on sign gloss token sequences.
  - Temporal boundary IoU: Jaccard overlap on sign transition boundaries.
- **Bilingual Translation (LSC -> es-CO / en-US):**
  - Human bilingual adequacy and semantic preservation scoring.
  - Automatic BLEU / chrF indicators (treated as supplementary metrics, not definitive proof of linguistic accuracy).
