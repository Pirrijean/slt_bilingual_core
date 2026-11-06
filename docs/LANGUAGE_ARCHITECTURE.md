# SLT Multilingual Language Architecture

**Versión:** 1.0.0 (Fase 0 - Fundacional)  
**Alcance:** Separación de lengua de señas de entrada e idiomas de salida, perfiles soberanos y ciclo de vida de modelos.

---

## 1. La Distinción Fundamental en SLT

Un error crítico en sistemas de traducción de señas es tratar a las distintas lenguas de señas como si fueran dialectos intercambiables de un mismo vocabulario mediante una simple variable de configuración.

SLT establece dos dimensiones lingüísticas completamente independientes:

```
+-----------------------------------------------------------------------------------+
|                        DIMENSIÓN 1: LENGUA DE SEÑAS DE ENTRADA                    |
|   LSC (Lengua de Señas Colombiana)  |  ASL (American Sign Language)  |  Otras     |
|   - Vocabulario propio              |  - Vocabulario propio          |  - ...     |
|   - Gramática viso-espacial propia  |  - Gramática propia            |            |
|   - Modelo cinemático propio        |  - Modelo propio               |            |
+--------------------------------------+--------------------------------------------+
                                       |
                                       v
+-----------------------------------------------------------------------------------+
|                     INTERFAZ SEMÁNTICA COMÚN NORMALIZADA                          |
|   - Representación de roles semánticos (Acción, Sujeto, Objeto, Modalidad)        |
|   - Preservación de estructura de origen, prosodia y referencias temporales       |
+--------------------------------------+--------------------------------------------+
                                       |
                   +-------------------+-------------------+
                   v                                       v
+------------------------------------+   +------------------------------------+
|   DIMENSIÓN 2: IDIOMA DE SALIDA    |   |   DIMENSIÓN 2: IDIOMA DE SALIDA    |
|   Español (ej. es-CO, es-ES)       |   |   English (ej. en-US, en-GB)       |
|   - Sintaxis SVO / pro-drop        |   |   - Pronombres explícitos obligat. |
|   - Conjugaciones verbales locales |   |   - Realización morfológica en-US  |
+------------------------------------+   +------------------------------------+
```

---

## 2. Estructura de un Perfil Lingüístico Soberano

Cada lengua de señas se registra en el directorio `profiles/sign_languages/` como un producto independiente:

```text
profiles/sign_languages/
├── manifest.json                  # Registro global de perfiles disponibles
├── lsc/
│   ├── profile.json               # Metadatos, capacidades y locales de salida admitidos
│   ├── vocabulary.json            # Glosas oficiales, descriptores y roles sintácticos
│   ├── grammar.json               # Reglas de concordancia, clasificadores y orden de constituyentes
│   └── model/
│       ├── manifest.json          # Metadatos del extractor, arquitectura y fecha
│       └── weights.npz            # Pesos o prototipos entrenados
└── asl/
    ├── profile.json
    ├── vocabulary.json
    ├── grammar.json
    └── model/
        ├── manifest.json
        └── weights.npz
```

### Capacidades Declaradas del Perfil (`capabilities`)
Cada perfil declara expresamente las características cinemáticas que soporta su modelo:
- `static_signs`: Posturas manuales estáticas.
- `dynamic_signs`: Señas con movimiento o cambio de forma.
- `two_hand_signs`: Señas bimanuales coordinadas o asimétricas.
- `continuous_sequences`: Reconocimiento continuo con decodificación temporal.
- `body_context`: Puntos corporales de referencia (hombros, torso).
- `non_manual_markers`: Elementos faciales y gestuales de cabeza.

---

## 3. Estados del Ciclo de Vida de una Lengua de Señas

Para evitar falsas afirmaciones sobre lenguas soportadas, ningún perfil puede presentarse como funcional ante el usuario final sin haber superado todos los estados de validación:

```
[1. Configurado] -> [2. Dataset Disponible] -> [3. Vocabulario Validado]
       |
       v
[4. Modelo Entrenado] -> [5. Modelo Validado] -> [6. Habilitado en Producción]
```

1. **Configurado:** Existe la definición en `manifest.json` y `profile.json`.
2. **Dataset Disponible:** Existen grabaciones estructuradas con consentimiento y diversidad de participantes.
3. **Vocabulario Validado:** Cada glosa ha sido revisada por hablantes nativos o lingüistas certificados de la comunidad sorda correspondiente.
4. **Modelo Entrenado:** Existen artefactos binarios compatibles con la versión del extractor.
5. **Modelo Validado:** Superó la matriz de evaluación en participantes independientes no vistos durante el entrenamiento.
6. **Habilitado en Producción:** Verificado en el pipeline continuo sin degradación de rendimiento.
