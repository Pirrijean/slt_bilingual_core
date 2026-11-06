"""Sentence builder with grammatical rules and fingerspelling assembly."""
from __future__ import annotations
from .lexicon import Lexicon, normalize_gloss

class SentenceBuilder:
    def __init__(self, lexicon: Lexicon):
        self.lexicon = lexicon

    def build_sentence(self, glosses: list[str], lang: str = "es") -> str:
        """Construct a grammatically coherent sentence in the requested language."""
        cleaned = [normalize_gloss(g) for g in glosses if g and normalize_gloss(g) != "_NADA_"]
        if not cleaned:
            return ""

        output_clauses: list[str] = []
        clause_items: list[tuple[str, str, dict | None]] = []
        i = 0

        while i < len(cleaned):
            # 1. Greedy match for idiomatic phrase expressions
            matched_phrase = None
            for phrase_glosses, phrase_data in self.lexicon.phrases:
                plen = len(phrase_glosses)
                if i + plen <= len(cleaned) and tuple(cleaned[i:i + plen]) == phrase_glosses:
                    matched_phrase = phrase_data
                    break

            if matched_phrase:
                self._flush_clause(clause_items, output_clauses, lang)
                output_clauses.append(matched_phrase[lang])
                i += len(matched_phrase["glosses"])
                continue

            g = cleaned[i]
            info = self.lexicon.get_sign(g)

            # Fallback for letters or words not in lexicon
            if not info:
                if len(g) == 1 and g.isalpha():
                    info = {"type": "letter"}
                else:
                    info = {"type": "word", "es": g.lower().replace("_", " "), "en": g.lower().replace("_", " ")}

            wtype = info.get("type", "word")

            # 2. Fingerspelling assembly (consecutive single letters)
            if wtype == "letter":
                j = i
                while j < len(cleaned):
                    nxt_info = self.lexicon.get_sign(cleaned[j])
                    if nxt_info and nxt_info.get("type") == "letter":
                        j += 1
                    elif not nxt_info and len(cleaned[j]) == 1 and cleaned[j].isalpha():
                        j += 1
                    else:
                        break
                spelled_word = "".join(cleaned[i:j]).lower()
                clause_items.append(("word", spelled_word, None))
                i = j
                continue

            # 3. Interjections emit self-contained clauses
            if wtype == "interj":
                self._flush_clause(clause_items, output_clauses, lang)
                output_clauses.append(info.get(lang, ""))
            # 4. Courtesy tail (e.g. "por favor") attaches to preceding clause
            elif wtype == "tail":
                if clause_items:
                    self._flush_clause(clause_items, output_clauses, lang, tail=info.get(lang))
                else:
                    output_clauses.append(info.get(f"solo_{lang}", info.get(lang, "")))
            else:
                clause_items.append((wtype, g, info))

            i += 1

        self._flush_clause(clause_items, output_clauses, lang)
        return " ".join(output_clauses).strip()

    def _flush_clause(
        self,
        clause_items: list[tuple[str, str, dict | None]],
        out_list: list[str],
        lang: str,
        tail: str | None = None
    ):
        if not clause_items:
            return

        # Solo single word with custom solo phrasing
        if len(clause_items) == 1 and clause_items[0][2] and not tail:
            solo_txt = clause_items[0][2].get(f"solo_{lang}")
            if solo_txt:
                out_list.append(solo_txt)
                clause_items.clear()
                return

        # Find subject and grammatical person
        subject_item = next((item for item in clause_items if item[0] == "pron"), None)
        person = "1"
        if subject_item and subject_item[2]:
            person = str(subject_item[2].get("person", 1))

        verbs = [item for item in clause_items if item[0] == "verb"]
        complements = [item for item in clause_items if item is not subject_item and item[0] != "verb"]

        def resolve_text(item: tuple[str, str, dict | None]) -> str:
            itype, igloss, iinfo = item
            if iinfo is None:
                return igloss
            val = iinfo.get(lang)
            if isinstance(val, dict):
                return val.get(person, val.get("1", ""))
            return str(val) if val is not None else igloss.lower()

        tokens = []
        if subject_item:
            tokens.append(resolve_text(subject_item))
        elif verbs and lang == "en":
            tokens.append("I")  # English requires explicit subject pronoun

        for v in verbs:
            tokens.append(resolve_text(v))
        for c in complements:
            tokens.append(resolve_text(c))

        raw_sent = " ".join(tokens).strip()
        if not raw_sent:
            clause_items.clear()
            return

        # Capitalize and append punctuation
        capitalized = raw_sent[0].upper() + raw_sent[1:]
        if tail:
            capitalized = f"{capitalized}, {tail}"

        if not capitalized.endswith((".", "!", "?")):
            capitalized += "."

        out_list.append(capitalized)
        clause_items.clear()
