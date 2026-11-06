# SLT Desktop: UI Specification & Design System

**Componente:** `src/slt_desktop/`  
**Framework:** PySide6 (Qt6 for Python)  
**Filosofía:** Minimalista, profesional, accesible y de alta legibilidad para personas sordas o con dificultades del habla.

---

## 1. Principios de Diseño

1. **La comunicación primero:** El objetivo central es la traducción y la dignidad del usuario, no convertir la ventana en un laboratorio de visión artificial o un editor de video.
2. **Reconocimiento siempre activo, visualización opcional:**
   - **Modo A (Pantalla Limpia - Predeterminada):** Muestra el flujo original de la cámara o video sin esqueletos, puntos ni cajas superpuestas.
   - **Modo B (Modo Demostración):** Interruptor independiente que superpone la estructura anatómica de 21 puntos y conexiones en la paleta de marca (Teal `#42BFB0` y Mint `#2DD4BF`).
3. **Subtítulos bilingües simultáneos de alto contraste:** Tipografía clara en español (prominente) e inglés (complementario), visible a distancia sin fatiga ocular.
4. **Telemetría discreta (Cleanmeter):** Diagnóstico de rendimiento en la franja inferior (FPS, latencia en milisegundos, manos detectadas y estado del motor).

---

## 2. Paleta de Color y Tema Oscuro (`theme.py`)

| Rol de Diseño | Color Hex | Color BGR (OpenCV) | Uso |
| :--- | :--- | :--- | :--- |
| **Fondo Principal** | `#101820` | `(32, 24, 16)` | Ventana principal y canvas de video |
| **Tarjetas y Paneles** | `#172631` | `(49, 38, 23)` | Tarjetas de subtítulos, cabecera y telemetría |
| **Bordes** | `#30434D` | `(77, 67, 48)` | Delimitadores de componentes |
| **Acento de Marca (Teal)** | `#42BFB0` | `(176, 191, 66)` | Huesos del esqueleto, botones primarios, títulos |
| **Acento Secundario (Mint)** | `#2DD4BF` | `(191, 212, 45)` | Puntas de los dedos, estado activo del motor |
| **Texto Primario** | `#FFFFFF` / `#EAF2F5`| `(245, 242, 234)` | Subtítulos en español, texto principal |
| **Texto Secundario** | `#CBD5E1` / `#8EA5AF`| `(175, 165, 142)` | Subtítulos en inglés, etiquetas auxiliares |
| **Alerta / Live Badge** | `#EF4444` / `#7F1D1D`| `(68, 68, 239)` | Indicador de sesión EN VIVO |

---

## 3. Disposición Espacial y Jerarquía

```
+-------------------------------------------------------------------------------------------------+
| [SLT BILINGUAL] [EN VIVO]           [ ] Demostración anatómica   Voz: [Ambos v] [ ] Voz auto    |
|                                                                 [Abrir Video...] [Cámara en Vivo]|
+-------------------------------------------------------------------------------------------------+
|                                                                                                 |
|                                                                                                 |
|                                        CANVAS DE VIDEO                                          |
|                         (Relación de aspecto preservada, fondo #101820)                         |
|                         Modo A: Cámara limpia / Modo B: Esqueletos Teal                         |
|                                                                                                 |
|                                                                                                 |
+-------------------------------------------------------------------------------------------------+
| TRADUCCIÓN BILINGÜE SIMULTÁNEA                                   [Pronunciar] [Copiar traducción]|
| ESPAÑOL :  Yo quiero agua, por favor.                                                           |
| ENGLISH :  I want water, please.                                                                |
+-------------------------------------------------------------------------------------------------+
| Historial: [YO] → [QUERER] → [AGUA]     [Deshacer] [Limpiar]   [Exportar SRT] [Exportar TXT]   |
+-------------------------------------------------------------------------------------------------+
| FPS: 30.0   Latencia: 14.5 ms   Manos: 1   [====================] ETA: 00:00   ● Motor activo   |
+-------------------------------------------------------------------------------------------------+
```

---

## 4. Controles y Atajos de Teclado

| Control | Atajo de Teclado | Función |
| :--- | :--- | :--- |
| **Pronunciar** | `Espacio` | Sintetiza en voz alta la traducción actual en el idioma configurado (ES, EN o ambos). |
| **Copiar traducción** | `Ctrl + C` | Copia al portapapeles ambas traducciones formateadas. |
| **Deshacer seña** | `Ctrl + Z` | Elimina la última seña confirmada del buffer y recalcula las oraciones. |
| **Limpiar todo** | `Escape` | Reinicia el acumulador de señas, el buffer lingüístico y la pantalla. |

---

## 5. Modos de Operación

### Modo Cámara en Vivo
- Captura por OpenCV en `VisionWorker` (hilo `QThread` no bloqueante).
- Inferencia MediaPipe Tasks en `RunningMode.VIDEO` con marcas de tiempo monótonamente crecientes.
- Confirmación de señas por quórum temporal y realizador lingüístico automático.
- Opción de voz automática al confirmar cada seña.

### Modo Archivo de Video Local
- Procesamiento mediante el **mismo motor** de reconocimiento anatómico y lingüístico.
- Marcas de tiempo exactas calculadas a partir de la tasa nativa de fotogramas del video.
- Barra de progreso porcentual y cálculo dinámico de ETA en la barra Cleanmeter.
- Generación de subtítulos estándar `.srt` (índices 1-based correlativos) y transcripciones detalladas `.txt`.
