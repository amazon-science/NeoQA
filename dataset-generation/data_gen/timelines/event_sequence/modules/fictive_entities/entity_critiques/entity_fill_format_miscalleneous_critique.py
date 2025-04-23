import re
from typing import Dict, Optional

from data_gen.llm.critiques.critique_result import CritiqueResult
from data_gen.llm.critiques.parsable_root_node_critique import ParsableRootNodeCritique


class EntityFillFormatMiscellaneousCritique(ParsableRootNodeCritique):

    """
    Double-checks by name and ID that all new entities have been filled.
    """

    def __init__(self, root_node: str, remove_node: Optional[str] = None, no_elaboration: bool = False):
        super().__init__(root_node, remove_node, no_elaboration)

    def process(self, values: Dict) -> CritiqueResult:

        response: str = values['response']
        has_double_misc: bool = bool(re.search(r'<miscellaneous>\s*<miscellaneous>', response))

        if has_double_misc:
            print(response)
            # new_response: str = re.sub(r'<miscellaneous>\s*<miscellaneous>', '<miscellaneous>', values['response'])
            # new_response: str = re.sub(r'</miscellaneous>\s*</miscellaneous>', '</miscellaneous>', new_response)
            # values['response'] = new_response
            # print('Changed response to::::')
            # print(values['response'])
            return CritiqueResult('nested-misc', False, [{'nested-misc': True}], "It seems you have nested the named entities incorrectly. Please list each named entity directly under the root node <results>. Avoid placing <miscellaneous> entities within another nested <miscellaneous> node.")

        return super().process(values)
