from typing import List

from src.mglockne_story_line.llm.verifiers.base_verifier import BaseVerifier
from src.mglockne_story_line.llm.verifiers.unified_output_verifier import UnifiedOutputVerifier


class NamedUnifiedOutputVerifier(UnifiedOutputVerifier):
    def __init__(self, name: str, keys_entity: List[str], keys_text: List[str], verifiers: List[BaseVerifier],
                 verbose: bool = True):
        super().__init__(keys_entity, keys_text, verifiers, verbose)
        self.name: str = name