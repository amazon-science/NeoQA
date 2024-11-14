from copy import deepcopy
from typing import Optional, Dict, List

from src.mglockne_story_line.llm.modules.named_module_pipeline import NamedModulePipeline
from src.mglockne_story_line.questions.elements.qa_pair import QAPair


class QuestionReviser:
    """
    Use as input to a question generator to additionally create new questions based on the already created questions.
    these questions have their own modules.
    """
    def __init__(
            self,
            output_key: str,
            question_generation_module: NamedModulePipeline,
            question_refine_module: Optional[NamedModulePipeline] = None
    ):
        self.output_key: str = output_key
        self.question_generation_module: NamedModulePipeline = question_generation_module
        self.question_refine_module: Optional[NamedModulePipeline] = question_refine_module

    def run(self, values: Dict, directory: str) -> Dict:
        if self.output_key in values:
            raise ValueError(f'Expected to generate  a new value for "{self.output_key}" but this property already exists!')
        values = self.question_generation_module.execute(directory, values)
        if self.question_refine_module is not None:
            values = self.question_refine_module.execute(directory, values)
        return values

    def get_qa_pairs(self, values: Dict, storyline: Dict, parent_qa_pair: QAPair) -> List[QAPair]:
        raise NotImplementedError

