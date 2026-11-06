# SLT Continuous Temporal Recognition Specification

**Versión:** 1.0.0 (Fase 0 - Fundacional)  
**Alcance:** Segmentación temporal, decodificación cinemática continua y gestión de relojes.

---

## 1. De la Postura Aislada al Reconocimiento Continuo

Un error frecuente en visión artificial aplicada a lengua de señas es suponer que una conversación en señas consiste en una sucesión de posturas estáticas fotografiadas fotograma a fotograma.

En la realidad lingüística:
1. Una seña posee una **fase de preparación**, una **fase de ejecución (núcleo)** y una **fase de retracción o transición (epéntesis de movimiento)**.
2. La velocidad de ejecución varía entre personas y contextos emocionales.
3. Existen señas bimanuales donde las manos realizan trayectorias complementarias o asimétricas.
4. Entre seña y seña ocurren movimientos de transición sin valor lingüístico intrínseco.

Por ello, el pipeline de SLT no entrega predicciones directas a la traducción: entrega **hipótesis de reconocimiento** a un **decodificador temporal** que emite eventos consolidados:

```
+-------------------------------------------------------------------------------+
|                            PIPELINE TEMPORAL CONTINUO                         |
|                                                                               |
| [FramePacket]                                                                 |
|   | (source_id, frame_index, timestamp_ns, image)                             |
|   v                                                                           |
| [PerceptionBackend]                                                           |
|   | (Landmarks 3D, lateralidad, score de presencia)                           |
|   v                                                                           |
| [PerceptionFrame]                                                             |
|   |                                                                           |
|   v                                                                           |
| [RecognitionBackend]                                                          |
|   | (Cálculo cinemático / espacial de candidatos)                             |
|   v                                                                           |
| [Sequence of RecognitionHypothesis]                                           |
|   |                                                                           |
|   v                                                                           |
| [TemporalDecoder] <--- (Ventana deslizante, histéresis, quórum, segmentación) |
|   |                                                                           |
|   v                                                                           |
| [SignEvent Stream]                                                            |
|   | (event_id, profile_id, sign_id, start_ns, end_ns, handedness, score)      |
|   v                                                                           |
| [PhraseBuffer]                                                                |
|   | (Conserva orden cronológico, evita duplicados, soporta undo/clear)        |
|   v                                                                           |
| [TranslationBackend]                                                          |
|   | (Produce TranslationOutput para los locales solicitados: es-CO, en-US)    |
+-------------------------------------------------------------------------------+
```

---

## 2. Definición y Reglas de los Relojes Temporales

Cada fuente de fotogramas mantiene un dominio temporal estrictamente independiente:

| Tipo de Fuente | Dominio del Reloj | Origen y Base Temporal | Regla de Monotonicidad |
| :--- | :--- | :--- | :--- |
| **Cámara en Vivo** | `time.monotonic_ns()` | Tiempo monótono del sistema en nanosegundos | $t_k > t_{k-1}$ de forma estricta. |
| **Archivo de Video** | Presentation Timestamp ($PTS \times time\_base$) | Base de tiempo del contenedor multimedia | $PTS_k > PTS_{k-1}$ según el flujo de decodificación. |

### Regla Fundamental de No Interferencia
Los relojes de diferentes fuentes **nunca deben compararse entre sí ni mezclarse en el mismo pipeline**. El `CorePipeline` gestiona y valida secuencias temporales de manera aislada por cada `source_id`.

---

## 3. Contrato y Validación de `SignEvent`

El evento de seña es la unidad atómica de intercambio entre el reconocimiento continuo y el motor lingüístico:

```python
@dataclass(frozen=True, slots=True)
class SignEvent:
    event_id: str
    profile_id: str
    sign_id: str
    start_ns: int
    end_ns: int
    handedness: tuple[Handedness, ...] = ()
    hand_tracking_ids: tuple[int, ...] = ()
    score: float | None = None
    score_semantics: ScoreSemantics | None = None
```

### Reglas de Integridad Temporal Férreas:
1. **$start\_ns \ge 0$ y $end\_ns \ge start\_ns$**: La duración jamás puede ser negativa.
2. **$end\_ns \le packet.timestamp\_ns$**: Ningún decodificador puede emitir un evento con una marca de tiempo futura al fotograma actual que se está procesando.
3. **Consistencia semántica del score**: Si existe `score`, debe especificarse su semántica (`CALIBRATED_PROBABILITY`, `UNCALIBRATED_SCORE` o `DISTANCE`). No se admiten probabilidades inventadas.
