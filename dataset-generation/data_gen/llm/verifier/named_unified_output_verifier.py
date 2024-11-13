from typing import List

from data_gen.llm.verifier.base_verifier import BaseVerifier
from data_gen.llm.verifier.unified_output_verifier import UnifiedOutputVerifier


class NamedUnifiedOutputVerifier(UnifiedOutputVerifier):
    def __init__(self, name: str, keys_entity: List[str], keys_text: List[str], verifiers: List[BaseVerifier],
                 verbose: bool = True):
        super().__init__(keys_entity, keys_text, verifiers, verbose)
        self.name: str = name
