from typing import List, Dict, Optional

from src.mglockne_story_line.llm.critiques.base_critique import BaseCritique
from src.mglockne_story_line.llm.critiques.modules.output_format_critique import OutputFormatCritique
from src.mglockne_story_line.llm.modules.parsable_base_module import ParsableBaseModule
from src.mglockne_story_line.llm.prompting.modules.nested_parsable_output_prompt import BasicNestedXMLParser
from src.mglockne_story_line.llm.prompting.parsable_prompt import ParsablePrompt
from src.mglockne_story_line.llm.wrapper.base_llm_wrapper import BaseLLMWrapper
from src.mglockne_story_line.questions.question_generator import QuestionGenerator

EXPECTED_OUTPUT_FORMAT: str = """
<items>
<id>[ID of the first selected item]</id>
<id>[ID of the second selected item]</id>
<id>[ID of the third selected item]</id>
...
</items>
""".strip()

class SimpleQuestionSentenceSelectionModule(ParsableBaseModule):

    def _postprocess_values(self, values: Dict) -> Optional[Dict]:
        values[QuestionGenerator.VAL_SELECTIONS] = values['selected_id']
        return values

    def __init__(self, llm: BaseLLMWrapper, name: str, instruction_name: str):
        super().__init__(
            llm,
            name,
            instruction_name,
            get_instructions(instruction_name),
        )

    def _create_critiques(self) -> List[BaseCritique]:
        return []

    def _create_formatting_critique(self, parsers: List[BasicNestedXMLParser]) -> Optional[BaseCritique]:
        return OutputFormatCritique('format-select-specifics', parsers, EXPECTED_OUTPUT_FORMAT)

    def _preprocess_values(self, values) -> Dict:
        return values

    def _get_parsers(self) -> List[BasicNestedXMLParser]:
        return [
            BasicNestedXMLParser('selected_id', './/id', is_object=False, allow_empty_list=False, result_node='items')
        ]

    def get_file_name(self, prompt: ParsablePrompt, values: Dict):
        node_idx: int = values['CREATED_AT']
        return f'N{node_idx:02d}-{self.name}_{self.instruction_name}.json'


def get_instructions(version: str) -> str:

    if version == 'v1':
        out: str = INSTRUCTIONS_V1
    else:
        raise ValueError(version)
    return out.strip()


INSTRUCTIONS_V1 = """
You are tasked with identifying the most specific items from an outline about a fictional event. Your goal is to select items that contain very specific and unique information.

Here is the outline you will be working with:
<outline>
{{OUTLINE}}
</outline>

To complete this task, follow these steps:

1. Carefully read through each <item> in the outline.
2. Look for items that contain very specific and unique information. These might include:
   - Precise numbers or statistics
   - Exact dates or times
   - Specific names of people, places, or things
   - Detailed descriptions of events or processes
   - Unique or unusual facts

3. As you read, keep track of the items you think are most specific. You will need to select {{NUM_ITEMS}} items in total.

4. Once you have reviewed all items, narrow down your selection to the {{NUM_ITEMS}} most specific items.

5. For your final output, you will only need to provide the <id> of each selected item.

Before providing your final answer, use the <scratchpad> tags to think through your selection process. Consider why you chose certain items over others and ensure you have selected the {{NUM_ITEMS}} most specific items.

When you're ready, provide your final selection in the following format:

<items>
<id>[ID of the first selected item]</id>
<id>[ID of the second selected item]</id>
<id>[ID of the third selected item]</id>
...
</items>

Remember to include exactly {{NUM_ITEMS}} items in your final selection.
"""
