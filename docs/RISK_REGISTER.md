# SLT Risk Register & Mitigation Strategy

**Versión:** 1.0.0 (Fase 0 - Fundacional)  
**Alcance:** Matriz integral de riesgos técnicos, lingüísticos y de plataforma para SLT Bilingual Core.

---

## 1. Matriz de Riesgos Técnicos

| ID | Riesgo Identificado | Consecuencia | Probabilidad | Impacto | Responsable | Estado | Evidencia | Estrategia de Mitigación |
| :---: | :--- | :--- | :---: | :---: | :--- | :---: | :--- | :--- |
| **RSK-001** | **Dataset insuficiente o poco diverso** | Baja generalización en usuarios no vistos durante el entrenamiento. | **Alta** (fase inicial de adquisición) | **Crítico** | Equipo de Datos | Abierto | Modelos sobreajustados rinden mal con manos de diferente tamaño. | Protocolo de adquisición estratificado por participantes con métrica Leave-One-Participant-Out. |
| **RSK-002** | **Confusión o mezcla entre lenguas de señas (LSC vs ASL)** | Traducciones incoherentes o señas mal clasificadas. | **Media** (al expandir vocabulario) | **Crítico** | Equipo Lingüístico | Mitigado por diseño | LSC y ASL comparten algunas formas pero difieren radicalmente en significado. | Arquitectura de perfiles soberanos (`profiles/`) con aislamiento estricto en `PhraseBuffer`. |
| **RSK-003** | **Señas dinámicas evaluadas como estáticas** | Pérdida de trayectoria y deformación temporal del significado. | **Alta** (si solo se usan descriptores de un cuadro) | **Alto** | Equipo de Reconocimiento | Abierto | Señas con movimiento requieren series temporales $X \in \mathbb{R}^{T \times F}$. | Separación arquitectónica de `TemporalDecoder` para incorporar modelos de secuencia. |
| **RSK-004** | **Complejidad de señas bimanuales** | Tracking oclusión y fallo en señas que usan ambas manos. | **Media** | **Alto** | Equipo de Visión | Mitigado por contrato | Señas como "COMIDA" o "AYUDA" involucran dos manos en LSC. | Contratos `HandObservation` y `SignEvent` con soporte nativo de lateralidad múltiple. |
| **RSK-005** | **Falsas predicciones por gestos desconocidos** | La aplicación habla o subtitula cuando la persona solo descansaba la mano. | **Alta** (en uso no supervisado) | **Alto** | Equipo de Reconocimiento | Mitigado por diseño | Clasificadores sin umbral asignan siempre una clase forzada. | Mecanismo de rechazo calibrado (`ScoreSemantics`, umbral de distancia y estado `UNKNOWN`/`REST`). |
| **RSK-006** | **Ausencia de Wheel MediaPipe en macOS Intel** | Imposibilidad de instalar el backend estándar en equipos Mac Intel x86-64. | **Cierta (100%)** | **Medio** | Arquitecto de Plataforma | Abierto | MediaPipe 1.2.2 en PyPI no publica wheel para `macosx_10_x86_64`. | Abstracción de backend de percepción; provisión de compilación local o motor alternativo. |
| **RSK-007** | **Incompatibilidad de motores de voz entre SO** | SAPI5 falla en Linux/macOS o produce errores de inicialización COM. | **Cierta (100%)** si se llama directo | **Alto** | Arquitecto de Plataforma | Mitigado por diseño | SAPI5 es exclusivo de Windows Win32. | Abstracción `SpeechBackend` con adaptadores independientes (`windows_sapi`, `macos_native`, `linux_espeak`). |
| **RSK-008** | **Desincronización en videos con framerate variable (VFR)** | Subtítulos SRT desalineados con respecto a la seña real. | **Media** en videos de smartphone | **Medio** | Equipo de Visión | Mitigado por diseño | Usar solo $1/FPS$ acumula deriva temporal en VFR. | Lectura de marcas de presentación ($PTS \times time\_base$) mediante PyAV/FFmpeg. |
| **RSK-009** | **Latencia y jitter en hardware modesto** | Caída de FPS y congelamiento de la experiencia de usuario. | **Media** | **Alto** | Equipo de Rendimiento | Controlado | Inferencia pesada en el hilo de interfaz bloquea Qt. | Hilos dedicados `QThread` (`VisionWorker`) y presupuesto de inferencia < 33 ms por fotograma. |
| **RSK-010** | **Ambigüedad sintáctica en traducción** | Traducción palabra por palabra que resulta ininteligible en inglés o español. | **Media** | **Alto** | Equipo Lingüístico | Controlado | Las lenguas de señas no son español codificado con las manos. | Mapeo mediante `SemanticFrame` antes de la realización morfológica en `es-CO` y `en-US`. |
