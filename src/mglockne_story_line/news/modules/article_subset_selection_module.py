from typing import List, Dict, Optional

from src.mglockne_story_line.llm.critiques.base_critique import BaseCritique
from src.mglockne_story_line.llm.modules.parsable_base_module import ParsableBaseModule
from src.mglockne_story_line.llm.prompting.modules.nested_parsable_output_prompt import BasicNestedXMLParser
from src.mglockne_story_line.llm.prompting.parsable_prompt import ParsablePrompt
from src.mglockne_story_line.llm.wrapper.base_llm_wrapper import BaseLLMWrapper
from src.mglockne_story_line.news.critiques.ensure_all_selected_ids_are_valid_and_from_same_event_critique import \
    EnsureAllSelectedIdsAreValidAndFromSameEventCritique
from src.mglockne_story_line.news.news_profiles.get_newspaper_profile import get_newspaper_profile_prompt


class ArticleSubsetSelectionModule(ParsableBaseModule):

    def _create_critiques(self) -> List[BaseCritique]:
        return [
            EnsureAllSelectedIdsAreValidAndFromSameEventCritique()
        ]

    def _postprocess_values(self, values: Dict) -> Optional[Dict]:
        cleaned_subsets = []
        for subset in values['subsets']:
            ids = sorted(
                list(set([_id.strip() for _id in subset.split(',')])),
                key = lambda _id: int(_id.split('-S')[1])
            )
            assert len(ids) > 0
            cleaned_subsets.append(ids)
        values['subsets'] = cleaned_subsets

        return super()._postprocess_values(values)

    def __init__(self, llm: BaseLLMWrapper, name: str, instruction_name: str):
        super().__init__(
            llm,
            name,
            instruction_name,
            get_instructions(instruction_name),
        )

    def _preprocess_values(self, values) -> Dict:
        return super()._preprocess_values(values)

    def _get_parsers(self) -> List[BasicNestedXMLParser]:
        return [
            BasicNestedXMLParser('subsets', './/subset', is_object=False, to_single=False, result_node='results'),
        ]

    def get_file_name(self, prompt: ParsablePrompt, values: Dict):
        node_idx = values['CREATED_AT']
        newspaper_name = values['NEWSPAPER_PROFILE']
        return f'N{node_idx:02d}-{self.name}-{newspaper_name}_{self.instruction_name}.json'

    def _get_system_prompt(self, values: Dict) -> Optional[str]:
        return get_newspaper_profile_prompt(values['NEWSPAPER_PROFILE'])


INSTRUCTIONS_V1 = """
You are tasked with selecting subsets of sentences from a fictional current event to be integrated into a fictional news story. You will be provided with the following inputs:

1. An optional {{HISTORY}} of fictional events from the past
2. A {{CURRENT_EVENT}} describing the current fictional event you are working with
3. The number of subsets {{NUM_SUBSETS}} to create

First, review the optional history of past events:

<history>
{{HISTORY}}
</history>

Now, examine the current event:

<current_event>
{{CURRENT_EVENT}}
</current_event>

Each sentence in the current event has a unique ID. Your task is to analyze the current event and select subsets of sentences that would be suitable for integration into a fictional news story.

To complete this task:

1. Carefully read and understand the current event.
2. Consider which sentences are most important or newsworthy.
3. Think about how different combinations of sentences could create coherent and interesting news stories.
4. Create {{NUM_SUBSETS}} distinct subsets of sentences, ensuring that each subset tells a slightly different aspect or perspective of the event.

For each subset:
- Select a group of sentence IDs that, when combined, would create a compelling news story.
- Ensure that the selected sentences provide enough context and detail to understand the main points of the event.
- Avoid redundant information within each subset.

Output your results in the following format:

<results>
<subset>[Comma-separated list of sentence IDs]</subset>
<subset>[Comma-separated list of sentence IDs]</subset>
...
</results>

Repeat the <subset> element {{NUM_SUBSETS}} times, each containing a unique selection of sentence IDs.

Remember to create distinct subsets that capture different aspects of the story. Your goal is to provide versatile options for creating varied news stories from the same event.
"""


INSTRUCTIONS_V2 = """
You are an AI assistant tasked with selecting subsets of sentences from a fictional current event to be integrated into a fictional news story. Your goal is to create versatile options for varied news stories from the same event. Follow these instructions carefully:

1. Review the optional history of past events:
<history>
{{HISTORY}}
</history>

2. Examine the current event:
<current_event>
{{CURRENT_EVENT}}
</current_event>

3. Analyze the current event:
   - Read and understand the content thoroughly.
   - Identify the most important or newsworthy sentences.
   - Consider how different combinations of sentences could create coherent and interesting news stories.
   - Think about which content aligns well with what you want to communicate in your newspaper, and which content should be omitted.

4. Create {{NUM_SUBSETS}} distinct subsets of sentences, following these guidelines:
   - Select groups of sentence IDs that, when combined, would create compelling news stories.
   - Ensure each subset tells a slightly different aspect or perspective of the event.
   - Include enough context and detail in each subset to understand the main points.
   - Avoid redundant information within each subset.
   - Consider your newspaper's profile when selecting the content to focus on.

5. Output your results in the following format:
<results>
<subset>[Comma-separated list of sentence IDs]</subset>
</results>

Repeat the <subset> element {{NUM_SUBSETS}} times, each containing a unique selection of sentence IDs.

6. Remember to create distinct subsets that capture different aspects of the story. Your goal is to provide versatile options for creating varied news stories from the same event.

Before providing your final answer, use a <scratchpad> to think through your selection process and ensure you're creating diverse and meaningful subsets.
"""


def get_instructions(version):
    if version == 'v1':
        out = INSTRUCTIONS_V1
    elif version == 'v2':
        out = INSTRUCTIONS_V2
    else:
        raise ValueError(version)

    return out.strip()
