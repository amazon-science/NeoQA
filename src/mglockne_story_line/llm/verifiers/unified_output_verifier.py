import logging
from collections import defaultdict
from typing import List, Dict

from src.mglockne_story_line.llm.verifiers.base_verifier import BaseVerifier

logger = logging.getLogger(__name__)


class UnifiedOutputVerifier:
    def __init__(
            self, keys_entity: List[str], keys_text: List[str], verifiers: List[BaseVerifier], verbose: bool = True
    ):
        self.keys_entity: List[str] = keys_entity
        self.keys_text: List[str] = keys_text
        self.verifiers: List[BaseVerifier] = verifiers
        self.verbose: bool = verbose

    def get_verifier_summaries(self, detailed_verification: Dict):
        summaries: Dict[str, Dict] = defaultdict(dict)
        for verifier in self.verifiers:

            num_checks: int = 0
            num_validated: int = 0
            for field in detailed_verification:
                verifier_results = [r for r in detailed_verification[field] if r['verifier'] == verifier.name]
                if len(verifier_results) > 1:
                    raise ValueError(f'Multiple identical verifiers for the same field: {verifier.name}')
                if len(verifier_results) == 1:
                    verifier_result = verifier_results[0]
                    num_validated += len(verifier_result['validated'])
                    num_checks += len(verifier_result['validated'])
                    num_checks += len(verifier_result['errors'])
            summaries[verifier.name] = {
                'checks': num_checks, 'validated': num_validated, 'errors': num_checks - num_validated
            }
        return summaries

    def check_structured_output(self, output: Dict) -> Dict:
        correct: bool = True

        detailed_verifications = defaultdict(list)

        for verifier in self.verifiers:
            if BaseVerifier.CAN_CHECK_ENTITY in verifier.can_check():
                for key in self.keys_entity:
                    out = verifier.check_entity(output[key])
                    detailed_verifications[key].append({**{'verifier': verifier.name}, **out.json()})
                    correct = correct and len(out.errors) == 0
                    if self.verbose:
                        logger.info('Verifier: ' + verifier.name)
                        logger.info(str(out))

            if BaseVerifier.CAN_CHECK_TEXT in verifier.can_check():
                for key in self.keys_text:
                    out = verifier.check_text(output[key])
                    detailed_verifications[key].append({**{'verifier': verifier.name}, **out.json()})
                    correct = correct and len(out.errors) == 0
                    if self.verbose:
                        logger.info('Verifier: ' + verifier.name)
                        logger.info(str(out))

        return {
            'correct': correct,
            'details': detailed_verifications,
            'summaries': self.get_verifier_summaries(detailed_verifications)
        }