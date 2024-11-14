from typing import Dict, List, Optional, Tuple

from src.mglockne_story_line.llm.modules.module_pipeline import CallableModule
from src.mglockne_story_line.llm.modules.parsable_base_module import ParsableBaseModule


class HistoryParsableModuleList(CallableModule):
    """
    A modules that wraps multiple submodule that (optionally) share the same history when applied in sequence.
    """

    def __init__(self, modules: List[ParsableBaseModule], name: str, reset_history_at: Optional[List[int]] = None):
        self.modules: List[ParsableBaseModule] = modules
        self.history: List[Tuple[str, str]] = []
        self.name: str = name
        self.reset_history_at: List[int] = reset_history_at or []

        for module in self.modules:
            module.set_history_enabled(True)

    def call(self, values: Dict, output_directory: str) -> Dict:
        return self._call_iteration(values, output_directory)

    def reset(self):
        self.history = []
        for module in self.modules:
            module.reset()

    def _call_iteration(self, values: Dict, output_directory: str) -> Dict:
        for i, module in enumerate(self.modules):
            if i in self.reset_history_at:
                print("reset History")
                self.history = []
            len_history: int = len(self.history)
            module.reset(True)
            module.set_history(self.history)
            values = module.call(values, output_directory)
            self.history = module.history
            if len(self.history) < len_history:
                raise ValueError('History did not increase!')
        return values