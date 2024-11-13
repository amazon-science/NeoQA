from typing import List, Optional, Dict

from data_gen.llm.critiques.base_critique import BaseCritique
from data_gen.llm.critiques.critique_result import CritiqueResult
from data_gen.llm.critiques.output_format_critique import OutputFormatCritique
from data_gen.llm.modules.parsable_base_module import ParsableBaseModule
from data_gen.llm.prompting.modules.nested_parsable_output_prompt import BasicNestedXMLParser
from data_gen.llm.prompting.parsable_prompt import ParsablePrompt
from data_gen.llm.wrapper.base_llm_wrapper import BaseLLMWrapper

EXPECTED_OUTPUT_FORMAT: str = """
The output format is incorrect. Please output the results in the following format:
<results>
<storyitems>
<storyitem>First story item</storyitem>
<storyitem>Second story item</storyitem>
...
<storyitem>Last story item</storyitem>
</storyitems>
</results>
""".strip()


class AllStoryItemsKeptCritique(BaseCritique):
    def process(self, values: Dict) -> CritiqueResult:
        expected_number_story_items: int = values['pre-consistency-num-items']
        actual_number_story_items: int = len(values['story_item'])
        if expected_number_story_items == actual_number_story_items:
            return CritiqueResult.correct(self.name)
        else:
            error_message: str = f'The original outline contained {expected_number_story_items} storyitems, but your response included only {actual_number_story_items}. Please ensure the refined outline includes all the original storyitems, even those you did not alter. Do not add any new storyitems. Remember to make only minimal changes to the original storyitems to ensure consistency.'
            return CritiqueResult(
                self.name, False, [{
                    'expected': expected_number_story_items, 'actual': actual_number_story_items
                }], error_message
            )

    def __init__(self):
        super().__init__('all-storyitems-kept-critique')

class CheckOutlineConsistencyModule(ParsableBaseModule):
    """
    This module checks (and corrects) the consistency of the outline.
    """

    def _create_critiques(self) -> List[BaseCritique]:
        return [AllStoryItemsKeptCritique()]

    def _create_formatting_critique(self, parsers: List[BasicNestedXMLParser]) -> Optional[BaseCritique]:
        return OutputFormatCritique('format-consistency-outline', parsers, EXPECTED_OUTPUT_FORMAT)

    def __init__(self, llm: BaseLLMWrapper, name: str, instruction_name: str, key_naming: str = 'KEY_OUTLINE_REFINE_STEP'):
        super().__init__(
            llm,
            name,
            instruction_name,
            get_instructions(instruction_name),
        )
        self.key_naming: str = key_naming

    def _preprocess_values(self, values) -> Dict:
        values['pre-consistency-num-items'] = len(values['story_item'])
        values['STORYITEM_XML'] = f'<storyitems>\n'
        values['STORYITEM_XML'] += '\n'.join([
            f'<storyitem>{sent}</storyitem>' for sent in values['story_item']
        ])
        values['STORYITEM_XML'] += f'\n<storyitems>'
        return values

    def _get_parsers(self) -> List[BasicNestedXMLParser]:
        return [
            BasicNestedXMLParser(
                'story_item', './/storyitem', is_object=False, allow_empty_list=False,
                result_node='results', remove_node='scratchpad'
            ),
        ]

    def get_file_name(self, prompt: ParsablePrompt, values: Dict):
        headline = values['EVENT_SUMMARY_FOR_NAME'].lower().replace(' ', '-')
        node_idx = values['CREATED_AT']
        return f'N{node_idx:02d}-{self.name}-{headline}_{self.instruction_name}.json'


def get_instructions(version: str) -> str:
    if version == 'v1':
        out: str = INSTRUCTIONS_V1
    else:
        raise ValueError(version)
    return out.strip()

INSTRUCTIONS_V1 = """
You are an AI assistant tasked with checking the consistency of a fictional story outline with previously established entities and events. Your goal is to ensure that the new outline is a consistent continuation of the previous events in the history.

You will be provided with three key pieces of information:

1. A list of fictional entities:
<entities>
<LOCATIONS>
{{LOCATIONS_XML}}
</LOCATIONS>

<PERSONS>
{{PERSONS_XML}}
</PERSONS>

<ORGANIZATIONS>
{{ORGANIZATIONS_XML}}
</ORGANIZATIONS>

<PRODUCTS>
{{PRODUCTS_XML}}
</PRODUCTS>

<ARTS>
{{ARTS_XML}}
</ARTS>

<EVENTS>
{{EVENTS_XML}}
</EVENTS>

<BUILDINGS>
{{BUILDINGS_XML}}
</BUILDINGS>

<MISCELLANEOUS>
{{MISCELLANEOUSS_XML}}
</MISCELLANEOUS>
</entities>

2. A history of fictional events involving these entities:
<history>
{{HISTORY_XML}}
</history>

3. The date of the next fictional event: {{DATE}}

3. An outline describing the next fictional event:
<outline>
{{STORYITEM_XML}}
</outline>

Follow these steps to complete your task:

1. Carefully compare the events described in the outline with the events from the history. Look for any inconsistencies or contradictions.

2. Compare the named entities described in the outline with the list of provided named entities. Ensure they are consistent.

3. Note that changes to known named entities are acceptable if they are reasonably discussed within the outline.

4. If you find any inconsistencies or contradictions:
   a. Make minimal changes to the outline to resolve the issues.
   b. Ensure your changes maintain the original structure and flow of the outline as much as possible.
   c. Double-check after fixing the inconsistencies to ensure they no longer persist.

5. If the outline is consistent with the provided list of entities and previous events (i.e., not contradictory), output the outline without any changes.

Present your results in the following format:

<results>
<scratchpad>
[Your reasoning process, including any inconsistencies found and how you resolved them]
</scratchpad>
<storyitems>
<storyitem>[First story item from the outline, corrected if necessary]</storyitem>
<storyitem>[Second story item from the outline, corrected if necessary]</storyitem>
<storyitem>[Continue with additional story items as needed]</storyitem>
</storyitems>
</results>

Important reminders:
- Always refer to named entities using their full name as described by the "name" property.
- Remember that all events are fictional but should sound plausible and realistic.
- Your output must include all storyitems, whether you had adjusted them or not.
- Do not add new events or significantly alter the plot. Your task is to ensure consistency, not to rewrite the story.

If you cannot resolve an inconsistency without significantly changing the plot, note this in your scratchpad and leave the story item as is, highlighting the inconsistency.

Begin your analysis now, and provide your results in the format specified above.
"""