# SLT Bilingual Core

> **Traductor de Lengua de Señas en Tiempo Real (Video → Subtítulos Bilingües + Voz Asíncrona en Español e Inglés)**  
> Desarrollado con **Python 3.12**, **MediaPipe Tasks**, **NumPy** y **PySide6**.

[![SLT Automated Tests](https://github.com/Pirrijean/slt_bilingual_core/actions/workflows/tests.yml/badge.svg)](https://github.com/Pirrijean/slt_bilingual_core/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-teal.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)

---

## 1. Descripción General
**SLT Bilingual Core** es una aplicación de escritorio diseñada para cerrar la brecha de comunicación entre personas sordas o mudas y oyentes. Mediante visión artificial de alta precisión y un clasificador geométrico 3D propio en NumPy puro, el sistema captura las señas del usuario a través de una cámara web convencional, las decodifica con filtrado temporal anti-rebote, construye frases gramaticales coherentes de forma simultánea en **Español** e **Inglés**, y las pronuncia mediante síntesis de voz asíncrona sin congelar la interfaz ni los fotogramas del video.

---

## 2. Características Principales
- **Arquitectura Modular Desacoplada:** Visión artificial, extracción geométrica, clasificación, motor lingüístico, síntesis de voz e interfaz gráfica operan en módulos estrictamente independientes.
- **MediaPipe Tasks Moderno:** Migrado al runtime oficial `HandLandmarker` (`hand_landmarker.task`), reemplazando la API obsoleta `mp.solutions`.
- **Extractor Geométrico de 106 Dimensiones:** Invariante a traslación, escala y distancia a la cámara, combinando 63 coordenadas normalizadas, 15 ángulos de flexión articular, 10 distancias interdigitales, 5 distancias muñeca-puntas, vector normal 3D de la palma y 10 aperturas digitales.
- **Clasificador Propio en NumPy Puro (`slt_model.npz`):** Inferencia ultrarrápida en CPU (< 1 ms por muestra) con umbrales de rechazo de gestos desconocidos y reposo (`_NADA_`).
- **Validación Independiente:** Evaluado sobre datos de prueba de participantes no vistos durante el entrenamiento (**92.48% de Exactitud Balanceada** y **92.20% de Macro F1**).
- **Estabilidad Temporal y Anti-Rebote:** Filtro de mayoría por ventana deslizante que genera eventos discretos `SIGN_CONFIRMED` y `SIGN_RELEASED`, impidiendo repeticiones erráticas.
- **Motor Lingüístico Bilingüe:** Traduce secuencias de glosas a español e inglés, soportando concordancia verbo-sujeto, expresiones compuestas, sujeto implícito y ensamble automático de deletreo dactilológico.
- **Voz Asíncrona Robusta:** Síntesis nativa en Windows SAPI5 (`Microsoft Helena` para español y `Microsoft Zira` para inglés) con cola multihilo no bloqueante.
- **Interfaz Gráfica Minimalista y Accesible (PySide6):** Dashboard en modo oscuro con visualización de esqueleto anatómico, HUD de telemetría (FPS, latencia, número de manos), subtítulos legibles y guía visual de señas.

---

## 3. Vocabulario Soportado (19 Clases)

| ID | Seña / Glosa | Categoría | Salida Español (Texto y Voz) | Salida Inglés (Text & Speech) |
| :---: | :--- | :--- | :--- | :--- |
| **0** | `_NADA_` | Estado | *(Reposo / Ausencia / Rechazo)* | *(Rest / Unknown)* |
| **1** | `HOLA` | Cortesía | ¡Hola! | Hello! |
| **2** | `GRACIAS` | Cortesía | Muchas gracias. | Thank you very much. |
| **3** | `POR_FAVOR` | Cortesía | Por favor. | Please. |
| **4** | `SI` | Respuestas | Sí. | Yes. |
| **5** | `NO` | Respuestas | No. | No. |
| **6** | `AYUDA` | Necesidades | ¡Necesito ayuda! | I need help! |
| **7** | `AGUA` | Necesidades | Agua, por favor. | Water, please. |
| **8** | `COMIDA` | Necesidades | Comida, por favor. | Food, please. |
| **9** | `ESTAR_BIEN` | Respuestas | Estoy bien. | I am fine. |
| **10** | `TE_QUIERO` | Expresiones | Te quiero. | I love you. |
| **11** | `YO` | Gramática | yo (Soy yo.) | I (It is me.) |
| **12** | `TU` | Gramática | tú (¿Y tú?) | you (And you?) |
| **13** | `QUERER` | Gramática | quiero / quieres | want / wants |
| **14** | `A` | Dactilológico | Letra A (ensamble) | Letter A (assembly) |
| **15** | `E` | Dactilológico | Letra E (ensamble) | Letter E (assembly) |
| **16** | `I` | Dactilológico | Letra I (ensamble) | Letter I (assembly) |
| **17** | `O` | Dactilológico | Letra O (ensamble) | Letter O (assembly) |
| **18** | `U` | Dactilológico | Letra U (ensamble) | Letter U (assembly) |

---

## 4. Instalación Rápida

### Windows (Recomendado)
1. Clona el repositorio:
   ```bash
   git clone https://github.com/Pirrijean/slt_bilingual_core.git
   cd slt_bilingual_core
   ```
2. Ejecuta el instalador automático en 1 clic:
   ```cmd
   install.bat
   ```

### Linux / macOS
```bash
chmod +x install.sh
./install.sh
```

---

## 5. Ejecución de la Aplicación

Una vez completada la instalación, activa el entorno virtual e inicia la interfaz:

```bash
# Windows
.venv\Scripts\activate.bat
python app.py

# Linux / macOS
source .venv/bin/activate
python app.py
```

---

## 6. Atajos de Teclado
| Tecla | Acción |
| :--- | :--- |
| **F1** | Abrir / Ocultar Guía de Señas y Vocabulario |
| **F2** | Iniciar o Detener Cámara |
| **F3** | Pausar o Reanudar Detección en Vivo |
| **F4** / **Ctrl+L** | Limpiar Frase Actual y Subtítulos |
| **F5** | Pronunciar únicamente en Español |
| **F6** | Pronunciar únicamente en Inglés |
| **F7** | Pronunciar en Modo Bilingüe (Español + Inglés) |
| **Espacio** | Pronunciar frase según el selector activo |
| **Retroceso** | Deshacer la última seña confirmada |
| **Ctrl+Q** | Salir de la aplicación |

---

## 7. Pruebas Automatizadas

El proyecto incluye una suite de pruebas exhaustiva con **pytest**:

```bash
pytest -v
```

Módulos testeados:
- `tests/test_features.py`: Invarianza espacial, estabilidad numérica y dimensión 106-D.
- `tests/test_classifier.py`: Inferencia k-NN y rechazo de vectores fuera de distribución.
- `tests/test_translation.py`: Reglas sintácticas, concordancia sujeto-verbo y deletreo dactilológico.
- `tests/test_lexicon.py`: Integridad y cobertura de las 19 clases y guías.
- `tests/test_audio.py`: Síntesis asíncrona SAPI5 sin bloqueo de hilos.
- `tests/test_integration.py`: Flujo integral desde coordenadas anatómicas hasta audio y subtítulos.

---

## 8. Alcance y Límites del Sistema
Este sistema reconoce un vocabulario delimitado de 19 configuraciones manuales, expresiones y vocales dactilológicas. Las lenguas de señas (como la LSC, LSM o ASL) son idiomas visuales complejos con gramática espacial, expresiones faciales y componentes dinámicos. Este proyecto establece la base de ingeniería para traducción asistida, extensible hacia modelos dinámicos continuos.

---

## 9. Licencia
Este proyecto está bajo la licencia **MIT** - consulta el archivo [LICENSE](LICENSE) para más detalles.
