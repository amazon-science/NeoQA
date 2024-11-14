from typing import Dict, Optional, Tuple, List

from src.mglockne_story_line.llm.prompting.parsable_prompt import ParsablePrompt


class FilePathModule:
    def get_file_name(self, prompt: ParsablePrompt, values: Dict):
        raise NotImplementedError()

class CallableModule:
    """
    Baseclass module that can be called and critiqued.
    """

    def call(self, values: Dict, output_directory: str) -> Dict:
        """
        Used when automatically applying this module within a pipeline.
        """
        raise NotImplementedError()

    def reset(self):
        raise NotImplementedError()

    def query(
            self,
            prompt: ParsablePrompt, values: Dict,
            output_directory: str,
            system_prompt: Optional[str] = None,
            params: Optional[Dict] = None,
            use_history: Optional[List[Tuple[str, str]]] = None,
            print_prompt: bool = False
    ) -> Dict:
        """
        Queries the callable module by providing all relevant information such as prompts etc. This differs from call(),
        which does not require explicitly providing them via the parameters.
        """
        raise NotImplementedError()

    def critique(self, critique_text: str, history: List[Tuple[str, str]], num_critique: int, cache_file_path: str) -> str:
        raise NotImplementedError()
