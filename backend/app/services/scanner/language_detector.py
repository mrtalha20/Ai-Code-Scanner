import re

EXTENSION_MAP = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".jsx": "javascript", ".tsx": "typescript", ".java": "java",
    ".go": "go", ".php": "php", ".rb": "ruby", ".cs": "csharp",
    ".cpp": "cpp", ".c": "c",
}

SUPPORTED_LANGUAGES = set(EXTENSION_MAP.values())

HEURISTICS = [
    ("python", [r"^\s*def ", r"^\s*import ", r"^\s*from .* import", r"print\(", r":\s*$"]),
    ("javascript", [r"(const|let|var)\s+\w+\s*=", r"=>\s*{", r"console\.log", r"require\("]),
    ("typescript", [r":\s*(string|number|boolean|void|any)\b", r"interface\s+\w+", r"<T>"]),
    ("java", [r"public\s+(class|interface)", r"System\.out\.print", r"@Override"]),
    ("go", [r"^func\s+", r"^package\s+", r":=", r"fmt\.Print"]),
    ("php", [r"<\?php", r"\$\w+\s*=", r"echo\s+"]),
    ("ruby", [r"^\s*def\s+\w+", r"puts\s+", r"\.each\s+do"]),
]


def detect_language(code: str, hint: str | None = None) -> str:
    if hint and hint.lower() in SUPPORTED_LANGUAGES:
        return hint.lower()

    scores: dict[str, int] = {}
    for lang, patterns in HEURISTICS:
        scores[lang] = sum(1 for p in patterns if re.search(p, code, re.MULTILINE))

    best = max(scores, key=lambda k: scores[k]) if scores else "unknown"
    return best if scores.get(best, 0) > 0 else "unknown"
