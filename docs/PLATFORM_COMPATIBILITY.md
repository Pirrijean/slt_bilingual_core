# SLT Platform Compatibility Matrix & Abstraction Blueprint

**Versión:** 1.0.0 (Fase 0 - Fundacional)  
**Alcance:** Matriz de viabilidad técnica multiplataforma y directrices de abstracción.

---

## 1. Matriz de Compatibilidad de Sistemas y Arquitecturas

| Sistema Operativo | Arquitectura CPU | Estado de Soporte | Backend Cámara | Backend Audio | Disponibilidad MediaPipe 1.2.2 | Notas Técnicas |
| :--- | :--- | :---: | :--- | :--- | :---: | :--- |
| **Windows 10 / 11** | x86-64 (AMD64) | **Objetivo Oficial (Tier 1)** | MSMF / DirectShow | SAPI5 COM Dispatch | Sí (Wheel PyPI) | Plataforma de desarrollo principal. |
| **Windows 11** | ARM64 | **Objetivo Oficial (Tier 1)** | MSMF | SAPI5 COM Dispatch | Sí (Wheel PyPI) | Soporte nativo verificado. |
| **Linux (Ubuntu 22.04/24.04)** | x86-64 | **Objetivo Oficial (Tier 1)** | V4L2 (`cv2.CAP_V4L2`) | `espeak-ng` | Sí (Wheel PyPI) | Requiere GLIBC >= 2.35 y dependencias de X11/Wayland para Qt. |
| **Linux** | ARM64 (aarch64) | **Objetivo Oficial (Tier 2)** | V4L2 | `espeak-ng` | Sí (Wheel PyPI) | Sujeto a pruebas de hardware en dispositivos embebidos. |
| **macOS (Sonoma / Sequoia)** | Apple Silicon (ARM64) | **Objetivo Oficial (Tier 1)** | AVFoundation | `NSSpeechSynthesizer` / `say` | Sí (Wheel PyPI) | Excelente desempeño con aceleración CoreML/Metal en Qt. |
| **macOS (Monterey+)** | Intel (x86-64) | **Compatibilidad Pendiente** | AVFoundation | `NSSpeechSynthesizer` / `say` | **No disponible en PyPI** | No existe wheel oficial de MediaPipe 1.2.2 para Intel Mac. Se requerirá compilación desde fuentes o backend de percepción alternativo. |

---

## 2. Abstracción Obligatoria de Plataforma

Para evitar el acoplamiento a sistemas operativos específicos, ningún componente del núcleo (`slt_core`) ni de la lógica de negocio podrá invocar directamente constantes o librerías dependientes de la plataforma.

### Arquitectura de Abstracción (`src/slt/platform/`)
```
src/slt/platform/
├── __init__.py         # Fábrica y resolución dinámica de plataforma
├── capabilities.py     # Detección de aceleración por hardware, cámaras y audio
├── camera.py           # Abstracción de captura de fotogramas según SO
├── speech.py           # Abstracción de síntesis de voz (SAPI5, macOS native, espeak-ng)
└── paths.py            # Resolución de directorios de usuario, caché y modelos
```

### Regla de Codificación Innegociable
```python
# PROHIBIDO dentro del núcleo o adaptadores:
camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)

# PERMITIDO (desacoplado y multiplataforma):
camera = platform_camera.open_default()
```

---

## 3. Estrategia de Audio Multiplataforma

El subsistema de síntesis vocal se estructurará mediante una interfaz común (`SpeechBackend`) con adaptadores especializados:

```
speech/
├── base.py             # Protocolo SpeechBackend (enqueue, ready, close)
├── windows_sapi.py     # Despacho COM SAPI5 nativo (Helena / Zira)
├── macos_native.py     # Enlace a NSSpeechSynthesizer / comando say
└── linux_espeak.py     # Conector para espeak-ng / speech-dispatcher
```

La aplicación no dependerá directamente de ninguno de estos motores: el backend de la plataforma resolverá e instanciará la implementación disponible en tiempo de ejecución.
