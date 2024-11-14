import re
from typing import Dict

import xml.etree.ElementTree as ET

from src.mglockne_story_line.llm.critiques.base_critique import BaseCritique, CritiqueResult


class ParsableRootNodeCritique(BaseCritique):
    """
    Checks that the root node is parsable and critiques otherwise.
    """

    def __init__(self, root_node: str):
        super().__init__('critique-parsable-xml')
        self.root_node: str = root_node

    def process(self, values: Dict) -> CritiqueResult:
        response: str = values['response']
        pattern = re.compile(r'(<' + self.root_node + '>[\w\W]+</' + self.root_node + '>)')
        match = re.search(pattern, response)
        if match:
            s = match.group(1)
            try:
                ET.fromstring(s)

                return CritiqueResult.correct(self.name)
            except:
                print('--------------------- Could not parse ----------')
                print(s)
                print('--------------end could not parse---------------')
                error_message: str = f"Please ensure that all XML within the <{self.root_node}> root node is valid and can be automatically parsed. DO NOT refer to any XML nodes during your thinking process. DO NOT use the characters '<' or '>' during your thinking process! Now provide only the corrected output in the correct format without any extra explanation!"
                return CritiqueResult(self.name, False, [{'missing_root_node': self.root_node}], error_message)
        else:
            error_message: str = f'Please provide all your results within a single <{self.root_node}> root node.'
            return CritiqueResult(self.name, False, [{'missing_root_node': self.root_node}], error_message)

