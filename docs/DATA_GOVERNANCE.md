# SLT Data Governance & Ethical Acquisition Framework

**Versión:** 1.0.0 (Fase 0 - Fundacional)  
**Alcance:** Procedencia, privacidad de participantes, protocolos de captura y partición estratificada.

---

## 1. Principios de Gobernanza de Datos

1. **Consentimiento Informado y Privacidad:** Las grabaciones de personas señantes contienen información biométrica y fisionómica. Ninguna captura puede realizarse sin consentimiento explícito, y los datos personales deben estar pseudonimizados desde su origen.
2. **Representatividad y Co-creación:** El vocabulario y las grabaciones de referencia deben validarse con personas sordas nativas o competentes de la comunidad lingüística de cada país.
3. **No Contaminación de Datos:** Prohibido mezclar muestras de diferentes lenguas de señas como si fueran intercambiables.

---

## 2. Esquema Metadato por Muestra

Cada muestra registrada para entrenamiento o evaluación debe contener los siguientes metadatos verificables:

```json
{
  "sample_id": "LSC-P04-S02-0045",
  "profile_id": "lsc",
  "sign_id": "AGUA",
  "participant_id": "PARTICIPANT_04",
  "session_id": "SESSION_02",
  "dominant_hand": "right",
  "recording_condition": {
    "camera_model": "Logitech C920",
    "resolution": [1920, 1080],
    "native_fps": 30.0,
    "lighting": "indoor_diffuse",
    "background": "uniform_neutral"
  },
  "timestamp_recorded_utc": "2026-11-06T05:00:00Z",
  "linguistic_validator_id": "VALIDATOR_CERT_01"
}
```

---

## 3. Protocolo de Partición Estratificada

### Regla Fundamental contra el Data Leakage
**La partición entre conjunto de entrenamiento, validación y prueba NUNCA debe realizarse por fotogramas aleatorios**.

- **Partición por Personas (Leave-One-Participant-Out o k-Fold por Sujetos):** Todas las grabaciones de un participante específico deben pertenecer exclusivamente al conjunto de entrenamiento o al de prueba.
- Esto garantiza que el modelo aprenda la invariancia cinemática de la seña y no la apariencia física, tamaño o velocidad particular de un individuo.

---

## 4. Política de Almacenamiento y Protección

- `data/raw/` y `data/private/`: Grabaciones completas de video con rostros identificables. **Estrictamente ignoradas por Git (`.gitignore`)** y almacenadas bajo cifrado local.
- `data/samples/` / `models/`: Archivos procesados de landmarks o tensores numéricos pseudonimizados aptos para reproducibilidad de entrenamiento.
