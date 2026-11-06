# SLT Bilingual Core

> **Communication Workspace · Video en Tiempo Real → Sign Timeline → Subtítulos Bilingües + Voz Asíncrona (ES/EN)**  
> *Filosofía: Construir sobre hombros de gigantes, pero desarrollar una solución propia.*  
> Desarrollado con **Python 3.12**, **MediaPipe Tasks**, **NumPy** y **PySide6**.

[![SLT Automated Tests](https://github.com/Pirrijean/slt_bilingual_core/actions/workflows/tests.yml/badge.svg)](https://github.com/Pirrijean/slt_bilingual_core/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-teal.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)

---

## 1. Principio Rector e Identidad

**SLT Bilingual Core** no es un prototipo experimental ni un envoltorio genérico de librerías. Es un producto tecnológico propio diseñado para la comunicación fluida y accesible entre personas sordas o con dificultades del habla y oyentes.

Diferenciamos explícitamente cuatro niveles en nuestra arquitectura:
1. **Tecnologías de Terceros:** Aprovechamos herramientas maduras y robustas: MediaPipe (percepción anatómica), OpenCV (captura y procesamiento de imagen), PySide6 (interfaz de escritorio) y NumPy (cálculo matricial numérico).
2. **Métodos Científicos:** Estudiamos fundamentos de HMI y visión artificial, adaptando conceptos como las transiciones de estado e histéresis del estudio *AutoNav* ([Scientific Reports 2024](https://doi.org/10.1038/s41598-024-80898-x), CC BY 4.0) a eventos lingüísticos discretos.
3. **Implementación Propia:** Escribimos nuestro propio extractor geométrico 106-D invariante, nuestra máquina de estados finitos (`InteractionState` y `SignEvent`), nuestro motor de representación semántica (`SemanticFrame`), realizadores gramaticales bilingües deterministas y motor de voz asíncrono en Windows SAPI5.
4. **Identidad del Producto (Communication Workspace):** Una experiencia de usuario centrada en la conversación humana, con una paleta sobria (*Graphite #101820*, *Slate #1B303B*, *Teal #42BFB0*, *Mist #ECF2F3*), un **Sign Timeline** interactivo y telemetría técnica discreta inspirada en *Cleanmeter*.

---

## 2. Arquitectura Compacta y Desacoplada

```text
slt_bilingual_core/
├── app.py                     # Punto de entrada de la aplicación
├── src/
│   └── slt/
│       ├── application.py     # Orquestación de ciclo de vida y señales
│       ├── capture.py         # Captura de video multihilo (OpenCV)
│       ├── perception.py      # Percepción anatómica y renderizado (MediaPipe Tasks)
│       ├── recognition.py     # Protocolo SignRecognizer, extractor 106-D y clasificador k-NN
│       ├── interaction.py     # Motor de interacción temporal, SignEvent y Sign Timeline
│       ├── language.py        # SemanticFrame, lexicón semántico versionado y realizadores ES/EN
│       ├── speech.py          # Síntesis de voz multihilo no bloqueante (SAPI5 nativo)
│       ├── ui/
│       │   ├── main_window.py # Ventana principal del Communication Workspace
│       │   ├── components.py  # PerceptionStage, SignTimelineWidget, SubtitlesCard, DiagnosticsBar
│       │   └── theme.py       # Paleta y hoja de estilos Qt (QSS)
│       └── utils/             # Rutas maestras y configuración de logging
├── config/
│   ├── lexicon.json           # Lexicón bilingüe estructurado con roles sintácticos y validación
│   ├── classes.json           # Registro oficial de las 19 clases soportadas
│   └── settings.json          # Configuración de hardware y parámetros de quórum
├── docs/
│   ├── ARCHITECTURE.md        # Especificación maestra de la arquitectura
│   ├── INTERACTION_SPEC.md    # Especificación de máquina de estados y eventos temporales
│   ├── RECOGNITION_SPEC.md    # Protocolo SignRecognizer y 3 representaciones geométricas
│   ├── LANGUAGE_SPEC.md       # SemanticFrame y reglas de realización bilingüe
│   ├── UI_UX_SPEC.md          # Especificación del sistema de diseño y Sign Timeline
│   ├── RESEARCH_LOG.md        # Registro cronológico de investigación científica
│   ├── TECHNOLOGY_PROVENANCE.md # Matriz de procedencia y propiedad intelectual
│   ├── LICENSES.md            # Registro de licencias de código abierto
│   └── DATASET.md             # Protocolo de adquisición y partición por participantes
├── scripts/
│   ├── capture.py             # Herramienta de captura interactiva de señas
│   ├── train.py               # Entrenamiento y empaquetado del modelo (slt_model.npz)
│   └── evaluate.py            # Evaluación con matriz de confusión y latencia
└── tests/
    ├── test_recognition.py    # Pruebas de extracción 106-D, invariancia y clasificador
    ├── test_interaction.py    # Pruebas de FSM, quórum, anti-rebote y timeline
    ├── test_language.py       # Pruebas de SemanticFrame, gramática SVO y dactilología
    ├── test_integration.py    # Flujo integral de extremo a extremo
    └── test_audio.py          # Pruebas del motor de síntesis de voz multihilo
```

---

## 3. Especificaciones de Ingeniería y Documentación Técnica

Para garantizar un desarrollo transparente, reproducible y riguroso, el repositorio incluye 5 contratos de diseño e ingeniería:

1. [**Architecture Blueprint**](docs/ARCHITECTURE.md): Comunicación desacoplada entre capas y flujo de eventos.
2. [**SLT Interaction Specification**](docs/INTERACTION_SPEC.md): Máquina de 5 estados (`IDLE`, `TRACKING`, `CANDIDATE`, `CONFIRMED`, `WAITING_RELEASE`) y contrato `SignEvent`.
3. [**Recognition Specification**](docs/RECOGNITION_SPEC.md): Protocolo `SignRecognizer`, extracción de 106 características geométricas y rechazo de reposo/desconocidos (`_NADA_`).
4. [**Language Specification**](docs/LANGUAGE_SPEC.md): Representación intermedia `SemanticFrame`, realizadores gramaticales con pro-drop en español y pronombres explícitos en inglés.
5. [**UI/UX Specification**](docs/UI_UX_SPEC.md): Niveles de interacción (Comunicación, Asistencia, Diagnóstico), sistema de diseño y Sign Timeline.

Documentación de atribución, licencias y reproducibilidad:
- [**Technology Provenance & IP Matrix**](docs/TECHNOLOGY_PROVENANCE.md): Qué tomamos de terceros y qué desarrollamos nosotros.
- [**Research Log**](docs/RESEARCH_LOG.md): Fundamentos científicos y referencias analizadas (AutoNav, OpusClip, Spinex, Cleanmeter).
- [**Dataset Specification**](docs/DATASET.md): Estructura del dataset y partición estratificada por participantes.
- [**Licenses**](docs/LICENSES.md): Licencias aplicables (MIT, Apache 2.0, LGPL v3, CC BY 4.0).

---

## 4. Vocabulario Soportado (19 Clases)

| ID | Glosa | Categoría | Rol Sintáctico | Salida Español (Texto y Voz) | Salida Inglés (Text & Speech) |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **0** | `_NADA_` | Estado | Rejection | *(Reposo / Sin seña activa)* | *(Rest / No active sign)* |
| **1** | `HOLA` | Cortesía | Discourse | ¡Hola! | Hello! |
| **2** | `GRACIAS` | Cortesía | Politeness | Muchas gracias. | Thank you very much. |
| **3** | `POR_FAVOR` | Cortesía | Politeness | Por favor. | Please. |
| **4** | `SI` | Respuestas | Discourse | Sí. | Yes. |
| **5** | `NO` | Respuestas | Discourse | No. | No. |
| **6** | `AYUDA` | Necesidades | Object/Verb | ¡Necesito ayuda! | I need help! |
| **7** | `AGUA` | Necesidades | Object | Agua, por favor. | Water, please. |
| **8** | `COMIDA` | Necesidades | Object | Comida, por favor. | Food, please. |
| **9** | `ESTAR_BIEN` | Respuestas | Predicate | Estoy bien. | I am fine. |
| **10** | `TE_QUIERO` | Expresiones | Predicate | Te quiero. | I love you. |
| **11** | `YO` | Gramática | Subject (1P) | yo (Soy yo.) | I (It is me.) |
| **12** | `TU` | Gramática | Subject (2P) | tú (¿Y tú?) | you (And you?) |
| **13** | `QUERER` | Gramática | Verb | quiero / quieres | want / wants |
| **14** | `A` | Dactilológico | Character | Letra A (ensamble dactilológico) | Letter A (fingerspelling) |
| **15** | `E` | Dactilológico | Character | Letra E (ensamble dactilológico) | Letter E (fingerspelling) |
| **16** | `I` | Dactilológico | Character | Letra I (ensamble dactilológico) | Letter I (fingerspelling) |
| **17** | `O` | Dactilológico | Character | Letra O (ensamble dactilológico) | Letter O (fingerspelling) |
| **18** | `U` | Dactilológico | Character | Letra U (ensamble dactilológico) | Letter U (fingerspelling) |

---

## 5. Instalación y Ejecución

### Requisitos Previos
- Windows 10/11 (64-bit)
- Python 3.12 (arquitectura x64)
- Cámara web integrada o USB

### Instalación Rápida
Ejecuta el script automatizado en la raíz del proyecto:
```cmd
install.bat
```

O instala manualmente en tu entorno virtual:
```bash
python -m venv .venv
source .venv/Scripts/activate  # En Linux: source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### Ejecutar la Aplicación
```bash
python app.py
```
O mediante el comando CLI registrado:
```bash
slt
```

---

## 6. Atajos de Teclado del Workspace

| Tecla / Atajo | Acción | Descripción |
| :--- | :--- | :--- |
| `Espacio` | **Pronunciar Frase** | Sintetiza en voz alta la traducción actual en el idioma seleccionado. |
| `Backspace` | **Deshacer Última Seña** | Elimina la última glosa registrada del buffer y actualiza la traducción. |
| `Ctrl + L` | **Limpiar Frase** | Vacía completamente el Sign Timeline y reinicia las tarjetas de traducción. |
| `F1` | **Guía de Señas** | Abre o cierra el cajón lateral con la descripción postural de las 19 señas. |
| `Ctrl + Q` | **Salir** | Cierra de manera limpia y segura todos los hilos de cámara y audio. |

---

## 7. Pruebas Automatizadas

La suite de pruebas automatizadas valida unitaria e integralmente todos los subsistemas del proyecto:

```bash
pytest -v
```

Todas las 18 pruebas se ejecutan en < 8 segundos con 100% de tasa de éxito:
- Invarianza matemática exacta a traslación y escala del extractor 106-D.
- Decodificación temporal y supresión de repeticiones en el motor de interacción.
- Validación de esquemas y concordancia bilingüe en el motor lingüístico.
- Concurrencia multihilo no bloqueante en la síntesis de voz.

---

## 8. Licencia y Créditos

Este proyecto está publicado bajo la licencia **MIT**. Consulta [LICENSES.md](docs/LICENSES.md) para detalles sobre dependencias de terceros y atribuciones científicas (AutoNav CC BY 4.0, MediaPipe Apache 2.0).
