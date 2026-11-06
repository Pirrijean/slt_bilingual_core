# Reporte de Validación y Pruebas Automatizadas

**Proyecto:** SLT Bilingual Core  
**Fecha de validación:** Noviembre 2026  
**Resultado Global:** 100% Superado (33/33 pruebas unitarias y de integración)

---

## 1. Resumen de Ejecución de Pruebas

```
tests/test_audio.py::test_speech_engine_lifecycle PASSED                 [  3%]
tests/test_audio.py::test_speech_multiple_consecutive PASSED             [  6%]
tests/test_desktop_adapters.py::test_translation_adapter PASSED          [  9%]
tests/test_desktop_adapters.py::test_recognition_adapter_contract PASSED [ 12%]
tests/test_drawing.py::test_draw_hand_landmarks_empty PASSED             [ 15%]
tests/test_drawing.py::test_draw_hand_landmarks_renders_overlay PASSED   [ 18%]
tests/test_hand_landmarker.py::test_hand_observation_dataclass PASSED    [ 21%]
tests/test_hand_landmarker.py::test_slt_hand_landmarker_lifecycle_and_monotonicity PASSED [ 24%]
tests/test_integration.py::test_full_pipeline_flow PASSED                [ 27%]
tests/test_interaction.py::test_interaction_engine_initial_state PASSED  [ 30%]
tests/test_interaction.py::test_interaction_tracking_and_candidate PASSED [ 33%]
tests/test_interaction.py::test_interaction_confirmation_and_timeline PASSED [ 36%]
tests/test_interaction.py::test_timeline_operations PASSED               [ 39%]
tests/test_interaction.py::test_custom_video_timestamp_tracking PASSED   [ 42%]
tests/test_language.py::test_lexicon_schema_and_classes PASSED           [ 45%]
tests/test_language.py::test_semantic_frame_parsing PASSED               [ 48%]
tests/test_language.py::test_greeting_and_courtesy_translation PASSED    [ 51%]
tests/test_language.py::test_pro_drop_and_english_subject PASSED         [ 54%]
tests/test_language.py::test_dactilology_fingerspelling_assembly PASSED  [ 57%]
tests/test_language.py::test_accumulator_operations PASSED               [ 60%]
tests/test_language.py::test_srt_generation_and_formatting PASSED        [ 63%]
tests/test_recognition.py::test_joint_angle_calculation PASSED           [ 66%]
tests/test_recognition.py::test_feature_dimension_and_no_nan PASSED      [ 69%]
tests/test_recognition.py::test_translation_invariance PASSED            [ 72%]
tests/test_recognition.py::test_scale_invariance PASSED                  [ 75%]
tests/test_recognition.py::test_classifier_prediction_and_rejection PASSED [ 78%]
tests/test_subtitles.py::test_format_timestamp PASSED                    [ 81%]
tests/test_subtitles.py::test_create_srt_content_sequential_indexing PASSED [ 84%]
tests/test_subtitles.py::test_export_srt_file PASSED                     [ 87%]
tests/test_subtitles.py::test_create_transcription_txt PASSED            [ 90%]
tests/test_ui.py::test_main_window_initial_state PASSED                  [ 93%]
tests/test_ui.py::test_main_window_sign_confirmation_flow PASSED         [ 96%]
tests/test_ui.py::test_main_window_mode_and_telemetry PASSED             [100%]

============================= 33 passed in 7.07s ==============================
```

---

## 2. Cobertura de Criterios de Aceptación

1. **Reconocimiento con Cámara Limpia (Modo A) y Demostración (Modo B):**
   - Verificado en `tests/test_drawing.py` y `tests/test_ui.py`.
   - La pantalla permanece limpia sin overlays por defecto.
   - La activación del interruptor renderiza la estructura anatómica en Teal `#42BFB0` sin modificar los fotogramas en memoria.
2. **Percepción en `RunningMode.VIDEO`:**
   - Verificado en `tests/test_hand_landmarker.py`.
   - Se imponen marcas de tiempo monótonamente crecientes requeridas por MediaPipe C++.
3. **Traducción Bilingüe Simultánea:**
   - Verificado en `tests/test_desktop_adapters.py` y `tests/test_language.py`.
   - Emite simultáneamente oraciones completas y correctas en español e inglés respetando pro-drop y pronombres explícitos.
4. **Síntesis de Voz SAPI5 Asíncrona:**
   - Verificado en `tests/test_audio.py`.
   - La reproducción en cola desacoplada no congela el hilo de la interfaz ni genera contención de bloqueo.
5. **Generación de Subtítulos Estándar SRT:**
   - Verificado en `tests/test_subtitles.py`.
   - Bloques con índices secuenciales 1-based, marcas de tiempo milimétricas y codificación UTF-8 sin errores de formato.
6. **Interfaz de Usuario y Manejo de Errores:**
   - Verificado en `tests/test_ui.py`.
   - Operaciones de confirmación de seña, deshacer última seña, limpiar oraciones y actualización de telemetría Cleanmeter verificadas en modo headless.
