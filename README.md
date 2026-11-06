# SLT Bilingual Core

> **Communication Workspace · Video en Tiempo Real → Sign Timeline → Subtítulos Bilingües + Voz Asíncrona (ES/EN)**  
> *Filosofía: Construir sobre hombros de gigantes, pero desarrollar una solución propia.*  
> Desarrollado con **Python 3.12**, **MediaPipe Tasks**, **NumPy** y **PySide6**.

[![SLT Automated Tests](https://github.com/Pirrijean/slt_bilingual_core/actions/workflows/tests.yml/badge.svg)](https://github.com/Pirrijean/slt_bilingual_core/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-teal.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)

---

## 1. Principio Rector y los 4 Pilares

**SLT Bilingual Core** no es un prototipo experimental ni un envoltorio genérico de librerías. Es un producto tecnológico propio diseñado para la comunicación fluida y accesible entre personas sordas o con dificultades del habla y oyentes.

El desarrollo se articula sobre **cuatro pilares inmutables**:

1. **Reconocimiento e Interacción Visual en Tiempo Real:**
   - Reconocimiento activo en segundo plano en todo momento.
   - **Modo A (Pantalla Limpia - Predeterminada):** Muestra el flujo de video original sin esqueletos ni marcadores superpuestos, priorizando una interacción natural y digna.
   - **Modo B (Modo Demostración):** Interruptor independiente que superpone la anatomía de las manos en Teal `#42BFB0`, articulaciones anti-aliased y badges de lateralidad.
2. **Traducción y Subtítulos Bilingües Simultáneos:**
   - Subtítulos de gran tamaño y legibilidad simultáneos en español e inglés.
   - Botón directo "Copiar traducción" al portapapeles.
   - Tira de historial cronológico con funciones "Deshacer" y "Limpiar".
   - Soporte para procesamiento de archivos de video locales (MP4, AVI, MOV) con exportación a subtítulos estándar `.srt` y reportes `.txt`.
3. **Comunicación Mediante Síntesis de Voz:**
   - Motor de voz multihilo no bloqueante mediante SAPI5 COM en Windows (`Helena` para español, `Zira` para inglés).
   - Selector de idioma de voz (Español, English, Ambos) y modo de voz automática opcional.
4. **Monitorización del Rendimiento (Cleanmeter Discreto):**
   - Telemetría en vivo: FPS, latencia de percepción en milisegundos, manos detectadas y estado del motor.
   - En procesamiento de video: barra de progreso, FPS de procesamiento y cálculo de tiempo restante (ETA).

---

## 2. Estructura del Proyecto

```text
slt_bilingual_core/
├── app.py                     # Punto de entrada de la aplicación de escritorio
├── src/
│   ├── slt_desktop/           # Capa de escritorio desacoplada (PySide6)
│   │   ├── hand_landmarker.py # MediaPipe HandLandmarker (RunningMode.VIDEO)
│   │   ├── drawing.py         # Visualización anatómica limpia (Modo B)
│   │   ├── vision_worker.py   # Hilo de captura QThread (Cámara / Video)
│   │   ├── recognition_adapter.py # Adaptador de clasificación 106-D + FSM
│   │   ├── translation_adapter.py # Adaptador lingüístico simultáneo (ES/EN)
│   │   ├── subtitles.py       # Generador y exportador de subtítulos SRT y TXT
│   │   ├── theme.py           # Tema oscuro minimalista y paleta de diseño
│   │   └── main_window.py     # Ventana principal del traductor de escritorio
│   └── slt/                   # Núcleo modular algorítmico
│       ├── recognition.py     # Extractor geométrico 106-D y clasificador k-NN
│       ├── interaction.py     # Máquina de estados finitos y SignEvent
│       ├── language.py        # SemanticFrame, lexicón bilingüe y realizadores
│       └── speech.py          # Síntesis de voz multihilo con COM SAPI5
├── config/
│   ├── lexicon.json           # Lexicón semántico bilingüe con 18 palabras léxicas
│   ├── classes.json           # 19 clases oficiales reconocidas
│   └── settings.json          # Parámetros de quórum y configuración de hardware
├── docs/
│   ├── CURRENT_STATE_REPORT.md# Informe técnico de auditoría y compatibilidad (Fase 0)
│   ├── ARCHITECTURE.md        # Especificación arquitectónica y los 4 pilares
│   ├── VALIDATION.md          # Reporte de validación con 33 pruebas automatizadas
│   ├── LICENSES.md            # Licencias de dependencias y atribuciones
│   └── DATASET.md             # Protocolo de adquisición de datos
├── models/
│   ├── hand_landmarker.task   # Modelo oficial MediaPipe Tasks Hand Landmarker
│   └── slt_model.npz          # Prototipos entrenados y parámetros de normalización
└── tests/
    ├── test_hand_landmarker.py# Pruebas del detector anatómico en modo VIDEO
    ├── test_drawing.py        # Pruebas de renderizado de esqueletos (Modo B)
    ├── test_subtitles.py      # Pruebas de generación y exportación SRT y TXT
    ├── test_desktop_adapters.py # Pruebas de contratos de los adaptadores
    ├── test_ui.py             # Pruebas del ciclo de vida y eventos de la GUI
    ├── test_recognition.py    # Pruebas de extracción 106-D e invariancia
    ├── test_interaction.py    # Pruebas de máquina de estados finitos
    ├── test_language.py       # Pruebas del motor lingüístico bilingüe
    ├── test_audio.py          # Pruebas de síntesis de voz asíncrona
    └── test_integration.py    # Pruebas integrales de flujo completo
```

---

## 3. Vocabulario Oficial Soportado (19 Clases)

| ID | Glosa | Categoría | Rol Sintáctico | Salida Español | Salida Inglés |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **0** | `_NADA_` | Control | Rejection | *(Reposo / Sin seña activa)* | *(Rest / No active sign)* |
| **1** | `HOLA` | Cortesía | Saludo | ¡Hola! | Hello! |
| **2** | `GRACIAS` | Cortesía | Agradecimiento | Muchas gracias. | Thank you very much. |
| **3** | `POR_FAVOR` | Cortesía | Petición | Por favor. | Please. |
| **4** | `SI` | Respuestas | Afirmación | Sí. | Yes. |
| **5** | `NO` | Respuestas | Negación | No. | No. |
| **6** | `AYUDA` | Necesidades | Emergencia | ¡Necesito ayuda! | I need help! |
| **7** | `AGUA` | Necesidades | Sustantivo | Agua, por favor. | Water, please. |
| **8** | `COMIDA` | Necesidades | Sustantivo | Comida, por favor. | Food, please. |
| **9** | `ESTAR_BIEN` | Respuestas | Predicado | Estoy bien. | I am fine. |
| **10** | `TE_QUIERO` | Expresiones | Predicado | Te quiero. | I love you. |
| **11** | `YO` | Gramática | Sujeto (1P) | yo (Soy yo.) | I (It is me.) |
| **12** | `TU` | Gramática | Sujeto (2P) | tú (¿Y tú?) | you (And you?) |
| **13** | `QUERER` | Gramática | Verbo | quiero / quieres | want / wants |
| **14** | `A` | Dactilológico | Carácter | Letra A | Letter A |
| **15** | `E` | Dactilológico | Carácter | Letra E | Letter E |
| **16** | `I` | Dactilológico | Carácter | Letra I | Letter I |
| **17** | `O` | Dactilológico | Carácter | Letra O | Letter O |
| **18** | `U` | Dactilológico | Carácter | Letra U | Letter U |

---

## 4. Instalación y Ejecución

### Requisitos Previos
- Windows 10 u 11 (64-bit)
- Python 3.12 (recomendado en entorno virtual `.venv`)
- Cámara web integrada o USB (para modo en vivo)

### Instalación Rápida
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

### Iniciar la Aplicación de Escritorio
```bash
python app.py
```
O directamente con el comando de consola registrado:
```bash
slt-desktop
```

---

## 5. Atajos de Teclado del Workspace

| Atajo | Acción | Descripción |
| :--- | :--- | :--- |
| `Espacio` | **Pronunciar** | Vocaliza la traducción actual usando la voz seleccionada (ES, EN o ambos). |
| `Ctrl + C` | **Copiar traducción** | Copia ambas oraciones traducidas al portapapeles del sistema. |
| `Ctrl + Z` | **Deshacer seña** | Elimina la última seña confirmada de la secuencia y actualiza la traducción. |
| `Escape` | **Limpiar todo** | Reinicia el buffer de señas, el timeline y las oraciones en pantalla. |

---

## 6. Pruebas Automatizadas

Para ejecutar la suite de 33 pruebas automatizadas con verificación unitaria y de integración:

```bash
pytest -v
```

Resultado verificado:
- **33/33 pruebas superadas (100% de éxito).**
- Cobertura matemática del extractor 106-D con invarianza exacta ante traslación y escala.
- Decodificación temporal en la máquina de estados e histéresis anti-rebote.
- Procesamiento de video offline con marcas de tiempo monótonas y exportación SRT.
- Concurrencia de audio desacoplada sin bloqueos de interfaz gráfica.

---

## 7. Licencia

Publicado bajo la licencia **MIT**. Consulta [LICENSES.md](docs/LICENSES.md) para más detalles.
