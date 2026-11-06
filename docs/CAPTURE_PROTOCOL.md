# LSC Data Capture Protocol Specification
**SLT Bilingual Core — Colombian Sign Language**  
**Version:** 1.0.0 (Phase 3A)  
**Standard Setup:** Controlled Studio Environment  

---

## 1. Physical Environment & Framing

To guarantee reliable computer vision perception (MediaPipe landmark stability, minimal motion blur, unoccluded signing space):
1. **Background:** Solid, neutral, non-reflective background (neutral grey or dark matte blue). Avoid visual clutter, posters, or reflective glass.
2. **Lighting:** Diffuse three-point lighting (key, fill, and back lights) providing minimum 300 lux on the signer's upper torso and hands without harsh cast shadows.
3. **Framing & Angle:**
   - Signer seated or standing squarely facing the camera at a $0^\circ$ azimuth angle.
   - Camera at eye level.
   - Field of view encompasses head, full upper torso, shoulders, and signing space down to the navel, plus $20\text{ cm}$ lateral clearance on both sides.

---

## 2. Technical Recording Parameters

- **Resolution:** Full HD ($1920 \times 1080$) native sensor resolution.
- **Frame Rate:** Minimum $30.0\text{ fps}$ (strictly stable, no variable frame rate drops below $25\text{ fps}$). High-speed $60.0\text{ fps}$ preferred for fast dynamic signs.
- **Exposure / Shutter Speed:** High shutter speed ($\ge 1/120\text{ s}$) to minimize hand motion blur during fast articulatory strokes.
- **Audio:** Audio capture is disabled by default in sign acquisition protocols (`audio_enabled: false`) unless specifically authorized for Spanish mouthing / acoustic correlation research.
- **Container / Codec:** Standard MP4 / Matroska containers using H.264 / AVC or raw video streams without lossy temporal filtering.

---

## 3. Session Procedure & Integrity Checklist

1. **Pre-Session Verification:**
   - Verify participant registration in `CorpusCatalog` with a valid pseudonymous `signer_id`.
   - Verify active, unrevoked `ConsentRecord` granting `ConsentPurpose.RECORD_AND_STORE`.
2. **Camera Calibration:**
   - Verify aspect ratio (16:9), frame rate, and focus lock.
3. **Task Elicitation:**
   - Present natural elicited tasks (e.g. narratives, structured dialogue, cartoon descriptions).
   - Signers must never be forced to sign at unnatural rhythms.
4. **Post-Recording Ingestion:**
   - Video file immediately ingested via `slt_corpus.storage.ingest_video`.
   - Content-addressed SHA-256 computed and registered in `data/private/catalog.sqlite3`.
