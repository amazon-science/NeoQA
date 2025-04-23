from typing import List, Dict, Optional, Set


class VerifyResult:
    def __init__(self, num_checked: int, num_correct: int, errors: Optional[List[Dict]] = None, success: Optional[List[Dict]] = None):
        if success is None:
            success = []
        if errors is None:
            errors = []
        self.num_checked: int = num_checked
        self.num_correct: int = num_correct
        self.errors: List[Dict] = errors
        self.success: List[Dict] = success

    def __str__(self):
        return '\n'.join([
            f"Number checked: {self.num_checked}",
            f"Number correct: {self.num_correct}",
            f"Errors:",
        ] + [
            f' - {err}' for err in self.errors
        ])

    def json(self) -> Dict:
        return {
            "validated": self.success, "errors": self.errors
        }


class BaseVerifier:
    CAN_CHECK_ENTITY: str = 'entity'
    CAN_CHECK_TEXT: str = 'text'

    def __init__(self, name: str):
        self.name: str = name

    def can_check(self) -> Set[str]:
        raise NotImplementedError()

    def check_entity(self, entity: str) -> VerifyResult:
        raise NotImplementedError()

    def check_text(self, text: str) -> VerifyResult:
        raise NotImplementedError()
