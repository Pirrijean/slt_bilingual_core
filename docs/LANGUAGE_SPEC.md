# SLT Language Specification

> **Linguistic Principle**: *Sign recognition is not translation. Linguistic translation requires syntactic realization, semantic composition, and grammatical target mapping.*

---

## 1. Intermediate Representation: `SemanticFrame`

Instead of naive string replacements (which produce ungrammatical "word salad"), SLT maps confirmed sign sequences into a structured, language-independent intermediate representation called a **`SemanticFrame`**:

```python
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class SemanticFrame:
    """Language-independent semantic representation of a sign sequence."""
    action: Optional[str] = None          # e.g., "WANT", "NEED", "GREET", "THANK"
    subject: Optional[str] = None         # e.g., "FIRST_PERSON", "SECOND_PERSON"
    object: Optional[str] = None          # e.g., "WATER", "FOOD", "HELP"
    polarity: str = "positive"            # "positive" | "negative"
    intention: str = "statement"          # "statement" | "question" | "exclamation" | "request"
    politeness: Optional[str] = None      # "PLEASE", "THANK_YOU", None
    fingerspelled: Optional[str] = None   # Concatenated letters from dactilology
    raw_glosses: List[str] = None
```

---

## 2. Realization Pipelines

Once the `SemanticFrame` is constructed, specialized, deterministic generators for Spanish and English produce natural target sentences:

| Semantic Frame Arguments | Spanish Realization | English Realization |
| :--- | :--- | :--- |
| `subject=1P, action=WANT, object=WATER` | *"Quiero agua."* (pro-drop) | *"I want water."* (explicit pronoun) |
| `subject=1P, action=WANT, object=FOOD` | *"Quiero comida."* | *"I want food."* |
| `subject=1P, object=HELP, intention=request` | *"Necesito ayuda urgente."* | *"I need urgent help."* |
| `action=GREET, intention=question` | *"Hola, ¿cómo estás?"* | *"Hello, how are you?"* |
| `politeness=PLEASE, polarity=positive` | *"Sí, por favor."* | *"Yes, please."* |
| `politeness=THANK_YOU, polarity=negative` | *"No, gracias."* | *"No, thank you."* |
| `politeness=PLEASE_AND_THANK_YOU` | *"Por favor y muchas gracias."* | *"Please and thank you very much."* |
| `fingerspelled="AGUA"` | *"Palabra: AGUA."* | *"Spelled: AGUA."* |

---

## 3. Versioned Lexicon Contract (`lexicon.json`)

Each entry in `config/lexicon.json` adheres to a strict schema with syntactic roles and validation metadata:

```json
{
  "sign_id": "SLT_SIGN_008",
  "gloss": "AGUA",
  "category": "noun",
  "semantic_id": "WATER",
  "translations": {
    "es": "agua",
    "en": "water"
  },
  "syntactic_role": "object",
  "requires_arguments": false,
  "validation_status": "validated",
  "vocabulary_version": "1.0.0"
}
```

The `validation_status` field (`"validated"` vs `"provisional"`) allows clear provenance tracking as the vocabulary expands to Colombian Sign Language (LSC) and American Sign Language (ASL).
