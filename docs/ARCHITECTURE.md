# SLT Bilingual Core: Architecture Blueprint

> **Philosophy**: *Construir sobre hombros de gigantes, pero desarrollar una solución propia.*

The SLT Bilingual Core is structured as an original **Human-Machine Communication Workspace** designed for deaf and hard-of-hearing individuals. Rather than a fragile collection of glued libraries or a naive frame-by-frame classifier, SLT is built on a clean, decoupled, event-driven architecture centered around 4 fundamental pillars.

---

## 1. The 4 Product Pillars

1. **Reconocimiento e Interacción Visual en Tiempo Real:**
   - La percepción y el reconocimiento operan de forma continua y transparente en segundo plano.
   - **Modo A (Pantalla limpia - Predeterminado):** Muestra el flujo de cámara o video original sin esqueletos ni marcadores superpuestos, priorizando la dignidad y naturalidad de la comunicación.
   - **Modo B (Modo demostración):** Interruptor independiente que superpone la visualización anatómica con la paleta de marca (Teal `#42BFB0`, articulaciones anti-aliased y badges de lateralidad).
2. **Traducción y Subtítulos Bilingües Simultáneos:**
   - Subtítulos de alta legibilidad en español e inglés en pantalla.
   - Botón de copiado al portapapeles y barra de historial de señas con deshacer y limpiar.
   - Procesamiento de archivos de video locales (MP4, AVI, MOV) con marcas de tiempo precisas y exportación a formatos estándar `.srt` y `.txt`.
3. **Comunicación Mediante Síntesis de Voz:**
   - Reproducción asíncrona no bloqueante mediante SAPI5 COM en Windows (`Helena` para español, `Zira` para inglés).
   - Selección de modo de voz (Español, English, Ambos) y opción de voz automática.
4. **Monitorización del Rendimiento (Cleanmeter Discreto):**
   - Barra inferior con telemetría en tiempo real: FPS, latencia de percepción en milisegundos, número de manos detectadas y estado del motor.
   - En modo de archivo de video: barra de progreso porcentual, FPS de procesamiento y tiempo estimado restante (ETA).

---

## 2. Diagrama Arquitectónico

```
+-------------------------------------------------------------------------+
|                           PERCEPTION LAYER                              |
|   OpenCV VideoCapture (Live / Video File) -> MediaPipe Tasks Landmarker |
|            (RunningMode.VIDEO con timestamps monótonamente crecientes)  |
+------------------------------------+------------------------------------+
                                     | HandObservation (21 3D Landmarks)
                                     v
+-------------------------------------------------------------------------+
|                      ADAPTADOR DE RECONOCIMIENTO                        |
|       slt_desktop.recognition_adapter.SLTRecognitionBackend             |
|   1. Extractor geométrico 106-D invariante (slt.recognition)            |
|   2. Clasificador k-NN ponderado con rechazo (slt.recognition)          |
|   3. Máquina de estados finitos y quórum temporal (slt.interaction)     |
+------------------------------------+------------------------------------+
                                     | Confirmed Sign Events
                                     v
+-------------------------------------------------------------------------+
|                       ADAPTADOR DE TRADUCCIÓN                           |
|       slt_desktop.translation_adapter.TranslationAdapter                |
|   BilingualTranslator + Lexicon + SemanticFrame (slt.language)          |
+------------------+---------------------------------+--------------------+
                   | Simultaneous (ES / EN)           | Sign Events List
                   v                                  v
+------------------------------------+   +--------------------------------+
|       SÍNTESIS DE VOZ ASÍNCRONA    |   |      SUBTÍTULOS Y EXPORTACIÓN  |
|   slt.speech.SpeechWorker          |   |  slt_desktop.subtitles         |
|   (SAPI5 COM Dispatch sin bloqueo) |   |  - create_srt_content (SRT)    |
|   - Helena (ES) / Zira (EN)        |   |  - create_transcription_txt    |
+------------------+-----------------+   +----------------+---------------+
                   | Audio Wave                           | .srt / .txt
                   v                                      v
+-------------------------------------------------------------------------+
|                     CAPA DE INTERFAZ DE USUARIO                         |
|       slt_desktop.main_window.MainWindow (PySide6)                      |
|   - Modo A (Limpio) / Modo B (Demostración)                             |
|   - Subtítulos bilingües simultáneos + Copiar traducción                |
|   - Tira cronológica de señas con Deshacer y Limpiar                    |
|   - Cleanmeter: FPS, latencia ms, manos, ETA                            |
+-------------------------------------------------------------------------+
```

---

## 3. Responsabilidades de Módulos

| Paquete / Módulo | Rol y Responsabilidad |
| :--- | :--- |
| `src/slt_desktop/hand_landmarker.py` | MediaPipe Tasks HandLandmarker en `RunningMode.VIDEO` garantizando marcas de tiempo monótonamente crecientes. Emite instancias de `HandObservation`. |
| `src/slt_desktop/drawing.py` | Renderizado anatómico minimalista de esqueletos y articulaciones en la paleta oficial (Teal `#42BFB0`, Mint `#2DD4BF`, Slate). Usado exclusivamente en Modo B. |
| `src/slt_desktop/recognition_adapter.py` | Implementa el protocolo `RecognitionBackend`, coordinando extracción 106-D, clasificación k-NN y confirmación de quórum temporal. |
| `src/slt_desktop/translation_adapter.py` | Conecta con el motor lingüístico `BilingualTranslator` produciendo oraciones naturales en español e inglés. |
| `src/slt_desktop/vision_worker.py` | Hilo de trabajo (`QThread`) para captura continua (cámara o archivo) sin bloquear la interfaz gráfica. Emite `QImage` y telemetría. |
| `src/slt_desktop/subtitles.py` | Formateo estricto de subtítulos SubRip `.srt` (índices 1-based, marcas de tiempo `HH:MM:SS,mmm`) y reportes estructurados de transcripción `.txt`. |
| `src/slt_desktop/theme.py` | Estilos oscuros (`DARK_THEME`), tipografía de alta legibilidad y jerarquía visual profesional. |
| `src/slt_desktop/main_window.py` | Ventana principal que unifica los 4 pilares en una experiencia minimalista y accesible. |
| `src/slt/recognition.py` | Núcleo matemático de extracción 106-D, clasificador k-NN, rechazo de gestos desconocidos y métricas de evaluación. |
| `src/slt/language.py` | Semántica intermedia (`SemanticFrame`), manejo de sujeto pro-drop en español, pronombres explícitos en inglés y deletreo dactilológico. |
| `src/slt/speech.py` | Hilo de síntesis de voz con despacho COM SAPI5 desacoplado. |
| `app.py` | Punto de entrada principal que inicializa `slt_desktop.main_window.main()`. |

---

## 4. Invarianza Matemática y Percepción Robusta

- **Vector de 106 dimensiones:**
  - 63 coordenadas normalizadas centrando la muñeca en $(0,0,0)$ en 64 bits y escalando por la longitud palmar hacia el nudillo central ($L_9$).
  - 15 ángulos de flexión articular en radianes.
  - 10 distancias interdigitales entre las 5 puntas de los dedos.
  - 5 distancias punta-muñeca.
  - 3 componentes del vector normal al plano palmar.
  - 10 aperturas digitales relativas.
  - **Invarianza matemática probada:** Total ante traslación 3D, escala métrica y rotación en perspectiva.
