from typing import Dict, List

from src.mglockne_story_line.llm.critiques.critique_result import CritiqueResult


class BaseCritique:
    """
    Critique class which processes and verifiers the values. Subclasses define the what and how this validation happens.
    If errors are found by the Critique, a statement is output to correct the output.
    """

    def __init__(self, name: str):
        self.name: str = name

    def process(self, values: Dict) -> CritiqueResult:
        """
        This method must be overwritten to implement the verification logic and critique commands in case of a failed verification.
        """
        raise NotImplementedError()

    def add_errors_to_result(self, values: Dict, errors: List[Dict]) -> Dict:
        if "critique_errors" not in values:
            values["critique_errors"] = dict()
        if self.name not in values["critique_errors"]:
            values["critique_errors"][self.name] = []
        values["critique_errors"][self.name].append({
            'errors': errors, 'success': ['not-specified']
        })
        return values

    def update_values(self, values: Dict, critique_results: List[CritiqueResult]) -> Dict:
        """
        Critiques may automatically correct the values without the need to prompt the LLM to correct the outputs.
        By default the values remain unchanged.
        If values are automatically updated, implement the logic to alter the returned "values".
        """
        return values

    def reset(self):
        """
        This function is called prior to a module being called for the first time.
        Every time a critique is called to correct the module's output this method is NOT called.
        Override if the critique subclass manages instance-level status variables to reset them.
        """
        pass

