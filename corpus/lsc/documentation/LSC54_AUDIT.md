# LSC-54 Dataset Due Diligence & Technical Quarantine Audit
**Resource ID:** `LSC54`  
**Dataset Name:** LSC-54 Landmark-Based Colombian Sign Language Dataset  
**Audit Date:** 2026-11-06  
**Auditor:** SLT Bilingual Core Legal & Governance Engine  
**Status:** **QUARANTINE — PENDING FORMAL RIGHTS CLEARANCE**  

---

## 1. Bibliographic & Repository Provenance
- **Publication Title:** *Multimodal landmark dataset and recognition of Colombian Sign Language*
- **Publisher:** PubMed Central (PMC 2025) / Science Data Bank (SciDB)
- **PMC URL:** https://pmc.ncbi.nlm.nih.gov/articles/PMC12557509/
- **Repository URL:** https://www.scidb.cn/en/detail?dataSetId=0fa5acc6293543bba9a39a822988843e
- **Version:** Version 1 (Released 2025)

---

## 2. Legal & Licensing Analysis
- **Publication License:** Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0).
- **Explicit Data License:** Hosted separately on Science Data Bank (SciDB). Terms must be validated against SciDB user agreement.
- **Commercial Use Rights:** **NOT AUTHORIZED** (CC BY-NC explicitly prohibits commercial use).
- **Derivative Rights:** Permitted under CC BY-NC for research only, provided attribution is maintained and terms are identical.
- **Participant Biometric Consent:** 22 signers. Consent agreements authorized non-commercial research.
- **Redistribution Rights:** Non-commercial research dissemination only.

---

## 3. Technical Assessment & Compatibility
- **Modalities Documented:**
  - MediaPipe holistic landmarks (hands, face, pose)
  - Time series numerical coordinate sequences
  - 2,850 original videos
  - 128,250 augmented instances (45x expansion via temporal scaling and rotation)
- **Linguistic Coverage:** 54 categories spanning colors, numbers, and courtesy phrases.
- **Participants:** 22 participants.
- **Technical Critical Finding (Imputation):** The authors report applying forward imputation for frames where MediaPipe failed to detect hands. **These imputed values do not represent empirical visual observations** and would corrupt velocity/temporal dynamics if treated as ground-truth observations.
- **Technical Compatibility with SLT:** Coordinate format requires conversion; augmented instances must be quarantined to prevent leakage.

---

## 4. Audit Decision & Operational Constraints
- **Decision:** `quarantine_pending_review`.
- **Operational Constraint:** May be evaluated only as an experimental landmark benchmark. Imputed frames must be excluded or flagged. Strictly quarantined from production releases.
- **Institutional Contact:** Science Data Bank deposit custodians and corresponding authors.
