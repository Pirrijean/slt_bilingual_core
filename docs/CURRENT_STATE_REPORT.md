# Informe Técnico de Auditoría y Compatibilidad (Fase 0)
**Proyecto:** SLT Bilingual Core  
**Fecha:** Noviembre 2026  
**Autor:** Antigravity / Pirrijean (`jp.ninor1@uniandes.edu.co`)  
**Versión de informe:** 1.0.0 (Fase 0 - Entrega 1)

---

## 1. Resumen Ejecutivo y Diagnóstico General

El proyecto **SLT Bilingual Core** tiene como objetivo proporcionar un sistema de traducción en tiempo real de lengua de señas a texto y voz en español e inglés, operable tanto con cámara web en vivo como mediante procesamiento de archivos de video locales, con generación de subtítulos en formato estándar `.srt` y transcripciones `.txt`.

Antes de realizar modificaciones en el código fuente, se ha ejecutado una auditoría integral estática y dinámica del repositorio, analizando la estructura de directorios, dependencias de entorno virtual, compatibilidad de dimensiones de modelos, divergencias en la taxonomía de clases, y el estado de la suite de pruebas automatizadas.

### Estado del Repositorio y Pruebas
- **Entorno de ejecución:** Windows 11 x64, Python 3.12.10 en `.venv`.
- **Librerías principales:** PySide6 6.12.0, MediaPipe 1.2.2, OpenCV 5.0.0, NumPy 2.5.4, comtypes 1.4.17.
- **Suite de pruebas existente (`pytest -v`):** 20/20 pruebas superadas (100% de éxito en audio, integración, máquina de estados temporal, lingüística y reconocimiento invariante).
- **Control de versiones:** Rama `main` limpia, sincronizada con el repositorio remoto `https://github.com/Pirrijean/slt_bilingual_core.git`.

---

## 2. Inventario de Componentes: Funcionales, Incompletos y Duplicados

| Componente / Archivo | Estado | Rol Arquitectónico | Observaciones / Acción |
| :--- | :--- | :--- | :--- |
| `src/slt_core.py` | Legacy / Referencia | Script monolítico v2 original (680 líneas) | Contiene la implementación histórica de captura, `TinyMLP` (78-D/1360-D), `Translator` y `Speaker`. **No debe sobreescribirse ni modificarse**; se mantiene como benchmark de referencia. |
| `src/slt/recognition.py` | **Funcional** | Extractor geométrico 106-D, clasificador k-NN ponderado por distancia, rechazo de gestos desconocidos, métricas y entrenamiento | Robusto, matemático, 100% probado en pruebas unitarias. |
| `src/slt/perception.py` | **Funcional** | Percepción anatómica con MediaPipe Tasks HandLandmarker | Opera actualmente en `RunningMode.IMAGE`. La especificación de escritorio requiere `RunningMode.VIDEO` (`detect_for_video`) con marcas de tiempo monótonas para procesamiento en streaming. |
| `src/slt/interaction.py` | **Funcional** | Máquina de estados finitos (IDLE, TRACKING, CANDIDATE, CONFIRMED, WAITING_RELEASE) | Maneja quórum temporal, emisión de `SignEvent` y timeline de señas. Soporta marcas de tiempo arbitrarias para análisis de video offline. |
| `src/slt/language.py` | **Funcional** | Motor semántico bilingüe (`BilingualTranslator`, `Lexicon`, `SemanticFrame`), generador SRT | Soporta pro-drop español, pronombres explícitos en inglés, interjecciones, cortesía y dactilología. |
| `src/slt/speech.py` | **Funcional** | Motor de síntesis de voz (`SpeechEngine`, `SpeechWorker`) | Implementa SAPI5 COM directo sin bloqueo (`Helena` para español, `Zira` para inglés) con hilo de trabajo desacoplado. |
| `src/slt/ui/` | **Funcional / Prototipo** | Interfaz gráfica PySide6 modular inicial | Contiene componentes (`PerceptionStage`, `LanguageOutputCard`, etc.). Debe integrarse formalmente en el paquete `src/slt_desktop/` con el diseño minimalista de 4 pilares. |
| `src/slt_desktop/` | **Pendiente** | Paquete de escritorio definitivo con adaptadores desacoplados | Requerido por la especificación: `hand_landmarker.py`, `drawing.py`, `vision_worker.py`, `main_window.py`, `theme.py`, `subtitles.py`, `recognition_adapter.py`, `translation_adapter.py`. |
| `_backup_original/` | Respaldo inmutable | Respaldo histórico del repositorio original | Inalterado y preservado. |

---

## 3. Discrepancia Crítica de Clases: Taxonomía Real (15 vs 18 vs 19 vs 20)

Uno de los hallazgos más relevantes de la auditoría es la presencia de múltiples conjuntos de clases según el nivel de abstracción del proyecto:

1. **Datos crudos originales (`data/seed_signs.csv` y `data/seed_signs.npz`):**
   - Contienen **15 clases**: `HOLA`, `GRACIAS`, `POR_FAVOR`, `SI`, `NO`, `AYUDA`, `AGUA`, `YO`, `TU`, `QUERER`, `A`, `E`, `I`, `O`, `U` (140 muestras por clase = 2100 muestras en total).
   - El vector de rasgos en `seed_signs.npz` es de **78 dimensiones**.
2. **Modelo entrenado (`models/slt_model.npz` y `config/classes.json`):**
   - Contiene **19 clases**:
     - 1 clase nula / reposo: `_NADA_`
     - 13 señas funcionales: `HOLA`, `GRACIAS`, `POR_FAVOR`, `SI`, `NO`, `AYUDA`, `AGUA`, `COMIDA`, `ESTAR_BIEN`, `TE_QUIERO`, `YO`, `TU`, `QUERER`
     - 5 vocales dactilológicas: `A`, `E`, `I`, `O`, `U`
     - Total: $1 + 13 + 5 = 19$ clases.
     - `X_train` tiene forma `(2660, 106)` ($19 \times 140 = 2660$ prototipos).
3. **Diccionario léxico (`config/lexicon.json`):**
   - Define **18 palabras léxicas**: las 13 señas funcionales + 5 vocales (la etiqueta de control `_NADA_` no es una palabra léxica, por lo que no forma parte del diccionario de salida).
4. **Discrepancia sobre la "clase 20" (`BANO` o `NECESITAR`):**
   - En algunas variantes de documentación se menciona la fórmula "14 señas funcionales + 5 vocales + 1 nula = 20 clases".
   - La auditoría sobre los artefactos binarios y de configuración demuestra que **`BANO` y `NECESITAR` no existen en `models/slt_model.npz` ni en `config/classes.json` ni en `config/lexicon.json`**.
   - **Conclusión técnica:** El modelo real entrenado y serializado soporta de manera nativa y verificada **19 clases**. Intentar clasificar hacia una clase 20 inexistente generaría desalineación con las dimensiones del modelo pre-entrenado. Los adaptadores de escritorio deben validar contra el vocabulario real de 19 clases.

---

## 4. Comparativa de Extractores y Dimensión de Características

Se identificaron tres extractores en el historial del repositorio:

| Descriptor | Dimensión | Naturaleza | Normalización | Invarianza |
| :--- | :--- | :--- | :--- | :--- |
| **Legacy `seed_signs.npz`** | 78-D | Estático mono-manual | Coordenadas 21x3 + aperturas | Parcial |
| **`slt_core.clip_features`** | 1360-D | Espacio-temporal bi-manual (8 ventanas de 170-D) | Tamaño de palma y trayectoria relativa | Alta en secuencias dinámicas |
| **`slt.recognition.extract_features`** | **106-D** | Estático geométrico mono-manual | Muñeca en origen (64-bit), escala por distancia muñeca-MCP medio ($L_9$) | **Total a traslación, escala y perspectiva** |

### Desglose analítico del vector de 106 dimensiones:
1. **Coordenadas 3D centradas y normalizadas (21 $\times$ 3):** 63 dimensiones.
2. **Ángulos de flexión articular (5 dedos $\times$ 3 articulaciones):** 15 dimensiones.
3. **Distancias euclidianas entre las 5 puntas de los dedos ($\binom{5}{2}$):** 10 dimensiones.
4. **Distancias euclidianas de cada punta a la muñeca:** 5 dimensiones.
5. **Vector normal unitario del plano palmar:** 3 dimensiones ($X, Y, Z$).
6. **Aperturas digitales (puntas a base MCP y puntas a nudillo central $L_9$):** 10 dimensiones.
**Total:** $63 + 15 + 10 + 5 + 3 + 10 = 106$ dimensiones.

### Compatibilidad con `models/slt_model.npz`:
El archivo `models/slt_model.npz` almacena:
- `X_train`: matriz de `(2660, 106)` float32.
- `y_train`: vector de `(2660,)` int64.
- `classes`: array de 19 strings.
- `mean`: vector de `(1, 106)` float32.
- `std`: vector de `(1, 106)` float32.

La compatibilidad entre el extractor geométrico de `src/slt/recognition.py` y `models/slt_model.npz` es **exacta (100%)**.

---

## 5. Incompatibilidades y Requisitos Técnicos para la Aplicación de Escritorio

1. **Modo de ejecución de MediaPipe HandLandmarker:**
   - La percepción en `src/slt/perception.py` fue concebida en `RunningMode.IMAGE`.
   - Para la aplicación de escritorio (`slt_desktop`), es imperativo utilizar `RunningMode.VIDEO` con llamadas a `detect_for_video(image, timestamp_ms)`, donde `timestamp_ms` sea monótonamente creciente en milisegundos.
   - En el análisis de video por archivo, se debe emplear el timestamp real de cada cuadro según los FPS del archivo de video, evitando el tiempo de reloj del sistema.
2. **Compatibilidad Qt6 / PySide6:**
   - `QShortcut` debe importarse desde `PySide6.QtGui` (en PySide2/Qt5 estaba en `QtWidgets`).
   - El procesamiento de cámara y video debe aislarse completamente en un `QThread` (`VisionWorker`) emitiendo `QImage` convertidos a espacio de color RGB para evitar congelamientos de la interfaz.
3. **No dependencia de librerías externas superfluas:**
   - No se debe importar `pandas`. Toda la manipulación de datos en producción y pruebas se realiza mediante `numpy`, `json` y el módulo estándar `csv`.
4. **Síntesis de voz no bloqueante:**
   - La comunicación por voz en Windows debe realizarse mediante COM SAPI5 (`Helena` y `Zira`) en un hilo de trabajo secundario para no introducir latencia en el renderizado de la interfaz gráfica.

---

## 6. Especificación de Interfaces y Contratos de Adaptación

Para garantizar una arquitectura desacoplada y no monolítica, se definen los siguientes contratos para los adaptadores de `src/slt_desktop/`:

### A. Contrato del Adaptador de Reconocimiento (`recognition_adapter.py`)
```python
class RecognitionBackend(Protocol):
    def process(
        self,
        observations: List[HandObservation],
        timestamp_ms: int
    ) -> List[Dict[str, Any]]:
        """
        Procesa las observaciones anatómicas del fotograma actual.
        Retorna una lista de eventos de señas confirmadas:
        [{
            "event_type": "SIGN_CONFIRMED",
            "label": str,
            "start_ms": int,
            "end_ms": int,
            "handedness": str,
            "stability": float
        }]
        """
        ...
```

### B. Contrato del Adaptador de Traducción (`translation_adapter.py`)
```python
class TranslationAdapter:
    def translate_glosses(self, glosses: List[str]) -> Dict[str, str]:
        """
        Transforma una secuencia de glosas en oraciones naturales simultáneas:
        Retorna {"es": "...", "en": "..."}
        """
        ...
```

---

## 7. Dictamen de Auditoría y Hoja de Ruta

- **Resultado de Fase 0:** APROBADO. El núcleo de algoritmos, modelos, métricas y datos se encuentra en un estado funcional, limpio y verificado.
- **Próximos pasos (Entregas 2 a 6):**
  1. **Entrega 2:** Creación del paquete `src/slt_desktop/` (`hand_landmarker.py`, `drawing.py`, `vision_worker.py`, `main_window.py`, `theme.py`, `subtitles.py`, adaptadores), actualización de `app.py` y `pyproject.toml`.
  2. **Entrega 3:** Conexión real del clasificador `SLTClassifier` y la máquina temporal en `recognition_adapter.py`.
  3. **Entrega 4:** Conexión de traducción simultánea (`translation_adapter.py`) y síntesis de voz SAPI5.
  4. **Entrega 5:** Modo de análisis de video de archivo local con exportación SRT estándar.
  5. **Entrega 6:** Pruebas unitarias de los nuevos módulos, suite de integración completa y documentación final.
