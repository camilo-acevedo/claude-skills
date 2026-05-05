from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Symbol:
    signature: str
    kind: str  # "function" | "class" | "constant" | "type"


@dataclass
class FileSummary:
    purpose: Optional[str] = None
    symbols: List[Symbol] = field(default_factory=list)
    parse_error: Optional[str] = None
