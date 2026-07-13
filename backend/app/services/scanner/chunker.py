import ast
import re
from dataclasses import dataclass
from typing import List


@dataclass
class CodeChunk:
    code: str
    language: str
    function_name: str
    line_start: int
    line_end: int


MAX_CHUNK_LINES = 150


def chunk_code(code: str, language: str) -> List[CodeChunk]:
    """Split code into logical chunks by function/class boundary."""
    if language == "python":
        return _chunk_python(code)
    return _chunk_generic(code, language)


def _chunk_python(code: str) -> List[CodeChunk]:
    chunks: List[CodeChunk] = []
    lines = code.splitlines()

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return _chunk_generic(code, "python")

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            start = node.lineno - 1
            end = (node.end_lineno or node.lineno) - 1
            chunk_lines = lines[start : end + 1]

            # Split oversized chunks
            for sub_chunk, sub_start in _split_large(chunk_lines, start, MAX_CHUNK_LINES):
                chunks.append(
                    CodeChunk(
                        code="\n".join(sub_chunk),
                        language="python",
                        function_name=getattr(node, "name", "unknown"),
                        line_start=sub_start + 1,
                        line_end=sub_start + len(sub_chunk),
                    )
                )

    # If no functions found, treat file as one chunk
    if not chunks:
        return _chunk_generic(code, "python")

    return chunks


def _chunk_generic(code: str, language: str) -> List[CodeChunk]:
    """Fallback: split by regex function patterns or fixed line windows."""
    lines = code.splitlines()
    patterns = {
        "javascript": r"^(async\s+)?function\s+\w+|^\s*(const|let|var)\s+\w+\s*=\s*(async\s+)?\(",
        "typescript": r"^(async\s+)?function\s+\w+|^\s*(const|let|var)\s+\w+\s*=\s*(async\s+)?\(",
        "java": r"^\s*(public|private|protected)\s+.*\w+\s*\(",
        "go": r"^func\s+",
        "php": r"^\s*function\s+\w+",
        "ruby": r"^\s*def\s+\w+",
    }
    pattern = patterns.get(language)
    chunks: List[CodeChunk] = []

    if pattern:
        func_starts = [i for i, line in enumerate(lines) if re.match(pattern, line)]
        func_starts.append(len(lines))

        for idx, start in enumerate(func_starts[:-1]):
            end = func_starts[idx + 1] - 1
            chunk_lines = lines[start : end + 1]
            func_name_match = re.search(r"\b(\w+)\s*\(", lines[start])
            func_name = func_name_match.group(1) if func_name_match else f"block_{idx + 1}"

            for sub_chunk, sub_start in _split_large(chunk_lines, start, MAX_CHUNK_LINES):
                chunks.append(
                    CodeChunk(
                        code="\n".join(sub_chunk),
                        language=language,
                        function_name=func_name,
                        line_start=sub_start + 1,
                        line_end=sub_start + len(sub_chunk),
                    )
                )

    # Fallback: fixed windows
    if not chunks:
        for i, (sub_chunk, sub_start) in enumerate(_split_large(lines, 0, MAX_CHUNK_LINES)):
            chunks.append(
                CodeChunk(
                    code="\n".join(sub_chunk),
                    language=language,
                    function_name=f"segment_{i + 1}",
                    line_start=sub_start + 1,
                    line_end=sub_start + len(sub_chunk),
                )
            )

    return chunks


def _split_large(lines: list, offset: int, max_lines: int):
    """Yield (chunk_lines, start_index) slices no larger than max_lines."""
    for i in range(0, max(len(lines), 1), max_lines):
        yield lines[i : i + max_lines], offset + i
