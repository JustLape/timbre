from enum import Enum


class ErrorCode(str, Enum):
    DAINA_NERASTA = "DAINA_NERASTA"
    NULINIAI_SVORIAI = "NULINIAI_SVORIAI"
    NETINKAMAS_SVORIS = "NETINKAMAS_SVORIS"
    NETINKAMAS_FILTRAS = "NETINKAMAS_FILTRAS"


class TimbreError(Exception):
    def __init__(self, code: ErrorCode, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"[{code.value}] {message}")