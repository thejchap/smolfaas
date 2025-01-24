from __future__ import annotations

class V8System:
    @staticmethod
    def compile_and_run(src: str) -> str: ...
    @staticmethod
    def compile(src: str) -> bytes: ...
