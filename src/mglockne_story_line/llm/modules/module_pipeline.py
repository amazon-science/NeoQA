
from typing import List, Optional, Dict

from src.mglockne_story_line.llm.modules.callable_module import CallableModule


class ModulePipeline:
    """
    Applies multiple modules in sequence.
    Modules share and update a values dictionary.
    """
    def __init__(self, modules: List[CallableModule]):
        self.modules: List[CallableModule] = modules

    def execute(self, output_directory: str, initial_status: Optional[Dict] = None) -> Dict:
        status: Dict = initial_status or dict()
        for module in self.modules:
            module.reset()
            status = module.call(status, output_directory)
            if not status['is_valid']:
                print("Stopping early because of invalid results!")
                break
        return status

