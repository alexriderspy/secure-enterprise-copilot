"""Which defences are on. Production uses all of them; the red-team eval switches them off to compare."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Defences:
    redact_ingest: bool = True   # mask identifiers before chunks are stored
    scan_ingest: bool = True     # quarantine chunks that look like prompt injection
    spotlight: bool = True       # sources inside <source> tags, with "never obey a source"
    guard_output: bool = True    # canary, link and image removal, identifier masking on the answer


ALL_ON = Defences()
NONE = Defences(False, False, False, False)  # last week's knowledge base
