# SLT Dataset & Acquisition Protocol

---

## 1. Vocabulary Classes (19 Total)

| ID | Class Label | Type | Semantic Meaning | Syntactic Role |
| :--- | :--- | :--- | :--- | :--- |
| `000` | `_NADA_` | Rest / Rejection | Neutral rest / unclassified posture | Rejection |
| `001` | `HOLA` | Courtesy / Greeting | Hello / Greeting | Discourse |
| `002` | `GRACIAS` | Courtesy | Thank you | Politeness |
| `003` | `POR_FAVOR` | Courtesy | Please | Politeness |
| `004` | `SI` | Affirmation | Yes | Affirmation |
| `005` | `NO` | Negation | No | Negation |
| `006` | `AYUDA` | Emergency / Need | Help | Object / Action |
| `007` | `AGUA` | Basic Need | Water | Object |
| `008` | `COMIDA` | Basic Need | Food | Object |
| `009` | `ESTAR_BIEN` | State | Well / OK / Fine | Predicate |
| `010` | `TE_QUIERO` | Affective Expression | I love you / Affection | Predicate |
| `011` | `YO` | Pronoun | I / Me | Subject (1P) |
| `012` | `TU` | Pronoun | You | Subject (2P) |
| `013` | `QUERER` | Verb | Want / Desire | Verb |
| `014` | `A` | Dactilology | Letter A | Character |
| `015` | `E` | Dactilology | Letter E | Character |
| `016` | `I` | Dactilology | Letter I | Character |
| `017` | `O` | Dactilology | Letter O | Character |
| `018` | `U` | Dactilology | Letter U | Character |

---

## 2. Acquisition Protocol & Data Partitioning

- **Data Directory**: `data/`
  - `data/raw/`: Raw CSV files captured per session.
  - `data/processed/`: Processed `.npz` feature matrices.
  - `data/splits/`: Stratified participant train/test split definitions.
- **Stratification Strategy**: Mappings are grouped by participant IDs (Signer 1, Signer 2, Signer 3, Signer 4, Signer 5). Testing is evaluated on an independent holdout participant to ensure realistic generalization.
