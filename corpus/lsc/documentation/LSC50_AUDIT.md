# LSC50 Dataset Due Diligence & Technical Quarantine Audit
**Resource ID:** `LSC50`  
**Dataset Name:** LSC50 Colombian Sign Language Dataset  
**Audit Date:** 2026-11-06  
**Auditor:** SLT Bilingual Core Legal & Governance Engine  
**Status:** **QUARANTINE — PENDING FORMAL RIGHTS CLEARANCE**  

---

## 1. Bibliographic & Repository Provenance
- **Publication Title:** *LSC50: A multimodal dataset for Colombian Sign Language recognition*
- **Publisher:** Nature Scientific Data (2024)
- **DOI / URL:** https://www.nature.com/articles/s41597-024-04172-5
- **Repository URL:** https://github.com/BiomecanicaUniandes/LSC50
- **Version:** 1.0 (Released 2024)
- **Institution:** Universidad de los Andes, Bogotá, Colombia (Laboratorio de Biomecánica)

---

## 2. Legal & Licensing Analysis
- **Publication License:** Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0).
- **Code Repository License:** MIT License (applies strictly to extraction scripts and repository code, NOT to video assets).
- **Explicit Data License:** Asset-level terms require institutional verification. The CC BY-NC-ND 4.0 license forbids commercial exploitation (`NC`) and distribution of altered/derived works (`ND`).
- **Commercial Use Rights:** **NOT AUTHORIZED.** Any commercial deployment or training of commercial recognition models is strictly prohibited under CC BY-NC-ND.
- **Derivative Rights:** **RESTRICTED.** Preprocessing, feature transformation, or spatial normalization cannot be distributed without explicit bilateral authorization.
- **Participant Biometric Consent:** Participants consented to academic biomechanical research; broad commercial waiver for facial/body media is not documented.
- **Redistribution Rights:** Non-derivative, non-commercial redistribution only.

---

## 3. Technical Assessment & Compatibility
- **Modalities Documented:**
  - Synchronized RGB video (4 viewpoints)
  - Depth video (Microsoft Kinect v2)
  - Infrared (IR) video
  - MediaPipe 3D Hand, Pose, and Face Landmarks
  - Wearable Inertial Measurement Unit (IMU) acceleration and angular velocity
- **Linguistic Coverage:** 50 isolated lexical signs.
- **Participants:** 5 deaf and hearing signers.
- **Total Samples:** 4,000 video instances.
- **Session / Signer Separation:** Feasible (participants P01–P05 documented).
- **Technical Compatibility with SLT:** High. MediaPipe landmarks align with SLT coordinate systems; RGB video decodable with PyAV.

---

## 4. Audit Decision & Operational Constraints
- **Decision:** `quarantine_pending_review`.
- **Operational Constraint:** LSC50 may be accessed locally exclusively as an academic baseline for sensor comparison and perception validation in isolated research branches. **It is strictly forbidden from being ingested into `data/releases/` for commercial scope or distributed with SLT binaries.**
- **Institutional Contact:** Universidad de los Andes, Departamento de Ingeniería Biomédica.
