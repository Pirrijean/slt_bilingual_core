# SLT Bilingual Core: Project Requirements Document (PRD)

**Versión:** 1.0.0 (Fase 0 - Fundacional)  
**Estado:** Aprobado para diseño e implementación  
**Alcance de la versión:** Núcleo desacoplado, independiente de GUI y motores pesados (`slt_core`).

---

## 1. Visión y Propósito del Producto

**SLT Bilingual Core** es una plataforma de software diseñada para posibilitar la comunicación interactiva y continua entre personas sordas o con dificultades del habla y oyentes. A diferencia de prototipos que clasifican gestos estáticos aislados cuadro a cuadro, SLT concibe el reconocimiento como un proceso continuo y temporal que transforma secuencias cinemáticas en representaciones semánticas y, en última instancia, en oraciones naturales en múltiples idiomas de salida.

---

## 2. Requisitos Funcionales (FR)

### 2.1. Arquitectura Multilingüe Desacoplada
- **FR-001 (Independencia de Lengua de Entrada):** El sistema debe tratar cada lengua de señas (ej. Lengua de Señas Colombiana - LSC, American Sign Language - ASL) como un perfil lingüístico soberano con vocabulario, modelo cinemático y gramática independientes.
- **FR-002 (Múltiples Idiomas de Salida):** Una seña o secuencia reconocida en una lengua de señas debe poder traducirse simultáneamente a uno o varios idiomas hablados y escritos (ej. `es-CO`, `en-US`), reutilizando una interfaz semántica común normalizada.
- **FR-003 (Aislamiento de Perfiles):** No se permite la mezcla de eventos de diferentes lenguas de señas dentro de un mismo acumulador de frase (`PhraseBuffer`).

### 2.2. Percepción y Procesamiento Temporal Continuo
- **FR-004 (Flujo de Percepción Desacoplado):** El motor debe recibir paquetes de fotogramas (`FramePacket`) procedentes de fuentes diversas (cámara web, video local, stream) y obtener observaciones anatómicas (`HandObservation`, `PerceptionFrame`) sin que la percepción dependa de la representación visual.
- **FR-005 (Decodificación Temporal Independiente):** El reconocimiento continuo debe realizarse mediante un componente decodificador temporal (`TemporalDecoder`) separado del clasificador estático de fotogramas, capaz de segmentar transiciones, calcular duraciones y emitir eventos confirmados (`SignEvent`).
- **FR-006 (Soporte Bimanual y Lateralidad):** Los contratos de percepción y eventos de señas deben soportar de forma nativa señas unimanuales (izquierda o derecha) y señas bimanuales simultáneas o alternadas.

### 2.3. Gestión de Frases y Buffer Lingüístico
- **FR-007 (Acumulación y Deshacer):** El sistema debe mantener una secuencia cronológica de señas confirmadas con soporte de descarte de duplicados, reversión de última seña (`undo`) y reinicio de contexto (`clear`).
- **FR-008 (Preservación de Marcas Temporales):** Cada seña confirmada debe registrar su intervalo de tiempo exacto (`start_ns` y `end_ns`) relativo al dominio temporal de su fuente de captura.

### 2.4. Síntesis y Salidas de Comunicación
- **FR-009 (Subtítulos Sincronizados):** Generación de subtítulos estándar en formato SubRip `.srt` con numeración secuencial continua y marcas de tiempo correlativas, así como reportes de texto estructurado `.txt`.
- **FR-010 (Síntesis de Voz Asíncrona):** Despacho de locución para las frases traducidas sin bloquear el hilo de procesamiento visual ni la interfaz de usuario.

---

## 3. Requisitos No Funcionales (NFR)

### 3.1. Arquitectura y Calidad de Código
- **NFR-001 (Independencia del Núcleo):** `slt_core` debe ser una biblioteca pura de Python sin dependencias obligatorias de MediaPipe, OpenCV, PySide6 o hardware de cámara para sus pruebas unitarias.
- **NFR-002 (Contratos Tipados y Validación Férrea):** Todos los objetos de intercambio de datos (`domain.py`) deben ser inmutables (`frozen=True`), con ranuras de memoria optimizadas (`slots=True`) y validación estricta en su inicialización (`__post_init__`).
- **NFR-003 (Determinismo Temporal):** Los timestamps deben expresarse en nanosegundos enteros (`int`) con monotonicidad estrictamente creciente por fuente.

### 3.2. Viabilidad y Portabilidad Multiplataforma
- **NFR-004 (Soporte de Sistemas Operativos):** El núcleo debe ser ejecutable e instalable en Windows 10/11 (x86-64 y ARM64), Linux (Ubuntu 22.04/24.04 x86-64 y ARM64) y macOS (Apple Silicon ARM64).
- **NFR-005 (Abstracción de Plataforma):** Se prohíbe el uso de APIs o constantes específicas de sistema operativo (como `cv2.CAP_DSHOW` o llamadas directas a SAPI5) dentro de los módulos centrales.
- **NFR-006 (Integración Continua Multiplataforma):** La suite de pruebas debe ejecutarse en pipelines automatizados de CI en matrices que cubran Windows, Linux y macOS bajo Python 3.12 y 3.13.

### 3.3. Rendimiento y Seguridad
- **NFR-007 (Latencia y Presupuesto Temporal):** El pipeline del núcleo (`CorePipeline`) debe procesar la transición de fotograma y verificación de contratos en menos de 1 milisegundo por cuadro.
- **NFR-008 (Prevención de Path Traversal):** La carga de perfiles y recursos lingüísticos debe sanitizar identificadores y rutas para impedir accesos no autorizados al sistema de archivos fuera del directorio de perfiles.
