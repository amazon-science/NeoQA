from typing import List, Dict, Optional

from src.mglockne_story_line.llm.critiques.base_critique import BaseCritique
from src.mglockne_story_line.llm.critiques.modules.output_format_critique import OutputFormatCritique
from src.mglockne_story_line.llm.modules.parsable_base_module import ParsableBaseModule
from src.mglockne_story_line.llm.prompting.modules.nested_parsable_output_prompt import BasicNestedXMLParser
from src.mglockne_story_line.llm.prompting.parsable_prompt import ParsablePrompt
from src.mglockne_story_line.llm.verifiers.named_unified_output_verifier import NamedUnifiedOutputVerifier
from src.mglockne_story_line.llm.wrapper.base_llm_wrapper import BaseLLMWrapper
from src.mglockne_story_line.util.story_tools import renew_outline

EXPECTED_OUTPUT_FORMAT: str = """
The output format is incorrect. Please output the results in the following format:
<outline>
<storyitem>First story item</storyitem>
<storyitem>Second story item</storyitem>
...
<storyitem>Last story item</storyitem>
</outline>
""".strip()


class OutlineRefiner(ParsableBaseModule):


    def _create_formatting_critique(self, parsers: List[BasicNestedXMLParser]) -> Optional[BaseCritique]:
        return OutputFormatCritique('format-refine-outline', parsers, EXPECTED_OUTPUT_FORMAT)

    def _postprocess_values(self, values: Dict) -> Optional[Dict]:
        values[self.key_naming] += 1
        return values

    def __init__(self, llm: BaseLLMWrapper, name: str, instruction_name: str, key_naming: str = 'KEY_OUTLINE_REFINE_STEP'):
        super().__init__(
            llm,
            name,
            instruction_name,
            get_instructions(instruction_name),
        )
        self.key_naming: str = key_naming

    def _preprocess_values(self, values) -> Dict:
        return renew_outline(values)

    def _get_verifiers(self) -> List[NamedUnifiedOutputVerifier]:
        return []

    def _get_parsers(self) -> List[BasicNestedXMLParser]:
        return [
            BasicNestedXMLParser('story_item', './/storyitem', is_object=False, allow_empty_list=False),
        ]

    def get_file_name(self, prompt: ParsablePrompt, values: Dict):
        headline = values['EVENT_SUMMARY_FOR_NAME'].lower().replace(' ', '-')
        step: int = values[self.key_naming]
        node_idx = values['CREATED_AT']
        return f'N{node_idx:02d}-{self.name}-{step}-{headline}_{self.instruction_name}.json'


INSTRUCTIONS_V3 = """
You are an AI assistant tasked with analyzing a fictional event summary and its corresponding outline to produce a list of atomic storyitems. Follow these instructions carefully:

First, read the provided fictional event summary:

<event_summary>
{{EVENT_SUMMARY}}
</event_summary>

Now, review the outline of the article:

<outline>
{{OUTLINE}}
</outline>

Your task is to transform the provided outline into atomic storyitems. For each sentence or point in the outline:
1. Identify all atomic / individual information pieces such as facts, actions, or other specific details.
2. List each of these information pieces as a short, concise, specific single sentence that only communicates this single piece of information.

Each storyitem must:
- Communicate only ONE fact, piece of information, or sub-event
- Be written as a concise, objective, factual statement
- Be faithful to the provided outline without introducing unwarranted new information
- Collectively cover all information from the outline without loss of content

Format your response as follows:

<storyitems>
<storyitem>[Insert first storyitem here]</storyitem>
<storyitem>[Insert second storyitem here]</storyitem>
<storyitem>[Continue with additional storyitems as needed]</storyitem>
</storyitems>

Important points to remember:
1. Base your storyitems primarily on the information provided in the outline.
2. Use the event summary as context, but do not include information from it unless it's also present in the outline or is a reasonable fictional addition.
3. Ensure that your storyitems are faithful representations of the outline content or provide specific supplementary information.

For any output within the XML nodes, make sure to escape the content properly!
"""

INSTRUCTIONS_V2 = """
You are an AI assistant tasked with analyzing a fictional event summary and its corresponding outline to produce a list of atomic storyitems. Follow these instructions carefully:

First, read the provided fictional event summary:

<event_summary>
{{EVENT_SUMMARY}}
</event_summary>

Now, review the outline of the article:

<outline>
{{OUTLINE}}
</outline>

Your task is to transform the provided outline into atomic storyitems. For each sentence or point in the outline:
1. Identify all atomic / individual information pieces such as facts, actions, or other specific details.
2. List each of these information pieces as a short, concise, specific single sentence that only communicates this single piece of information.

Each storyitem must:
- Communicate only ONE fact, piece of information, or sub-event
- Be written as a concise, objective, factual statement
- Be faithful to the provided outline without introducing unwarranted new information
- Collectively cover all information from the outline without loss of content

Format your response as follows:

<storyitems>
<storyitem>[Insert first storyitem here]</storyitem>
<storyitem>[Insert second storyitem here]</storyitem>
<storyitem>[Continue with additional storyitems as needed]</storyitem>
</storyitems>

Important points to remember:
1. Base your storyitems primarily on the information provided in the outline.
2. Use the event summary as context, but do not include information from it unless it's also present in the outline or is a reasonable fictional addition.
3. Ensure that your storyitems are faithful representations of the outline content or provide specific supplementary information.
4. Aim for completeness and specificity in your storyitems, breaking down complex sentences into multiple atomic pieces of information.
5. The storyitems must fully capture the content of the outline.
6. Separate any relative clauses or appositives that provide additional information into separate storyitems.

Before finalizing your response, follow these steps:
1. Create an initial list of storyitems based on the outline.
2. Review each storyitem to ensure it contains only one piece of information. If a storyitem contains multiple pieces of information, break it down further.
3. Cross-check your storyitems against the outline to ensure all information has been captured.
4. If any information from the outline is missing, add new storyitems to cover it.
5. Review your storyitems once more to ensure they are concise, specific, and faithful to the outline.

Once you have completed these steps, present your final list of storyitems within the <storyitems> tags as shown in the format above. Remember, each storyitem should contain only one piece of information and collectively they should fully represent the content of the outline.
"""


INSTRUCTIONS_V1 = """
You are an AI assistant tasked with analyzing a fictional event summary and its corresponding outline to produce a list of atomic storyitems. Follow these instructions carefully:

First, read the provided fictional event summary:

<event_summary>
{{EVENT_SUMMARY}}
</event_summary>

Now, review the outline of the article:

<outline>
{{OUTLINE}}
</outline>

Your task is to transform the provided outline into atomic storyitems. For each sentence in the outline:
1. Identify all atomic / individual information pieces such as facts, actions, or other specific details.
2. List each of these information pieces as a short, concise, specific single sentence that only communicates this single piece of information.

Each storyitem must:
- Communicate only ONE fact, piece of information, or sub-event
- Be written as a concise, objective, factual statement
- Be faithful to the provided outline without introducing unwarranted new information
- Collectively cover all information from the outline without loss of content

If you believe some key information (facts) are missing, you can add fictional facts as additional story items. When adding fictional facts:
- Ensure they do not increase the scope of the event
- Only provide additional specific details to the event
- Make sure they are consistent with the other facts in the outline
- Write each additional fact as a separate storyitem

Format your response as follows:

<storyitems>
<storyitem>[Insert first storyitem here]</storyitem>
<storyitem>[Insert second storyitem here]</storyitem>
<storyitem>[Continue with additional storyitems as needed]</storyitem>
</storyitems>

Important points to remember:
1. Base your storyitems primarily on the information provided in the outline.
3. Ensure that your storyitems are faithful representations of the outline content or provide specific supplementary information.
4. Aim for completeness and specificity in your storyitems, breaking down complex sentences into multiple atomic pieces of information.
5. The storyitems must fully capture the content of the outline.
6. If specific details should be added, each specific detail can be added as a separate concise, short and atomic story item.
7. Separate any relative clauses or appositives that provide additional information into separate storyitems.

Begin your analysis and creation of storyitems now. Remember to include all storyitems within the <storyitems> tags as shown in the format above. Ensure that each storyitem really only contains one piece of information.
"""

INSTRUCTIONS_V4 = """
You are an AI assistant tasked with analyzing a fictional event summary and its corresponding outline to produce a list of atomic storyitems. Follow these instructions carefully:

First, read the provided fictional event summary:

<event_summary>
{{EVENT_SUMMARY}}
</event_summary>

Now, review the outline of the event:

Date: {{DATE}}
<outline>
{{OUTLINE}}
</outline>

Your task is to transform the provided outline into atomic storyitems. For each sentence in the outline:
1. Identify all atomic / individual information pieces such as facts, actions, or other specific details.
2. List each of these information pieces as a short, concise, specific single sentence that only communicates this single piece of information. Note that a single sentence in the OUTLINE can communicate multiple different story items. You must separate them and list them separately.

Each storyitem must:
- Communicate only ONE fact, piece of information, or sub-event
- Be written as a concise, objective, factual statement
- Be faithful to the provided outline without introducing unwarranted new information
- Collectively cover all information from the outline without loss of content
- Make sure to break up complex or long sentences from the OUTLINE into multiple concise storyitems.

Format your response as follows:

<storyitems>
<storyitem>[Insert first storyitem here]</storyitem>
<storyitem>[Insert second storyitem here]</storyitem>
<storyitem>[Continue with additional storyitems as needed]</storyitem>
</storyitems>

Important points to remember:
1. Base your storyitems on the information provided in the outline.
2. Ensure that your storyitems are faithful representations of the outline content or provide specific supplementary information.
3. Aim for completeness and specificity in your storyitems, breaking down complex sentences into multiple atomic pieces of information.
4. The storyitems must fully capture the content of the outline.
5. Separate any relative clauses or appositives that provide additional information into separate storyitems.

Begin your analysis and creation of storyitems now. Remember to include all storyitems within the <storyitems> tags as shown in the format above. Ensure that each storyitem really only contains one piece of information.
"""



def get_instructions(version: str) -> str:
    if version == 'v1':
        out: str = INSTRUCTIONS_V1
    elif version == 'v4':
        out: str = INSTRUCTIONS_V4
    else:
        raise ValueError(version)
    return out.strip()
