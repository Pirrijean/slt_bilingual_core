# LSC70 Dataset Due Diligence & Technical Quarantine Audit
**Resource ID:** `LSC70`  
**Dataset Name:** Dynamic Colombian Sign Language Dataset (70 participants)  
**Audit Date:** 2026-11-06  
**Auditor:** SLT Bilingual Core Legal & Governance Engine  
**Status:** **QUARANTINE — PENDING FORMAL RIGHTS CLEARANCE**  

---

## 1. Bibliographic & Repository Provenance
- **Publication Title:** *A dataset for dynamic Colombian Sign Language recognition*
- **Publisher:** Data in Brief / PMC (2025)
- **PMC URL:** https://pmc.ncbi.nlm.nih.gov/articles/PMC11720433/
- **Repository URL:** https://data.mendeley.com/datasets/9ssyn8tff5/2 (Mendeley Data v2)
- **Version:** Version 2 (Published 2025)

---

## 2. Legal & Licensing Analysis
- **Publication License:** Creative Commons Attribution 4.0 International (CC-BY).
- **Explicit Data License:** Hosted on Mendeley Data. While the article indicates availability for scientific research, the exact terms of the repository deposit and the underlying consent agreements with the 70 participants require formal legal verification.
- **Commercial Use Rights:** **NOT CONFIRMED / NOT AUTHORIZED.** Prior to commercial deployment, explicit documentation verifying that participants waived commercial claims over biometric features is mandatory under Colombian Law 1581 of 2012.
- **Derivative Rights:** Requires verification against Mendeley terms.
- **Participant Biometric Consent:** 70 volunteers. Consent forms focused on scientific research publication.
- **Redistribution Rights:** Subject to repository review.

---

## 3. Technical Assessment & Compatibility
- **Modalities Documented:**
  - High-resolution dynamic sequences
  - Segmented sign image sequences (35,208 frames)
- **Linguistic Coverage:** 47 lexical signs in LSC.
- **Participants:** 70 signers (high inter-signer diversity).
- **Session / Signer Separation:** Feasible; frame sequences are indexed by volunteer ID.
- **Technical Compatibility with SLT:** Moderate. Images must be assembled into continuous video containers for full pipeline compatibility.

---

## 4. Audit Decision & Operational Constraints
- **Decision:** `quarantine_pending_review`.
- **Operational Constraint:** Permitted exclusively for inter-signer variance evaluation and anatomical benchmarking in non-commercial environments. Quarantined from all release packaging.
- **Institutional Contact:** Corresponding author listed on PMC publication.
