from typing import List, Dict, Optional

from data_gen.llm.modules.module_pipeline import ModulePipeline
from data_gen.llm.modules.parsable_base_module import ParsableBaseModule


class NamedModulePipeline(ModulePipeline):
    """
    Pipeline version that can output a name.
    """
    def __init__(self, modules: List[ParsableBaseModule], name: str, enable_history: bool = False):
        super().__init__(modules)
        self.name: str = name
        self.modules: List[ParsableBaseModule] = modules
        self.enable_history: bool = enable_history

    def execute(self, output_directory: str, initial_status: Optional[Dict] = None) -> Dict:
        if not self.enable_history:
            return super().execute(output_directory, initial_status)
        else:
            values: Dict = initial_status or dict()
            current_history: List = []
            for i, module in enumerate(self.modules):
                len_history: int = len(current_history)
                module.reset(True)
                module.set_history(current_history)
                values = module.call(values, output_directory)
                current_history = module.history
                if len(current_history) < len_history:
                    raise ValueError('History did not increase!')
            return values

    def get_content_versions(self) -> List[Dict]:
        return [
            {
                'module_name': module.name,
                'instruction_name': module.instruction_name
            }
            for module in self.modules
        ]
