# SLT Tracking & Hand Geometry Engine

**Módulos:** `slt_core.perception.tracking`, `slt_core.perception.geometry`, `slt_core.perception.motion`  
**Versión:** 2.0.0 (Fase 2A)  
**Alcance:** Seguimiento temporal multi-fotograma, asignación de identificadores únicos, extracción de descriptores morfológicos y análisis de movimiento.

---

## 1. Por qué MediaPipe no proporciona IDs persistentes

MediaPipe Tasks Hand Landmarker es un modelo de estimación anatómica basado en detección y ajuste de mallas cuadro a cuadro. Aunque internamente en modo `VIDEO` conserva un prior para orientar la caja de atención en el cuadro subsiguiente, su API pública **no expone un identificador temporal persistente**.

En particular:
- Si el usuario muestra la mano derecha y luego introduce la mano izquierda, el orden de las listas `hand_landmarks` puede cambiar arbitrariamente entre `[Right, Left]` y `[Left, Right]` entre fotogramas consecutivos.
- Si una mano queda brevemente ocluida por una fracción de segundo, la API no reasocia la identidad al reaparecer.

Por tanto, SLT incorpora su propio subsistema determinista de seguimiento: `HandTracker`.

---

## 2. Algoritmo de Seguimiento: `HandTracker`

`HandTracker` resuelve el problema de asociación temporal de datos mediante asignación por costo mínimo (Greedy / Hungarian nearest-neighbor):

### 2.1. Vector de Estado del Track
Cada mano en seguimiento almacena internamente:
- `tracking_id: int`: Identificador único y monotónicamente creciente asignado al iniciar la trayectoria.
- `(center_x, center_y): (float, float)`: Centro geométrico normalizado de la mano en el fotograma anterior (calculado como el punto medio entre la muñeca `0` y la articulación `MCP` del dedo medio `9`).
- `handedness: Handedness`: Lateralidad observada predominante.
- `missed_frames: int`: Contador de fotogramas transcurridos sin observaciones asociadas.
- `last_frame_index: int`: Último índice de fotograma en el que estuvo activa.

### 2.2. Función de Costo de Asociación
Para cada par compuesto por un track existente $i$ y una nueva observación $j$, el costo de emparejamiento se define como:

$$C_{i,j} = d_{\text{euclidean}}(\mathbf{c}_i, \mathbf{c}_j) + P_{\text{handedness}}$$

Donde:
- $d_{\text{euclidean}}(\mathbf{c}_i, \mathbf{c}_j) = \sqrt{(x_i - x_j)^2 + (y_i - y_j)^2}$ representa la proximidad espacial normalizada en el plano $[0, 1]$.
- $P_{\text{handedness}} = 0.0$ si las lateralidades coinciden (`LEFT` == `LEFT` o `RIGHT` == `RIGHT`), o si alguna es `UNKNOWN`.
- $P_{\text{handedness}} = 10.0$ si las lateralidades difieren explícitamente (`LEFT` vs `RIGHT`), impidiendo que una mano izquierda se asocie erróneamente con la trayectoria de una mano derecha cercana en cruces de manos.

### 2.3. Umbral de Asociación y Ciclo de Vida
1. **Asociación Exitosa:** Si $C_{i,j} \le \text{max\_distance}$ (por defecto $0.25$ en espacio normalizado), la observación $j$ se asigna al track $i$.
2. **Creación de Nuevos Tracks:** Cualquier observación sin asociar que exceda el umbral genera un nuevo `tracking_id`.
3. **Expiración de Tracks:** Si un track no recibe observaciones durante $\text{max\_missed\_frames}$ fotogramas (por defecto 10 fotogramas consecutivo), el track se descarta formalmente para evitar acumulación de memoria.
4. **Monotonía Temporal:** Si `HandTracker` recibe un `frame_index` menor o igual al último procesado, lanza una excepción `TrackingError` para garantizar coherencia causal.

---

## 3. Extracción de Descriptores Geométricos (`slt_core.perception.geometry`)

Para alimentar de manera estandarizada los modelos de clasificación de señas, el motor calcula la estructura `HandGeometry`:

### 3.1. Bounding Box Normalizada y Absoluta
A partir de los 21 puntos normalizados:
- $x_{\min} = \min(x_k)$, $y_{\min} = \min(y_k)$
- $x_{\max} = \max(x_k)$, $y_{\max} = \max(y_k)$
- $\text{width} = x_{\max} - x_{\min}$, $\text{height} = y_{\max} - y_{\min}$

Adicionalmente, se proyecta a coordenadas enteras de píxeles para el renderizado del overlay o recorte de imagen.

### 3.2. Centro de la Palma
Calculado como el baricentro medio entre la muñeca (`WRIST = 0`) y la base del dedo medio (`MIDDLE_FINGER_MCP = 9`):

$$\mathbf{p}_{\text{palm}} = \frac{\mathbf{p}_0 + \mathbf{p}_9}{2}$$

### 3.3. Ángulos Inter-falángicos
Para evaluar la flexión o extensión de cada dedo, se calcula el ángulo tridimensional entre los vectores formados por las articulaciones:

$$\theta = \arccos\left(\frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\| \|\mathbf{v}\|}\right) \times \frac{180^\circ}{\pi}$$

Se extraen ángulos para:
- Pulgar: Ángulo entre segmentos `(1, 2)` y `(3, 4)`.
- Índice: Ángulo entre segmentos `(5, 6)` y `(7, 8)`.
- Medio: Ángulo entre segmentos `(9, 10)` y `(11, 12)`.
- Anular: Ángulo entre segmentos `(13, 14)` y `(15, 16)`.
- Meñique: Ángulo entre segmentos `(17, 18)` y `(19, 20)`.

### 3.4. Distancias Euclidianas Clave
Distancias entre las puntas de los dedos y el centro de la palma o la punta del pulgar (por ejemplo, distancia `THUMB_TIP` a `INDEX_FINGER_TIP` para distinguir configuraciones de pinza como en la letra "O" o "F").

---

## 4. Análisis de Movimiento y Cinemática (`slt_core.perception.motion`)

Las señas dinámicas (por ejemplo, saludos, preguntas o verbos en LSC) requieren conocer no solo la forma estática de la mano, sino también su vector de velocidad y aceleración en el tiempo.

### 4.1. `MotionAnalyzer`
`MotionAnalyzer` mantiene el estado cinemático por cada `tracking_id` activo:
- Calcula el diferencial temporal $\Delta t = (t_k - t_{k-1}) \text{ s}$.
- Calcula el desplazamiento euclidiano del centro de la palma:

$$\mathbf{v} = \frac{\mathbf{p}_k - \mathbf{p}_{k-1}}{\Delta t} \quad \left[\frac{\text{unidades}}{\text{segundo}}\right]$$

- Rapidez escalar: $s = \|\mathbf{v}\|$.
- Aceleración: $\mathbf{a} = \frac{\mathbf{v}_k - \mathbf{v}_{k-1}}{\Delta t}$.

### 4.2. Invarianza a la Frecuencia de Muestreo
Al calcular las derivadas cinemáticas dividiendo por $\Delta t$ exacto en nanosegundos (obtenido directamente del `FramePacket`), los vectores de velocidad son cuantitativamente comparables tanto si la captura ocurre a 30 FPS, 60 FPS o con framerate variable (VFR).
