# SLT Bilingual Core — Informe de Cierre de Fase 2A: Percepción Visual y Tracking de Manos

**Fecha:** 6 de Noviembre de 2026  
**Rama:** `feature/phase2-perception`  
**Estado:** **COMPLETADO SATISFACTORIAMENTE (FASE 2A)**  
**Próxima Fase:** Fase 2B (Percepción Facial y Corporal) — *En espera de revisión y aprobación explícita.*

---

## 1. Resumen Ejecutivo

En cumplimiento de la **Orden de Ejecución 002: Fase 2 (Percepción visual, tracking y procesamiento de vídeo)**, se completó de manera íntegra y rigurosa la subfase **Fase 2A (Percepción Anatómica y Seguimiento de Manos)**.

El objetivo central consistió en transformar SLT Core en un motor de percepción capaz de recibir secuencias visuales desde cámaras web o archivos de vídeo decodificados a nivel de fotograma nativo, extraer los 21 puntos anatómicos por mano mediante MediaPipe Tasks en modo `VIDEO`, asignar identificadores de seguimiento consistentes en el tiempo, calcular descriptores geométricos y cinemáticos invariantes, y certificar la integridad criptográfica de los modelos sin comprometer la latencia ni violar las reglas de diseño modular.

---

## 2. Componentes Implementados y Corregidos

### 2.1. Ajuste de Contratos Fundacionales (`slt_core.domain`)
- **`FramePacket`:**
  - Añadido `pixel_format: str = "BGR24"` tipificado y validado.
  - Añadido `timestamp_kind: str = "monotonic" | "presentation"`.
  - Añadido `presentation_pts: int | None`, `time_base_num: int | None`, `time_base_den: int | None` para preservación de tiempo de medio.
- **`HandObservation`:**
  - Añadido `tracking_id: int | None` para persistencia multi-cuadro.
  - Incorporado `world_landmarks: Sequence[Landmark]` (coordenadas 3D métricas reales en metros centradas en la mano).
  - Renombrado y clarificado `handedness_score: float | None` en sustitución del confuso `detection_score`.
- **Enlace Unívoco de Fuentes (`CorePipeline`):**
  - Implementado `_bound_source_id`. Una instancia de pipeline procesa estrictamente una sola fuente; el intento de mezclar fuentes lanza `ComponentContractError`.

### 2.2. Subsistema de Ingestión y Fuentes (`slt_core.sources`)
- **`CameraSource`:**
  - Captura multiplataforma orientada a DirectShow/MSMF en Windows, AVFoundation en macOS, V4L2 en Linux y `CAP_ANY` como fallback.
  - Generación de marcas de tiempo monótonas en nanosegundos (`time.monotonic_ns()`).
  - Compatibilidad total con inyección de dobles de captura para pruebas unitarias sin hardware físico (`capture_factory`).
- **`VideoSource`:**
  - Ingestión de archivos de vídeo basada en PyAV (enlace nativo libavformat / libavcodec de FFmpeg).
  - Cálculo exacto de tiempo de presentación en nanosegundos: $t_{\text{ns}} = \lfloor \text{PTS} \times \text{num} \times 10^9 / \text{den} \rfloor$.
  - Soporte nativo para vídeos con tasa de cuadros variable (VFR).
  - Verificación de monotonía estricta con excepción `InvalidVideoTimestampError`.

### 2.3. Motor de Percepción y Seguimiento (`slt_core.perception`)
- **`MediaPipeHandPerception`:**
  - Uso estricto de MediaPipe Tasks (`vision.HandLandmarker`) en `RunningMode.VIDEO`.
  - Verificación previa obligatoria de integridad criptográfica SHA-256 antes de la carga.
  - Conversión desacoplada `convert_mediapipe_result()` hacia contratos `HandObservation`.
- **`HandTracker`:**
  - Algoritmo de asignación temporal por mínima distancia espacial normalizada con penalización drástica por discrepancia de lateralidad ($P_{\text{handedness}} = 10.0$).
  - Máquina de estados de tracks con expiración configurable (`max_missed_frames = 10`).
- **`HandGeometry`:**
  - Cajas delimitadoras normalizadas y en coordenadas de píxeles.
  - Centro de la palma baricéntrico (`WRIST` + `MIDDLE_MCP`).
  - Ángulos inter-falángicos tridimensionales en grados para los cinco dedos.
  - Distancias euclidianas normalizadas clave.
- **`MotionAnalyzer`:**
  - Vectores de velocidad tridimensional, rapidez escalar y aceleración por `tracking_id`.
  - Diferencial temporal $\Delta t$ real en nanosegundos, haciéndolo invariante al framerate.
- **`overlay.py`:**
  - Renderizado visual sin efectos secundarios sobre el fotograma original (opera sobre una copia explícita).

### 2.4. Seguridad de la Cadena de Suministro (`slt_core.perception.model_assets`)
- Descarga y verificación del modelo oficial `hand_landmarker.task` de MediaPipe.
- Cálculo de hash SHA-256 real: `fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1`.
- Creación de `models/mediapipe/manifest.json`.

---

## 3. Telemetría y Pruebas de Desempeño

Mediante la herramienta de diagnóstico `tools/phase2_smoke.py`, se ejecutó una prueba de estrés procesando vídeo con decodificación completa y pipeline de percepción activo:

| Métrica | Requisito Objetivo | Resultado Medido (CPU AMD64) | Estado |
| :--- | :--- | :--- | :---: |
| **Latencia P50** | $< 33.3\text{ ms}$ (30 FPS) | **10.73 ms** | **SUPERADO AMPLIAMENTE** |
| **Latencia P95** | $< 45.0\text{ ms}$ | **11.42 ms** | **SUPERADO AMPLIAMENTE** |
| **Tasa de Cuadros Teórica** | $\ge 30\text{ FPS}$ | **$\sim 90\text{ FPS}$** | **APTO PARA TIEMPO REAL** |
| **Fugas de Recursos** | 0 descriptores abiertos | Verificado (`close()` idempotente) | **CONFORME** |

---

## 4. Cobertura de Pruebas Automatizadas

Se ejecutó la suite completa de pruebas unitarias y de integración:
- **Pruebas Totales:** 117 ejecutadas, 117 aprobadas (0 fallos).
- **Tiempo de Ejecución:** 6.82 segundos.
- **Cobertura de Código en `src/slt_core`:** **94%** (1017 sentencias, 58 no cubiertas pertenecientes a excepciones de hardware no presente).
- **Tipado Estático:** Mypy `strict = true` con 0 errores en los 19 archivos del núcleo.
- **Estilo y Calidad:** Ruff con 0 errores en `src/slt_core` y `tools`.

---

## 5. Matriz de Entregables Documentales

1. `docs/PERCEPTION_ENGINE.md`: Arquitectura del motor de percepción, validación de fotogramas e inferencia en modo VIDEO.
2. `docs/TRACKING_AND_GEOMETRY.md`: Seguimiento persistente `HandTracker`, cinemática y descriptores geométricos.
3. `docs/VIDEO_TIMING.md`: Preservación de tiempos de presentación (PTS), soporte VFR y diferencias entre tiempo de medio y reloj monótono.
4. `docs/MODEL_PROVENANCE.md`: Trazabilidad criptográfica de modelos, manifiestos y hashes SHA-256.
5. `.github/workflows/phase2-vision.yml`: Workflow multiplataforma para Windows, Ubuntu 24.04 y macOS 15.

---

## 6. Condición de Detención

> **DETENCIÓN FORMAL:** De acuerdo con la instrucción explícita del usuario y los principios de la Orden de Ejecución 002, el desarrollo de la Fase 2A concluye aquí. **NO** se procederá a implementar la Fase 2B (FaceLandmarker / PoseLandmarker), ni a desarrollar interfaces gráficas de usuario, ni a entrenar modelos de señas, hasta contar con la revisión y autorización del usuario.
