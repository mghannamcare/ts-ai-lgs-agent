from pathlib import Path
from .document_parser import parse_document


def build_kb_text_from_files(paths: list[str | Path]) -> tuple[str, list[dict]]:
    chunks = []
    meta = []
    for p in paths:
        p = Path(p)
        try:
            parsed = parse_document(p)
            text = parsed.get('text', '')
            meta.append({'file': p.name, 'status': parsed.get('status'), 'chars': len(text)})
            if text:
                chunks.append(f'[TS KNOWLEDGE SOURCE: {p.name}]\n{text}')
        except Exception as exc:
            meta.append({'file': p.name, 'status': 'error', 'error': str(exc), 'chars': 0})
    return '\n\n'.join(chunks), meta
