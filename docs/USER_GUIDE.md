# SLT Bilingual Core · Guía del Usuario (User Guide)

> **Aplicación de Traducción de Lengua de Señas en Tiempo Real**  
> *Cuatro Pilares: Reconocimiento Visual · Subtítulos Bilingües · Síntesis de Voz · Monitorización Discreta*

---

## 1. Modos de Visualización

El reconocimiento funciona **siempre de forma activa y continua**. La visualización anatómica es opcional y conmutable mediante un único botón en la barra superior:

### Modo A: Pantalla Limpia (Predeterminado)
- **Experiencia**: La imagen de la cámara se presenta limpia, sin esqueletos, puntos ni marcadores superpuestos.
- **Indicador**: Distintivo sutil en la esquina inferior:
  `● Reconocimiento activo · Cámara funcionando`
- **Uso ideal**: Conversación diaria, videollamadas o presentaciones donde el interlocutor solo necesita leer los subtítulos bilingües.

### Modo B: Visualización de Reconocimiento (Modo Demostración)
- **Activación**: Presiona el botón **"Visualización: DESACTIVADA"** en la barra superior (o el atajo `F2`). Cambiará a **"Visualización: ACTIVADA"**.
- **Elementos mostrados**:
  - 21 landmarks anatómicos 3D con líneas de articulación en color *Teal SLT (`#42BFB0`)*.
  - Puntas de los dedos destacadas con anillos de contraste.
  - Distintivo superior: `VISUALIZACIÓN ACTIVA · DEMO`.
  - Etiqueta de la seña activa detectada con porcentaje de confianza.
  - Estado de tracking manual y conteo de manos.
- **Importante**: Desactivar la visualización **NO detiene** el reconocimiento, la extracción geométrica ni la traducción.

---

## 2. Traducción Bilingüe Simultánea

Conforme realizas señas, el motor construye oraciones coherentes en tiempo real:

### A. Subtítulos en Vivo
- Tarjeta de alto contraste con subtítulo en **Español** e **Inglés**.
- **Copiar traducción**: Botón `📋 Copiar traducción` que copia ambas frases al portapapeles con confirmación visual.
- **Sign Timeline**: Tira horizontal con las señas confirmadas y su duración (ej. `YO · 0.8s`, `QUERER · 0.9s`, `AGUA · 1.1s`). Puedes hacer clic en la `✕` de cualquier chip para descartar una seña errónea.

### B. Traducción de Video Local (MP4 / AVI / MOV)
Cambia a la pestaña **`📁 Analizar Video Local`**:
1. Haz clic en **`📁 Seleccionar archivo...`** y elige tu video.
2. Presiona **`▶ Analizar Video`**.
3. El video se procesa a través del **mismo motor unificado de reconocimiento**.
4. Visualiza la barra de progreso con porcentaje, velocidad de procesamiento en FPS y tiempo restante estimado.
5. Al finalizar, obtén:
   - Marcas de tiempo de las señas identificadas (ej. `00:02 – 00:04 | YO · QUERER`).
   - Traducción española consolidada (`Español: Yo quiero agua.`).
   - Traducción inglesa consolidada (`English: I want water.`).
6. **Exportar Subtítulos (.srt)**: Genera un archivo estándar `.srt` con códigos de tiempo precisos para reproductores de video (VLC, YouTube, etc.).
7. **Exportar Transcripción (.txt)**: Genera un reporte detallado en texto plano.

---

## 3. Comunicación por Voz (Síntesis de Audio)

- **Selector de Idioma**:
  - `Voz: Ambos (ES + EN)`: Pronuncia primero la frase en español y a continuación la versión en inglés.
  - `Voz: Sólo Español`: Síntesis mediante voz nativa en español (`Microsoft Helena`).
  - `Voz: Only English`: Síntesis mediante voz nativa en inglés (`Microsoft Zira`).
- **Reproducción Automática**: Casilla `Reproducción automática de voz`. Al activarse, cada frase confirmada se pronuncia sin intervención manual.
- **Pronunciación Manual**: Presiona el botón `🗣️ Pronunciar ahora` o la barra espaciadora (`Espacio`).
- **Cola Segura**: La síntesis es multihilo y no bloquea la interfaz ni corta oraciones en curso.

---

## 4. Monitorización de Rendimiento (Cleanmeter Style)

En el pie de la ventana, una franja técnica discreta muestra la salud del sistema:
- **En cámara en vivo**: `CÁMARA · 30.0 FPS · 32.4 ms · 1 MANO · MODELO: SLT-v1.1.0 · MOTOR: ACTIVO`
- **En análisis de video**: `VIDEO LOCAL · 45.2 FPS PROC · 65% · 1 MANO · MODELO: SLT-v1.1.0 · MOTOR: ACTIVO`

---

## 5. Atajos de Teclado del Workspace

| Tecla / Atajo | Acción | Descripción |
| :--- | :--- | :--- |
| `Espacio` | **Pronunciar Frase** | Sintetiza en voz alta la traducción actual en el idioma configurado. |
| `Backspace` | **Deshacer Última Seña** | Elimina la última glosa registrada y recalcula la traducción. |
| `Ctrl + L` | **Limpiar Frase** | Vacía el timeline y reinicia las tarjetas de subtítulos. |
| `F1` | **Catálogo de Señas** | Abre o cierra el cajón lateral con la guía visual y postural de las 19 señas. |
| `F2` | **Alternar Visualización** | Cambia entre Pantalla Limpia (Modo A) y Visualización de Demostración (Modo B). |
| `Ctrl + Q` | **Salir** | Cierra de manera segura todos los hilos y sale de la aplicación. |
