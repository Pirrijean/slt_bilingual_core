# SLT Data Governance & Ethical Acquisition Framework
**SLT Bilingual Core — Colombian Sign Language (LSC)**  
**Version:** 2.0.0 (Phase 3A Hardened)  
**Legal Context:** Colombian Statutory Law 1581 of 2012 (Habeas Data) & Regulatory Decree 1377 of 2013  

---

## 1. Legal and Ethical Foundations

### 1.1 Classification of Biometric Personal Data
Under Articles 5 and 6 of Colombian Law 1581 of 2012, video recordings capturing human facial features, bodily motion, or voice constitute **Sensitive Personal Data** (*Datos Sensibles*). Processing such data is strictly prohibited unless:
1. The data subject grants explicit, informed, and unambiguous prior authorization.
2. The processing serves specific, clearly defined scientific, non-commercial, or commercial purposes.
3. The data subject is expressly informed that granting authorization for sensitive biometric data is voluntary.

### 1.2 Principle of Purpose Specification (*Principio de Finalidad*)
Authorization must be purpose-specific. Consent to participate in an academic laboratory experiment does not constitute authorization for:
- Derivative commercial machine learning training.
- Public redistribution of raw video recordings.
- Cross-border cloud data transfers without adequate safeguards.

In `slt_corpus.consent`, purpose authorization is granularly enforced through the `ConsentPurpose` enum:
- `RECORD_AND_STORE`
- `DERIVE_LANDMARKS`
- `INTERNAL_RESEARCH`
- `NONCOMMERCIAL_TRAINING`
- `COMMERCIAL_TRAINING`
- `SHARE_WITH_PARTNERS`
- `PUBLISH_RAW_VIDEO`
- `PUBLISH_DERIVED_DATA`

---

## 2. Pseudonymity & Identity Vault Separation

To minimize privacy risks, identity data is decoupled from corpus metadata:
1. **Corpus Metadata:** Contains only pseudonymous slugs (`signer_001`, `signer_002`), demographic brackets (e.g. `age_bracket: "20-30"`), and physiological variables (`dominant_hand: "right"`).
2. **Prohibited Keys:** The domain layer (`slt_corpus.domain.validate_no_direct_identifiers`) programmatically rejects metadata containing direct personal identifiers (`name`, `email`, `phone`, `cedula`, `documento`, `address`, etc.).
3. **Identity Vault:** The mapping connecting `signer_id` to signed physical/digital consent documents and real legal identities resides in an encrypted, isolated identity vault outside the corpus catalog and repository.

---

## 3. Revocation & Data Withdrawal Workflow

Under Article 8 of Law 1581 of 2012, participants hold the right to revoke consent and demand deletion of their personal data at any time (*Derecho de Supresión*):
1. **Revocation Invocation:** The participant's `ConsentRecord` is marked with `revoked_at_utc`.
2. **Immediate Pipeline Gating:** Any operation calling `require_consent()` immediately raises `ConsentDeniedError`.
3. **Downstream Asset Purge:** All derived assets (`Asset`) linked to the participant's recordings are flagged for deletion from future dataset releases.
4. **Release Manifest Archival:** Existing released models that have already ingested weights cannot undo past training mathematically, but no future release or active training pipeline may include the retracted recordings.

---

## 4. Quarantined External Datasets

Third-party scientific datasets (such as LSC50, LSC70, and LSC-54) are held under strict legal quarantine:
- Their published papers under Creative Commons licenses (e.g. CC BY-NC-ND 4.0 or CC-BY) do not automatically confer unrestricted rights to distribute raw biometric videos or train commercial systems.
- They are cataloged in `corpus/lsc/documentation/external_datasets.json` with status `quarantine_pending_review`.
- No `DatasetRelease` with scope `COMMERCIAL_TRAINING` can include quarantined data.
