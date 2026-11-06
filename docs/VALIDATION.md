# Reporte de Validación y Pruebas Automatizadas

**Proyecto:** SLT Bilingual Core  
**Fecha de validación:** Noviembre 2026  
**Resultado SLT Core (Fase 1):** 100% Superado (40/40 pruebas unitarias del núcleo, 99% de cobertura)  
**Resultado Legacy Desktop:** 100% Superado (33/33 pruebas de UI y adaptadores)

---

## 1. Matriz Formal de Trazabilidad y Criterios de Aceptación (Fase 1)

| ID | Requisito | Prueba de Aceptación | Estado | Evidencia |
| :--- | :--- | :--- | :--- | :--- |
| **CORE-001** | Contratos válidos | Construcción de objetos y validación exhaustiva de campos | **APROBADO** | `tests/test_domain.py` (Landmark, HandObservation, SignEvent, PerceptionFrame, TranslationOutput, LanguageProfile) |
| **CORE-002** | Perfiles independientes | Cargar perfiles diferentes sin mezclarlos | **APROBADO** | `tests/test_profiles.py`, `tests/test_phrase_buffer.py::test_profile_isolation` |
| **CORE-003** | Varios idiomas de salida | Generar ES/EN desde el mismo perfil cuando esté habilitado | **APROBADO** | `tests/test_pipeline.py::test_full_pipeline_flow` |
| **CORE-004** | Eventos temporales | Mantener inicio y final de cada seña con precisión | **APROBADO** | `tests/test_domain.py::test_sign_event_single_hand`, `tests/test_pipeline.py` |
| **CORE-005** | Dos manos | Representar y validar eventos bimanuales | **APROBADO** | `tests/test_domain.py::test_sign_event_bimanual` (`len(handedness)==2`, `len(hand_tracking_ids)==2`) |
| **CORE-006** | Orden temporal | Rechazar timestamps regresivos por fuente | **APROBADO** | `tests/test_phrase_buffer.py::test_temporal_monotonicity`, `tests/test_pipeline.py::test_frame_index_and_timestamp_monotonicity` |
| **CORE-007** | Fuentes independientes | Procesar fuentes con relojes diferentes e independientes | **APROBADO** | `tests/test_pipeline.py::test_multi_source_isolation` |
| **CORE-008** | Phrase Buffer | Añadir, deduplicar, deshacer (undo) y limpiar eventos | **APROBADO** | `tests/test_phrase_buffer.py::test_append_and_retrieve`, `test_deduplication`, `test_undo`, `test_clear` |
| **CORE-009** | Traducción | Conservar asociación estricta entre evento y salida | **APROBADO** | `tests/test_pipeline.py::test_translation_contract_validation` |
| **CORE-010** | Fallos | Detectar componentes no disponibles antes de procesar | **APROBADO** | `tests/test_pipeline.py::test_component_readiness_checks` |
| **CORE-011** | Recursos | Cerrar y liberar todos los componentes de forma segura | **APROBADO** | `tests/test_pipeline.py::test_flush_clear_and_close` |
| **CORE-012** | Multiplataforma | Superar CI en Windows, Linux (Ubuntu 24.04) y macOS | **APROBADO** | `.github/workflows/core-tests.yml` (pure Python sin dependencias C++ obligatorias para core) |
| **CORE-013** | Reproducibilidad | Mismos datos producen resultados deterministas | **APROBADO** | `tests/test_pipeline.py::test_full_pipeline_flow` |

---

## 2. Resumen de Ejecución de Pruebas SLT Core

```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.2.0, pluggy-1.7.0
rootdir: C:\Users\enfoc\Desktop\slt_bilingual_core
configfile: pyproject.toml
plugins: cov-7.1.0
collected 40 items

tests/test_domain.py::test_landmark_valid PASSED                         [  2%]
tests/test_domain.py::test_landmark_non_finite_raises PASSED             [  5%]
tests/test_domain.py::test_hand_observation_valid PASSED                 [  7%]
tests/test_domain.py::test_hand_observation_invalid PASSED               [ 10%]
tests/test_domain.py::test_frame_packet_valid PASSED                     [ 12%]
tests/test_domain.py::test_frame_packet_invalid PASSED                   [ 15%]
tests/test_domain.py::test_perception_frame_valid_and_invalid PASSED     [ 17%]
tests/test_domain.py::test_recognition_hypothesis_semantics PASSED       [ 20%]
tests/test_domain.py::test_sign_event_single_hand PASSED                 [ 22%]
tests/test_domain.py::test_sign_event_bimanual PASSED                    [ 25%]
tests/test_domain.py::test_sign_event_validation_errors PASSED           [ 27%]
tests/test_domain.py::test_translation_output_validation PASSED          [ 30%]
tests/test_domain.py::test_language_profile_validation PASSED            [ 32%]
tests/test_profiles.py::test_load_profile_without_model PASSED           [ 35%]
tests/test_profiles.py::test_artifacts_present_when_files_exist PASSED   [ 37%]
tests/test_profiles.py::test_missing_manifest_raises PASSED              [ 40%]
tests/test_profiles.py::test_malformed_json_raises PASSED                [ 42%]
tests/test_profiles.py::test_invalid_schema_version_raises PASSED        [ 45%]
tests/test_profiles.py::test_duplicate_profile_id_raises PASSED          [ 47%]
tests/test_profiles.py::test_invalid_profile_id_syntax PASSED            [ 50%]
tests/test_profiles.py::test_path_traversal_prevention PASSED            [ 52%]
tests/test_profiles.py::test_unknown_profile_raises PASSED               [ 55%]
tests/test_profiles.py::test_registry_manifest_structure_errors PASSED   [ 57%]
tests/test_profiles.py::test_registry_entries_and_safe_path PASSED       [ 60%]
tests/test_profiles.py::test_registry_listing_and_contains PASSED        [ 62%]
tests/test_phrase_buffer.py::test_append_and_retrieve PASSED             [ 65%]
tests/test_phrase_buffer.py::test_deduplication PASSED                   [ 67%]
tests/test_phrase_buffer.py::test_profile_isolation PASSED               [ 70%]
tests/test_phrase_buffer.py::test_temporal_monotonicity PASSED           [ 72%]
tests/test_phrase_buffer.py::test_append_many PASSED                     [ 75%]
tests/test_phrase_buffer.py::test_undo PASSED                            [ 77%]
tests/test_phrase_buffer.py::test_clear PASSED                           [ 80%]
tests/test_pipeline.py::test_full_pipeline_flow PASSED                   [ 82%]
tests/test_pipeline.py::test_component_readiness_checks PASSED           [ 85%]
tests/test_pipeline.py::test_frame_index_and_timestamp_monotonicity PASSED [ 87%]
tests/test_pipeline.py::test_multi_source_isolation PASSED               [ 90%]
tests/test_pipeline.py::test_decoder_contract_validation PASSED          [ 92%]
tests/test_pipeline.py::test_translation_contract_validation PASSED      [ 95%]
tests/test_pipeline.py::test_pipeline_additional_edge_cases PASSED       [ 97%]
tests/test_pipeline.py::test_flush_clear_and_close PASSED                [100%]

=============================== tests coverage ================================
Name                               Stmts   Miss  Cover   Missing
----------------------------------------------------------------
src\slt_core\__init__.py               4      0   100%
src\slt_core\contracts.py             17      0   100%
src\slt_core\domain.py               151      0   100%
src\slt_core\errors.py                 9      0   100%
src\slt_core\phrase_buffer.py         49      0   100%
src\slt_core\pipeline.py             110      0   100%
src\slt_core\profile_registry.py      92      1    99%   123
----------------------------------------------------------------
TOTAL                                432      1    99%
============================= 40 passed in 0.53s ==============================
```
