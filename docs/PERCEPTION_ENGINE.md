# SLT Perception Engine Specification

**Módulo:** `slt_core.perception`  
**Versión:** 2.0.0 (Fase 2A)  
**Alcance:** Pipeline de percepción visual anatómica, ingestión de fotogramas, inferencia con MediaPipe Tasks y validación estructural.

---

## 1. Visión General de la Arquitectura

El motor de percepción de SLT es responsable de procesar flujos de imágenes provenientes de cámaras o contenedores de vídeo, detectar la presencia anatómica de manos humanas, normalizar sus coordenadas espaciales y proyectar los datos hacia las capas de seguimiento y geometría.

```
       [CameraSource / VideoSource]
                    │
                    ▼ FramePacket (BGR24, timestamp_ns, presentation_pts)
         [validate_bgr_frame()]
                    │
                    ▼ (Validación de memoria continua, 3 canales uint8)
     [MediaPipe Tasks HandLandmarker] (Modo VIDEO)
                    │
                    ▼ HandLandmarkerResult (21 landmarks por mano)
       [convert_mediapipe_result()]
                    │
                    ▼ Sequence[HandObservation]
              [HandTracker]
                    │
                    ▼ HandObservation con tracking_id persistente
             [MotionAnalyzer]
                    │
                    ▼ HandMotion (velocidad, aceleración, delta t)
            [PerceptionFrame]
```

---

## 2. MediaPipe Tasks Hand Landmarker en Modo VIDEO

### 2.1. Selección del Modelo
SLT emplea exclusivamente el modelo oficial `hand_landmarker.task` de MediaPipe Tasks Vision (`mediapipe.tasks.python.vision.HandLandmarker`). Se prohíbe taxativamente el uso de `gesture_recognizer.task` o de la API obsoleta `mp.solutions.hands`.

### 2.2. Modo de Ejecución: `RunningMode.VIDEO`
MediaPipe Tasks soporta tres modos de ejecución:
1. `IMAGE`: Inferencia aislada sobre imágenes estáticas (no conserva estado ni priors temporales).
2. `VIDEO`: Inferencia sobre secuencias de vídeo con marcas de tiempo monótonamente crecientes en milisegundos (`timestamp_ms`). Mantiene seguimiento temporal de las regiones de interés (ROI) y reduce sustancialmente el consumo de CPU/GPU al reutilizar priors de detección entre fotogramas.
3. `LIVE_STREAM`: Inferencia asíncrona mediante callback.

Para SLT, se seleccionó de manera determinista el modo `RunningMode.VIDEO` porque garantiza sincronía estricta con el bucle de procesamiento y soporta tanto captura de cámara en vivo como decodificación cuadro por cuadro de archivos de vídeo.

### 2.3. Restricción Temporal de MediaPipe Video Mode
En modo `VIDEO`, MediaPipe requiere de forma inviolable que cada llamada a `detect_for_video(image, timestamp_ms)` satisfaga:

$$t_{k+1} > t_k \quad (\text{en milisegundos})$$

Si dos fotogramas consecutivos reportan el mismo milisegundo (o un valor decreciente), MediaPipe lanza un error irrecuperable en el motor nativo C++. `MediaPipeHandPerception` previene activamente esta condición:
- Calcula `timestamp_ms = max(current_ms, last_ms + 1)` en caso de fluctuaciones menores.
- En caso de discontinuidades temporales o reinicio de fuente, se debe crear una nueva instancia del motor de percepción.

---

## 3. Coordenadas Anatómicas: Image vs World Landmarks

MediaPipe Hand Landmarker genera dos representaciones espaciales complementarias para cada mano detectada (21 puntos anatómicos, desde la muñeca `WRIST = 0` hasta la punta de los dedos `THUMB_TIP = 4`, `INDEX_FINGER_TIP = 8`, `MIDDLE_FINGER_TIP = 12`, `RING_FINGER_TIP = 16`, `PINKY_TIP = 20`):

### 3.1. Normalized Image Landmarks (`landmarks`)
- Coordenadas normalizadas en el plano de la imagen: $x, y \in [0.0, 1.0]$.
- $z$ representa la profundidad relativa respecto a la muñeca (escala similar a $x$).
- Son fundamentales para:
  - Dibujado del overlay visual sobre el fotograma original.
  - Cálculo de la caja delimitadora (Bounding Box) en coordenadas de pantalla.
  - Tracking en el plano de la cámara.

### 3.2. World 3D Landmarks (`world_landmarks`)
- Coordenadas métricas en el espacio euclidiano tridimensional real (en metros).
- Origen $(0,0,0)$ centrado en el baricentro geométrico de la mano.
- Invariantes a la posición de la mano en el cuadro de la cámara y a la distancia focal relativa.
- Son esenciales para:
  - Extracción de características geométricas invariantes a escala (ángulos inter-falángicos, distorsión de palma).
  - Reconocimiento de señas tridimensionales independientes del usuario.

---

## 4. Clasificación de Lateralidad y Puntuación

### 4.1. Semántica de `handedness`
MediaPipe entrega categorías de lateralidad asumidas desde la perspectiva del observador o del propio usuario dependiendo del modo de espejo:
- En SLT, `Handedness.LEFT` y `Handedness.RIGHT` se tipifican rigurosamente mediante el Enum nativo de `slt_core.domain.Handedness`.

### 4.2. Corrección de Semántica: `handedness_score` vs Detección
En versiones tempranas de especificación se asumía erróneamente que la puntuación de MediaPipe representaba la confianza de detección anatómica de la mano. En MediaPipe Tasks:
- La puntuación entregada es `category.score`, correspondiente a la **probabilidad condicional de lateralidad** (¿es mano izquierda o derecha?), **NO** a la presencia o confianza anatómica de la mano.
- En consecuencia, el contrato de `HandObservation` se tipificó de forma precisa como `handedness_score: float | None`, evitando falsas interpretaciones en el clasificador de señas.

---

## 5. Validación Rigurosa de Fotogramas (`validate_bgr_frame`)

Para garantizar robustez frente a corrupciones de buffer o entradas inválidas de cámara, todo fotograma entrante debe satisfacer las siguientes precondiciones antes de cualquier cómputo:

1. **Tipo de Objeto:** Debe ser una instancia de `numpy.ndarray`.
2. **Dimensionalidad:** Debe tener exactamente 3 dimensiones: $(H, W, C)$.
3. **Número de Canales:** $C = 3$ (formato de color BGR24 o RGB24).
4. **Dimensiones Espaciales:** $H > 0$ y $W > 0$.
5. **Tipo de Dato:** `dtype == np.uint8` (8 bits por canal sin signo).
6. **Contigüidad de Memoria:** `frame.flags["C_CONTIGUOUS"] == True`. En caso de slices de NumPy no continuos en memoria, se fuerza `np.ascontiguousarray()`.

Si alguna de estas condiciones no se cumple, se genera inmediatamente una excepción especializada `InvalidFrameError` antes de invocar los métodos nativos de C++.
