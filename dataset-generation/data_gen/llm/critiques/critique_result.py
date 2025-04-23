from typing import List, Dict


class CritiqueResult:
    """
    Result class of a critique.
    """
    def __init__(self, name: str, is_valid: bool, errors: List[Dict], critique_command: str):
        self.name: str = name
        self.is_valid: bool = is_valid
        self.errors: List[Dict] = errors
        self.critique_command: str = critique_command

    @classmethod
    def correct(cls, name: str) -> 'CritiqueResult':
        return CritiqueResult(
            name, True, [], ''
        )

    def json(self) -> Dict:
        return {
            'name': self.name,
            'errors': self.errors
        }
