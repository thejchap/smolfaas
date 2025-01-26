from __future__ import annotations

from typing import Any

class V8System:
    @staticmethod
    def compile_and_invoke_source(source: str) -> str: ...
    @staticmethod
    def invoke_function(
        function_id: str,
        source: str,
        live_deployment_id: str,
        payload: dict[Any, Any] | None = None,
    ) -> str: ...
