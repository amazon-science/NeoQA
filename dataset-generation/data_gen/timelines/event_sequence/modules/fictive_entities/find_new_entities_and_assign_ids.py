from typing import Optional, Dict, List

from data_gen.llm.critiques.base_critique import BaseCritique
from data_gen.llm.critiques.output_format_critique import OutputFormatCritique
from data_gen.llm.modules.parsable_base_module import ParsableBaseModule
from data_gen.llm.prompting.modules.nested_parsable_output_prompt import BasicNestedXMLParser
from data_gen.llm.prompting.parsable_prompt import ParsablePrompt
from data_gen.llm.wrapper.base_llm_wrapper import BaseLLMWrapper
from data_gen.timelines.event_sequence.modules.fictive_entities.entity_critiques.find_and_id_used_entities_critique import \
    FindUsedEntitiesCritique
from data_gen.util.entity_util import get_entity_categories, EntityIdProvider
from data_gen.util.story_tools import renew_outline
from data_gen.util.xml_util import dict_to_xml

EXPECTED_OUTPUT_FORMAT: str = """
<results>
<entities>
[List all identified entities here as <[entity_type]>[content]</[entity_type]> nodes.]
</entities>
</results>
"""


class FindNewAndOldEntitiesWithIDs(ParsableBaseModule):
    """
    This module identifies the old and the newly introduced named entities in the outline. While this is
    somewhat redundant (since we have detected named entities previously) this task is specifically about their detection
    with all known named entities, excluding any other factors that may distract the LLM from this main task.
    """
    def spy_on_output(self, output: Dict):
        super().spy_on_output(output)

    def _create_formatting_critique(self, parsers: List[BasicNestedXMLParser]) -> Optional[BaseCritique]:
        return OutputFormatCritique('format-find-used-entities', parsers, EXPECTED_OUTPUT_FORMAT, min_number_results_total=1)

    def _create_critiques(self) -> List[BaseCritique]:
        return [FindUsedEntitiesCritique('find-used-entities-critique')]

    def _postprocess_values(self, values: Dict) -> Optional[Dict]:
        return super()._postprocess_values(values)

    def _get_parsers(self) -> List[BasicNestedXMLParser]:
        return [
            BasicNestedXMLParser(f'used_{entity_type}', f'.//entities/{entity_type}', is_object=True, result_node='results')
            for entity_type in get_entity_categories()
        ]

    def _preprocess_values(self, values) -> Dict:
        # ID ids
        values = renew_outline(values)
        id_provider: EntityIdProvider = EntityIdProvider(values['next_ids'])
        for entity_type in get_entity_categories():
            new_entity_names: List[Dict] = values[f'corrected_{entity_type}_name']
            for entity in new_entity_names:
                entity['id'] = id_provider.get_id(entity_type)
            # Update the XML version
            values[f'adjusted_{entity_type}s_xml'] = '\n'.join([f'<{entity_type}>{dict_to_xml(e)}</{entity_type}>' for e in new_entity_names])
        values['next_ids'] = id_provider.export()
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
You are an AI assistant tasked with identifying which of the provided entities are explicitly named within the provided outline. Follow these instructions carefully:

1. The date for this fictional event outline is:
<date>{{DATE}}</date>

2. Here is the outline you need to analyze:
<outline>
{{OUTLINE}}
</outline>

3. Here is the list of known (fictional) named entities:
<entities>
{{LOCATIONS_XML}}
{{PERSONS_XML}}
{{ORGANIZATIONS_XML}}
{{PRODUCTS_XML}}
{{ARTS_XML}}
{{EVENTS_XML}}
{{BUILDINGS_XML}}
{{MISCELLANEOUSS_XML}}

{{ADJUSTED_LOCATIONS_XML}}
{{ADJUSTED_PERSONS_XML}}
{{ADJUSTED_ORGANIZATIONS_XML}}
{{ADJUSTED_PRODUCTS_XML}}
{{ADJUSTED_ARTS_XML}}
{{ADJUSTED_BUILDINGS_XML}}
{{ADJUSTED_EVENTS_XML}}
{{ADJUSTED_MISCELLANEOUSS_XML}}
</entities>

4. Your task is to go through all of the named entities in the provided list. For each named entity, check if it is explicitly referred to by name in the outline. If a named entity is explicitly mentioned by name, include it in your results.

5. For each entity you identify, list them using the following format:
<[entity_type]><id>[id of the entity]</id><name>[full name of the entity]</name></[entity_type]>

6. Present your final output within a single <results> root node, structured as follows:

<results>
<entities>
[List all identified entities here as described in step 5]
</entities>
</results>

7. Double-check your work: For each entity that you have identified, make sure to find the sentence within the outline that explicitly refers to this identified entity by name. If you cannot find that the entity is mentioned explicitly by name in the outline, do not include it in your results.

8. You can use a <scratchpad> for your thinking process. Do not include any XML tags within your scratchpad.

9. Make sure that you have not missed any named entity from the outline that was also provided to you in the list of named entities.

Remember, only include entities that are explicitly mentioned by name in the outline. Do not infer or assume the presence of entities that are not directly named.
"""

def get_instructions(version):

    if version == 'v3':
        out = INSTRUCTIONS_V3
    else:
        raise ValueError(version)
    return out.strip()
