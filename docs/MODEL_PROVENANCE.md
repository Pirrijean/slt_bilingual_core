# SLT Model Provenance, Supply Chain Security & Asset Verification

**Módulos:** `slt_core.perception.model_assets`, `models/mediapipe/`  
**Versión:** 2.0.0 (Fase 2A)  
**Alcance:** Trazabilidad criptográfica, verificación de integridad de modelos, esquema de manifiesto y seguridad de la cadena de suministro.

---

## 1. Principio de Seguridad: Integridad Criptográfica de Artefactos

En aplicaciones profesionales de visión por computador e inteligencia artificial, cargar archivos binarios pre-entrenados sin verificación previa constituye una vulnerabilidad crítica de seguridad (inyección de modelos modificados o corrupción silenciosa de pesos en disco).

En SLT:
> **Regla Inquebrantable:** Ningún modelo de percepción puede ser instanciado o cargado en memoria sin antes verificar su suma de comprobación criptográfica SHA-256 contra un manifiesto inmutable firmado en el repositorio.

---

## 2. Especificación del Modelo de Percepción de Manos

| Atributo | Valor Oficial Verificado |
| :--- | :--- |
| **Nombre del Artefacto** | `hand_landmarker.task` |
| **Arquitectura** | MediaPipe Tasks Hand Landmarker (TFLite Bundle) |
| **Proveedor** | Google AI Edge / MediaPipe |
| **URL Oficial de Descarga** | `https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task` |
| **Tamaño en Disco** | 7,819,105 bytes (~7.46 MB) |
| **Algoritmo de Hashing** | SHA-256 |
| **Hash SHA-256 Calculado** | `fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1` |
| **Licencia del Modelo** | Apache License 2.0 |

---

## 3. Esquema del Manifiesto de Activos (`manifest.json`)

Los modelos distribuidos o descargados localmente se acompañan de un archivo `manifest.json` en `models/mediapipe/manifest.json`:

```json
{
  "model_name": "MediaPipe Hand Landmarker",
  "version": "float16/1",
  "filename": "hand_landmarker.task",
  "sha256": "fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1",
  "size_bytes": 7819105,
  "source_url": "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task",
  "verified_at": "2026-11-06T00:27:00Z"
}
```

---

## 4. Procedimiento de Verificación en Tiempo de Ejecución

La función `verify_model_asset(model_path, manifest_path=None, expected_sha256=None)` ejecuta el siguiente protocolo estricto:

```
[Path al modelo]
       │
       ▼ ¿Existe el archivo en disco?
       ├── NO ──► Lanza ModelAssetError("Model file not found")
       │
       ▼ Calcula SHA-256 en bloques de 64 KB
       │
       ▼ ¿Se especificó manifest_path?
       ├── SÍ ──► Lee manifest.json, parsea y extrae campo "sha256"
       │
       ▼ ¿Se especificó expected_sha256 directo?
       ├── SÍ ──► Compara con hash esperado
       │
       ▼ Compara Hash Calculado vs Hash Esperado
       ├── DISCREPANCIA ──► Lanza ModelAssetError("SHA-256 mismatch: expected X, computed Y")
       │
       ▼ ÉXITO: Retorna hash verificado y permite instanciación
```

Cualquier discrepancia provoca la detención inmediata del proceso antes de invocar la librería de inferencia C++, asegurando reproducibilidad y protección frente a descargas truncadas o manipulaciones maliciosas.
