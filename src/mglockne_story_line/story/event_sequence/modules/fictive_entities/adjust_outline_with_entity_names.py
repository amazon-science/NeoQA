from typing import Dict, List

from src.mglockne_story_line.llm.critiques.base_critique import BaseCritique
from src.mglockne_story_line.llm.critiques.modules.output_format_critique import OutputFormatCritique
from src.mglockne_story_line.llm.modules.parsable_base_module import ParsableBaseModule
from src.mglockne_story_line.llm.prompting.modules.nested_parsable_output_prompt import BasicNestedXMLParser
from src.mglockne_story_line.llm.prompting.parsable_prompt import ParsablePrompt
from src.mglockne_story_line.llm.wrapper.base_llm_wrapper import BaseLLMWrapper
from src.mglockne_story_line.util.entity_util import get_entity_categories
from src.mglockne_story_line.story.event_sequence.modules.fictive_entities.entity_critiques.entity_outline_fix_critique import \
    HeuristicallyVerifyNamedEntitiesAreChangedCritique
from src.mglockne_story_line.util.xml_util import dict_to_xml


EXPECTED_OUTPUT_FORMAT = """
<results>
<storyitem>[Updated sentence 1]</storyitem>
<storyitem>[Updated sentence 2]</storyitem>
...
<storyitem>[Updated sentence n]</storyitem>
</results>
""".strip()


class ResolveFoundNamedEntityConflictsInOutlineModule(ParsableBaseModule):
    """
    This module makes adjustments to the outline by changing the name of all named entities which needed
    to be renamed due to conflicts with Wikipedia.
    """
    def spy_on_output(self, output: Dict):
        super().spy_on_output(output)

    def _create_critiques(self) -> List[BaseCritique]:
        return [HeuristicallyVerifyNamedEntitiesAreChangedCritique('avoid-old-names-in-outline')]

    def _get_parsers(self) -> List[BasicNestedXMLParser]:
        return [
            BasicNestedXMLParser('story_item', './/storyitem', is_object=False, result_node='results'),
        ]

    def _create_formatting_critique(self, parsers: List[BasicNestedXMLParser]) -> BaseCritique:
        return OutputFormatCritique('format-adjust-outline', parsers, EXPECTED_OUTPUT_FORMAT)

    def _preprocess_values(self, values) -> Dict:
        num_corrected: int = 0
        for key in get_entity_categories():
            corrected_entities: List[Dict] = values[f'corrected_{key}_name']
            corrected_entities = [e for e in corrected_entities if e['name'] != e['old_name']]
            num_corrected += len(corrected_entities)
            values[f'adjusted_{key}s_xml'] = '\n'.join([f'<{key}>{dict_to_xml(e)}</{key}>' for e in corrected_entities])

        if num_corrected == 0:
            self.skip = True
        else:
            self.skip = False
        return values

    def get_file_name(self, prompt: ParsablePrompt, values: Dict):
        summary = values['EVENT_SUMMARY_FOR_NAME'].lower().replace(' ', '-')
        node_idx = values['CREATED_AT']
        return f'N{node_idx:02d}-{self.name}-{summary}_{self.instruction_name}.json'

    def __init__(self, llm: BaseLLMWrapper, name: str, instruction_name: str):
        super().__init__(
            llm,
            name,
            instruction_name,
            get_instructions(instruction_name)
        )

INSTRUCTIONS_V3 = """
You are an AI assistant tasked with updating an OUTLINE to be consistent with new entity names. Your goal is to make minimal changes while ensuring all entity names are updated correctly. Follow these instructions carefully:

First, here are the entities for which the names have been changed:

<entities>
<adjusted_locations>
{{ADJUSTED_LOCATIONS_XML}}
</adjusted_locations>
<adjusted_persons>
{{ADJUSTED_PERSONS_XML}}
</adjusted_persons>
<adjusted_organizations>
{{ADJUSTED_ORGANIZATIONS_XML}}
</adjusted_organizations>
<adjusted_products>
{{ADJUSTED_PRODUCTS_XML}}
</adjusted_products>
<adjusted_arts>
{{ADJUSTED_ARTS_XML}}
</adjusted_arts>
<adjusted_buildings>
{{ADJUSTED_BUILDINGS_XML}}
</adjusted_buildings>
<adjusted_events>
{{ADJUSTED_EVENTS_XML}}
</adjusted_events>
<adjusted_miscellaneouss>
{{ADJUSTED_MISCELLANEOUSS_XML}}
</adjusted_miscellaneouss>
</entities>

Your task is to update the OUTLINE to be consistent with the new names of these entities. Follow these instructions carefully:

1. Make minimal changes to the outline. Only update the names of entities that have been changed.
2. Apply changes on each sentence individually.
3. Output each updated sentence as a separate <storyitem>.
4. If a sentence does not contain any entities that need to be changed, output it as is.
5. Ensure that you maintain the original structure and content of the OUTLINE, changing only the necessary entity names.
6. Always use the full name as defined by the "name" property of the entities.

Output format:
Place all your outputs in a root node <results>. Do not output any content outside of this root node. Each sentence should be in its own <storyitem> tag. Your output should look like this:

<results>
<storyitem>[Updated sentence 1]</storyitem>
<storyitem>[Updated sentence 2]</storyitem>
...
<storyitem>[Updated sentence n]</storyitem>
</results>

Important reminders:
- Make only the necessary changes to reflect the new entity names while preserving the original meaning and structure of each sentence.
- Ensure that all entity name changes are consistent with the provided data for locations, persons, organizations, products, art, buildings, events, and miscellaneous items.
- Double-check your work to make sure you haven't missed any entity name changes or accidentally modified any content that should remain unchanged.

Now, here is the OUTLINE to update:

Date: {DATE}
<outline>
{OUTLINE}
</outline>

Process each sentence in the OUTLINE, updating entity names as necessary, and output the results as instructed above.

DO NOT include the date as a storyitem.
"""


INSTRUCTIONS_V2 = """
You are an AI assistant tasked with updating an OUTLINE to be consistent with new entity names. Your goal is to make minimal changes while ensuring all entity names are updated correctly. Follow these instructions carefully:

First, here are the entities for which the names have been changed:

<entities>
<adjusted_locations>
{{ADJUSTED_LOCATIONS_XML}}
</adjusted_locations>
<adjusted_persons>
{{ADJUSTED_PERSONS_XML}}
</adjusted_persons>
<adjusted_organizations>
{{ADJUSTED_ORGANIZATIONS_XML}}
</adjusted_organizations>
<adjusted_products>
{{ADJUSTED_PRODUCTS_XML}}
</adjusted_products>
<adjusted_arts>
{{ADJUSTED_ARTS_XML}}
</adjusted_arts>
<adjusted_buildings>
{{ADJUSTED_BUILDINGS_XML}}
</adjusted_buildings>
<adjusted_events>
{{ADJUSTED_EVENTS_XML}}
</adjusted_events>
<adjusted_miscellaneouss>
{{ADJUSTED_MISCELLANEOUSS_XML}}
</adjusted_miscellaneouss>
</entities>

Your task is to update the OUTLINE to be consistent with the new names of these entities. Follow these instructions carefully:

1. Make minimal changes to the outline. Only update the names of entities that have been changed.
2. Apply changes on each sentence individually.
3. Output each updated sentence as a separate <storyitem>.
4. If a sentence does not contain any entities that need to be changed, output it as is.
5. Ensure that you maintain the original structure and content of the OUTLINE, changing only the necessary entity names.
6. Do not remove or modify any abbreviations present in the original OUTLINE. Make sure all existing abbreviations in the new outline make sense with the updated entities!

Output format:
Place all your outputs in a root node <results>. Do not output any content outside of this root node. Each sentence should be in its own <storyitem> tag. Your output should look like this:

<results>
<storyitem>[Updated sentence 1]</storyitem>
<storyitem>[Updated sentence 2]</storyitem>
...
<storyitem>[Updated sentence n]</storyitem>
</results>

Important reminders:
- Make only the necessary changes to reflect the new entity names while preserving the original meaning and structure of each sentence.
- Do not remove or modify any abbreviations present in the original OUTLINE.
- Ensure that all entity name changes are consistent with the provided XML data for locations, persons, organizations, products, art, buildings, events, and miscellaneous items.
- Double-check your work to make sure you haven't missed any entity name changes or accidentally modified any content that should remain unchanged.

Now, here is the OUTLINE to update:

Date: {{DATE}}
<outline>
{{OUTLINE}}
</outline>

Process each sentence in the OUTLINE, updating entity names as necessary, and output the results as instructed above.

DO NOT include the date as a storyitem.
"""

INSTRUCTIONS_V1 = """
You are an AI assistant tasked with updating an OUTLINE to be consistent with new entity names. Your goal is to make minimal changes while ensuring all entity names are updated correctly. Follow these instructions carefully:

First, here are the entities for which the names have been changed:

<entities>
{{ADJUSTED_LOCATIONS_XML}}
{{ADJUSTED_PERSONS_XML}}
{{ADJUSTED_ORGANIZATIONS_XML}}
{{ADJUSTED_PRODUCTS_XML}}
{{ADJUSTED_ARTS_XML}}
{{ADJUSTED_BUILDINGS_XML}}
{{ADJUSTED_EVENTS_XML}}
{{ADJUSTED_MISCELLANEOUSS_XML}}
</entities>

Your task is to update the OUTLINE to be consistent with the new names of these entities. Follow these instructions carefully:

1. Make minimal changes to the outline. Only update the names of entities that have been changed.
2. Apply changes on each sentence individually.
3. Output each updated sentence as a separate <storyitem>.
4. If a sentence does not contain any entities that need to be changed, output it as is.
5. Ensure that you maintain the original structure and content of the OUTLINE, changing only the necessary entity names.
6. Do not remove or modify any abbreviations present in the original OUTLINE. Make sure all existing abbreviations in the new outline make sense with the updated entities!

Output format:
Place all your outputs in a root node <results>. Do not output any content outside of this root node. Each sentence should be in its own <storyitem> tag. Your output should look like this:

<results>
<storyitem>[Updated sentence 1]</storyitem>
<storyitem>[Updated sentence 2]</storyitem>
...
<storyitem>[Updated sentence n]</storyitem>
</results>

Important reminders:
- Make only the necessary changes to reflect the new entity names while preserving the original meaning and structure of each sentence.
- Do not remove or modify any abbreviations present in the original OUTLINE.
- Ensure that all entity name changes are consistent with the provided XML data for locations, persons, organizations, products, art, buildings, events, and miscellaneous items.
- Double-check your work to make sure you haven't missed any entity name changes or accidentally modified any content that should remain unchanged.

Now, here is the OUTLINE to update:

Date: {{DATE}}
<outline>
{{OUTLINE}}
</outline>

Process each sentence in the OUTLINE, updating entity names as necessary, and output the results as instructed above.
"""


def get_instructions(version):
    if version == 'v1':
        out = INSTRUCTIONS_V1
    elif version == 'v2':
        out = INSTRUCTIONS_V2
    elif version == 'v3':
        out = INSTRUCTIONS_V3
    else:
        raise ValueError(version)
    return out.strip()