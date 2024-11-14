from typing import List, Dict, Tuple, Optional

from src.mglockne_story_line.llm.critiques.base_critique import BaseCritique, CritiqueResult
from src.mglockne_story_line.llm.modules.callable_module import CallableModule
from src.mglockne_story_line.llm.prompting.parsable_prompt import ParsablePrompt


def get_critique_text(version: str) -> str:
    if version == 'v1':
        out: str = """
        I found problems with your response. Please fix these problems and return the corrected output using the same format as before. The problems I found are:
        """
    else:
        raise NotImplementedError()
    return out.strip()


class XMlParseError(ValueError):
    pass


class UnifiedCritiqueModule:
    """
    A wrapper class to combine multiple BaseCritique instances. Appies each BaseCritique and outputs a unified
    critique message based on all used critiques.
    """
    def __init__(
            self,
            critiques: List[BaseCritique],
            format_critique: BaseCritique,
            max_critiques: int = 0,
            critique_text: str = 'v1',
            history: Optional[List[Tuple[str, str]]] = None
    ):
        self.critiques: List[BaseCritique] = critiques
        for critique in critiques:
            critique.reset()
        self.format_critique: BaseCritique = format_critique
        self.max_critiques: int = max_critiques
        self.errors: List[CritiqueResult] = []
        self.num_critiqued = 0
        self.history: List[Tuple[str, str]] = history or []
        self.critique_text: str = get_critique_text(critique_text)

    def update_values(self, values: Dict) -> Dict:
        """
        Unify the update_values methods from all child critique instances.
        """
        for critique in self.critiques:
            critique_results: List[CritiqueResult] = [r for r in self.errors if r.name == critique.name]
            values = critique.update_values(values, critique_results)
        return values

    def verify(self, values: Dict, response: Optional[str] = None) -> bool:
        """
        Verify if the response is valid (i.e. no critique is triggered).
        """
        if len(self.critiques) > 0:
            critique_results: List[CritiqueResult] = [critique.process(values) for critique in self.critiques]
            self.errors: List[CritiqueResult] = list(filter(lambda r: not r.is_valid, critique_results))

            if len(self.errors) > 0 and response is not None:
                print('-----ERROR RESPONSE:------')
                print(response)
                print('------END--------')
        return len(self.errors) == 0

    def set_history(self, history: List[Tuple[str, str]]):
        """
        Set the history of messages.
        Ensures that all context is available. Gets updated with critiques.
        """
        self.history = history

    def can_critique_more(self) -> bool:
        """
        Checks if the number of critiques has reached its allowed maximum to avoid critiquing forever.
        """
        return self.num_critiqued < self.max_critiques

    def get_valid_format_response_with_critique(self, llm_caller: CallableModule, cache_file_path: str) -> str:
        """
        Does two things:
        1. Applies a critique to correct the mistakes by the LLM
        2. Makes sure that the LLM output has the right format (or critiques the LLM to get the right format - if a format critique is provided.)
        """
        critique_text: str = self.get_critique_text().strip()
        print('-------CRITIQUE:----------')
        print(critique_text)
        print('-----')

        response: str = llm_caller.critique(critique_text.strip(), self.history, self.num_critiqued, cache_file_path)
        print("-------CRITIQUE RESPONSE--------")
        print(response)
        print('-----END-----\n')
        self.num_critiqued += 1
        self.history.append((critique_text, response))
        format_validation: CritiqueResult = self.has_valid_format(response)
        if not format_validation.is_valid:
            response = self.get_valid_format(llm_caller, cache_file_path, format_validation)

        assert response is not None
        return response

    def get_valid_format(self, llm_caller: CallableModule, cache_file_path: str, critique_result: CritiqueResult) -> str:

        critique_text: str = critique_result.critique_command.strip()
        if len(critique_text) == 0:
            raise ValueError("Cannot critique!")

        response: Optional[str] = None
        while not critique_result.is_valid and self.can_critique_more():
            print(f'FORMAT CRITIQUE ({self.num_critiqued} / {self.max_critiques})')
            print(critique_text.strip())
            response: str = llm_caller.critique(critique_text.strip(), self.history, self.num_critiqued, cache_file_path)
            print('-----------')
            print('RESPONSE')
            print(response)
            print('-------END-------')
            self.num_critiqued += 1
            self.history.append((critique_text, response))
            critique_result = self.has_valid_format(response)

        if critique_result.is_valid:
            assert response is not None
            return response
        else:
            print(f'({self.num_critiqued} / {self.max_critiques})     s')
            raise XMlParseError(critique_result.errors)

    def has_valid_format(self, response: str) -> CritiqueResult:
        if self.format_critique is None:
            return CritiqueResult('default', True, [], '')
        result: CritiqueResult = self.format_critique.process({'response': response})
        return result

    def critique_content(self, parsable_prompt: ParsablePrompt, llm_caller: CallableModule, cache_file_path: str):
        if len(self.errors) == 0:
            raise ValueError('Cannot critique!')

        assert len(self.history) > 0

        response: str = self.get_valid_format_response_with_critique(
            llm_caller, cache_file_path
        )
        return parsable_prompt.parse(response) | {'response': response}

    def get_history(self) -> List[Tuple[str, str]]:
        return self.history

    def get_critique_text(self, add_critique_instructions: bool = True) -> str:
        if len(self.errors) == 0:
            raise ValueError('Cannot critique!')
        critique_text: str = self.critique_text + '\n\n' if add_critique_instructions else ''
        for err in self.errors:
            critique_text += f'{err.critique_command}\n\n'

        return critique_text


    def last_validity_issues(self) -> List[Dict]:
        return [
            err.json() for err in self.errors
        ]


