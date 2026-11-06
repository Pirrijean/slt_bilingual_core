# SLT Video Timing, PTS Presentation & Synchronization Architecture

**Módulos:** `slt_core.sources.video`, `slt_core.domain.FramePacket`  
**Versión:** 2.0.0 (Fase 2A)  
**Alcance:** Manejo determinista de tiempos de presentación (PTS), soporte para Variable Frame Rate (VFR) y aislamiento entre reloj monótono y tiempo de medio.

---

## 1. El Problema del Tiempo en la Percepción Visual

En aplicaciones de visión por computador ingenuas, es común ver que los fotogramas de un archivo de vídeo se procesan asumiendo un tiempo sintético basado en el índice del cuadro y un supuesto framerate constante:

$$t_{\text{ingenuo}}(k) = \frac{k}{\text{FPS}} \quad (\text{INCORRECTO en vídeos reales})$$

O peor aún, midiendo `time.monotonic()` mientras la CPU decodifica el archivo:

$$t_{\text{ingenuo}}(k) = \text{reloj del sistema durante el bucle} \quad (\text{FATAL para análisis offline})$$

### 1.1. Por qué falla la asunción de Framerate Constante (CFR)
Los vídeos grabados con teléfonos móviles modernos (iOS / Android) y cámaras web utilizan casi universalmente **Variable Frame Rate (VFR)** para optimizar la exposición lumínica y la tasa de bits. En un vídeo a nominalmente "30 FPS", la distancia temporal real entre fotogramas puede oscilar entre 16 ms y 45 ms.
Si se asume CFR:
- La velocidad cinemática calculada $\mathbf{v} = \Delta \mathbf{p} / \Delta t$ queda completamente falseada.
- Los subtítulos generados (SRT / WebVTT) se desincronizan gradualmente respecto al audio y al movimiento de las manos (deriva temporal acumulativa).

### 1.2. Por qué no se puede usar el reloj del sistema (`time.monotonic`) en archivos de vídeo
Si un vídeo de 10 segundos se decodifica en un procesador veloz en apenas 2 segundos, `time.monotonic()` registrará una duración de 2 segundos. Por el contrario, si la inferencia es pesada y toma 25 segundos, el reloj del sistema registrará 25 segundos.
- El reloj monótono del sistema mide la velocidad a la que la computadora procesa el vídeo, **NO** la posición temporal del contenido dentro de la grabación.
- Los subtítulos y las marcas de tiempo de las señas deben reflejar cuándo ocurrió el gesto en el vídeo original.

---

## 2. Especificación Formal de Marcas de Tiempo en SLT

En SLT se definen dos clases de marcas de tiempo en el contrato `FramePacket`:

| Campo | `timestamp_kind = "monotonic"` | `timestamp_kind = "presentation"` |
| :--- | :--- | :--- |
| **Origen** | Cámara en vivo (`CameraSource`) | Archivo de vídeo / Contenedor (`VideoSource`) |
| **Referencia** | Reloj de alta resolución del sistema (`time.monotonic_ns()`) | Presentation Timestamp (`PTS`) del flujo de vídeo |
| **Escala** | Nanosegundos absolutos de ejecución | Nanosegundos relativos al inicio de la reproducción ($0$ a duración) |
| **Comportamiento** | Transcurre a tiempo real (1 segundo por segundo) | Independiente de la velocidad de decodificación de la CPU |

---

## 3. Cálculo Exacto de PTS con PyAV / FFmpeg

Para archivos de vídeo, SLT utiliza la librería `av` (enlace nativo a FFmpeg libavformat y libavcodec).

### 3.1. Base de Tiempo del Flujo (`time_base`)
Cada flujo de vídeo en un contenedor multimedia posee una base de tiempo fraccionaria fundamental:

$$\text{time\_base} = \frac{\text{num}}{\text{den}}$$

Por ejemplo, en contenedores MP4/MPEG-4 AVC suele ser $\frac{1}{90000}$ o $\frac{1}{1000}$.

### 3.2. Marca de Presentación en Nanosegundos
Para cada fotograma decodificado con `frame.pts`:

$$t_{\text{ns}} = \left\lfloor \frac{\text{PTS} \times \text{num} \times 10^9}{\text{den}} \right\rfloor$$

Esta operación se ejecuta utilizando aritmética entera de 64 bits en Python (`presentation_timestamp_ns()`), eliminando por completo cualquier acumulación de error de redondeo de punto flotante.

### 3.3. Garantía de Monotonía Temporal Estricta
En contenedores con cuadros B (bidireccionales), el orden de decodificación (DTS) puede diferir del orden de presentación (PTS). `VideoSource` opera sobre el generador de fotogramas decodificados de PyAV (`container.decode(video=0)`), el cual entrega los cuadros reordenados en su secuencia natural de presentación.

`VideoSource` verifica explícitamente que:

$$t_{\text{ns}}(k) > t_{\text{ns}}(k-1)$$

Si un fotograma reporta un PTS nulo, base de tiempo inválida o no monótona, se emite una excepción formal `InvalidVideoTimestampError`, impidiendo que datos corruptos contaminen el pipeline.
