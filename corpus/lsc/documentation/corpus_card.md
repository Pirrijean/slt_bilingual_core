# LSC Corpus Card: Colombian Sign Language
**Corpus ID:** `lsc-corpus`  
**Profile ID:** `lsc`  
**Target Locales:** `es-CO` (Colombian Spanish), `en-US` (US English)  
**Version:** 0.1.0 (Foundational Architecture)  

---

## 1. Corpus Summary
The SLT Colombian Sign Language Corpus is a multimodal, linguistic-first collection of LSC productions designed for empirical sign language recognition, temporal boundary modeling, and bidirectional translation. It records continuous natural communication as well as controlled lexical tokens with native deaf signers.

## 2. Modality & Technical Specifications
- **Video:** Full HD ($1920 \times 1080$) at $\ge 30\text{ fps}$, progressive scan, H.264 / AVC container.
- **Landmarks:** 21 anatomical hand landmarks, 468/478 facial landmarks, and 33 pose landmarks tracked synchronously by frame index.
- **Annotations:** ELAN (.eaf v3.0) with nanosecond semi-open intervals $[start, end)$ across 20 hierarchical tiers.

## 3. Governance & Legal Framework
- **Consent:** Purpose-specific informed consent under Colombian Law 1581 of 2012.
- **Identity Isolation:** Direct participant identity is stored in an encrypted vault; the corpus registry operates exclusively with pseudonymous identifiers.
- **Withdrawal:** Immediate revocation supported; retracted recordings are excluded from downstream releases.

## 4. Dataset Releases Derived
- `lsc-handshape-v1`: Isolated handshape classification.
- `lsc-isolated-signs-v1`: Isolated lexical sign recognition.
- `lsc-dynamic-signs-v1`: Dynamic trajectory sign recognition.
- `lsc-continuous-recognition-v1`: Continuous sequence recognition.
- `lsc-translation-v1`: Discourse-level translation into Spanish and English.
