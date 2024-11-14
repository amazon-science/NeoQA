from typing import Optional, Dict, List, Set

from src.mglockne_story_line.llm.critiques.base_critique import BaseCritique
from src.mglockne_story_line.llm.critiques.modules.output_format_critique import OutputFormatCritique
from src.mglockne_story_line.llm.modules.parsable_base_module import ParsableBaseModule
from src.mglockne_story_line.llm.prompting.modules.nested_parsable_output_prompt import BasicNestedXMLParser
from src.mglockne_story_line.llm.prompting.parsable_prompt import ParsablePrompt
from src.mglockne_story_line.llm.wrapper.base_llm_wrapper import BaseLLMWrapper
from src.mglockne_story_line.story.event_sequence.elements.entity import Entity
from src.mglockne_story_line.story.event_sequence.modules.fictive_entities.entity_critiques.idfy_outline_critique import \
    IdfyOutlineCritique
from src.mglockne_story_line.story.event_sequence.modules.fictive_entities.entity_critiques.idfy_outline_too_many_ids_critique import \
    IdfyOutlineTooManyIdsCritique
from src.mglockne_story_line.util.entity_util import get_entity_categories
from src.mglockne_story_line.util.story_tools import renew_outline
from src.mglockne_story_line.util.xml_util import dict_to_xml

EXPECTED_OUTPUT_FORMAT: str = """
The output format is incorrect. Please output the results in the following format:
<outline>
<storyitem>First story item</storyitem>
<storyitem>Second story item</storyitem>
...
<storyitem>Last story item</storyitem>
</outline>
""".strip()


class IdfyOutlineWithNamedEntitiesModule(ParsableBaseModule):
    """
    This module adjusts the outline such that each named entity is detected and resolved.
    Each named entity is referred to via {phrase|ID}.
    """
    def _create_critiques(self) -> List[BaseCritique]:
        return [
            IdfyOutlineCritique('idfy-outline-critique', 3),
            IdfyOutlineTooManyIdsCritique()
        ]

    def __init__(self, llm: BaseLLMWrapper, name: str, instruction_name: str):
        super().__init__(
            llm,
            name,
            instruction_name,
            get_instructions(instruction_name),
            max_critiques=5
        )

    def _create_formatting_critique(self, parsers: List[BasicNestedXMLParser]) -> Optional[BaseCritique]:
        return OutputFormatCritique('format-idfy-outline', parsers, EXPECTED_OUTPUT_FORMAT)

    def _postprocess_values(self, values: Dict) -> Optional[Dict]:
        return super()._postprocess_values(values)

    def _get_parsers(self) -> List[BasicNestedXMLParser]:
        return [
            BasicNestedXMLParser('story_item', './/storyitem', is_object=False, result_node='outline'),
        ]

    def _preprocess_values(self, values) -> Dict:
        values = renew_outline(values)

        # Get XML for old and new entities
        for entity_type in get_entity_categories():
            pre_existing_entities: List[Entity] = values[entity_type]
            used_entity_ids: Set[str] = set([e['id'] for e in values[f'used_{entity_type}']])
            pre_existing_entities = [e for e in pre_existing_entities if e.entity_id in sorted(list(used_entity_ids))]
            pre_existing_entity_ids: Set[str] = {e.entity_id for e in pre_existing_entities}
            new_entities = [e | {"category": entity_type} for e in  values[f'used_{entity_type}'] if e['id'] not in pre_existing_entity_ids]

            values[f'used_pre-existing-{entity_type}'] = pre_existing_entities
            values[f'used_new-{entity_type}'] = new_entities
            values[f'all_used_{entity_type}_xml'] = '\n'.join(
                [e.xml() for e in pre_existing_entities] + [f'<{e["category"]}>' + dict_to_xml(e) + f'</{e["category"]}>' for e in new_entities]
            )
            values[f'used-name-and-id-for-{entity_type}'] = values[f'used_new-{entity_type}'] + [
                {'name': ent.name, 'id': ent.entity_id} for ent in values[f'used_pre-existing-{entity_type}']
            ]

        return values

    def get_file_name(self, prompt: ParsablePrompt, values: Dict):
        summary = values['EVENT_SUMMARY_FOR_NAME'].lower().replace(' ', '-')
        node_idx = values['CREATED_AT']
        return f'N{node_idx:02d}-{self.name}-{summary}_{self.instruction_name}.json'


INSTRUCTIONS_V1 = """
You are an AI assistant tasked with identifying and marking fictional entities within an outline of a fictional event. Your goal is to replace each occurrence of these entities with a specific format that includes the entity's ID. Follow these instructions carefully:

You will be working with two inputs:

Date: {{DATE}}
<outline>
{{OUTLINE}}
</outline>

<entities>
{{ALL_USED_LOCATION_XML}}
{{ALL_USED_PERSON_XML}}
{{ALL_USED_ORGANIZATION_XML}}
{{ALL_USED_PRODUCT_XML}}
{{ALL_USED_ART_XML}}
{{ALL_USED_BUILDING_XML}}
{{ALL_USED_EVENT_XML}}
{{ALL_USED_MISCELLANEOUS_XML}}
</entities>

Process the outline by following these steps:

1. Carefully review the list of entities provided in the <entities> section. Each entity will have an associated ID.

2. Search the outline for all occurrences of each entity in the list.

3. For each occurrence found, replace it with the format: {phrase|ID}
   Where "phrase" is exactly how the entity appears in the text (maintaining any abbreviations or variations), and "ID" is the entity's identifier from the entities list.

4. Maintain the original structure and formatting of the outline, only changing the entities as described.

5. After processing all entities, review the entire outline to ensure all occurrences have been properly marked and no entities were missed.

6. Output the processed outline, maintaining its original structure but with all entity occurrences replaced as instructed.

Important points to remember:
- Be thorough in your search for entities, including variations or partial mentions.
- Preserve the original text exactly as it appears, only adding the entity markup.
- Keep the COMPLETE phrase that you are replacing with {phrase|ID}. The sentence should be identical to how it was before, except for the added markup.
- If an entity is referred to by full name, the "phrase" is the full name.
- If an entity is referred to by an abbreviation, the "phrase" is the used abbreviation.
- If an entity is referred to using parts of the full name, then the "phrase" would be the same parts of the full name.

Format your output as follows:
- Enclose the entire processed outline within <outline> tags.
- Place each sentence of the outline within separate <storyitem> tags.

Examples:
1. "Renowned novelist Elara Vance and celebrated philanthropist Rohan Kapoor exchanged vows." 
   Should be replaced with:
   "Renowned novelist {Elara Vance|PERSON-1} and celebrated philanthropist {Rohan Kapoor|PERSON-2} exchanged vows."
   (When Elara Vance has ID PERSON-1 and Rohan Kapoor has ID PERSON-2)

2. "Renowned novelist Elara and celebrated philanthropist R. Kapoor exchanged vows." 
   Should be replaced with:
   "Renowned novelist {Elara|PERSON-1} and celebrated philanthropist {R. Kapoor|PERSON-2} exchanged vows."

Provide your final output without any additional commentary or explanations. Focus solely on processing the outline as instructed.
"""


INSTRUCTIONS_FULL1 = """
You are an AI assistant tasked with identifying and marking fictional entities within an outline of a fictional event. Your goal is to replace each occurrence of these entities with a specific format that includes the entity's ID. Follow these instructions carefully:

You will be working with the following inputs:

Date: {{DATE}}

<outline>
{{OUTLINE}}
</outline>

<entities>
{{ALL_USED_LOCATION_XML}}
{{ALL_USED_PERSON_XML}}
{{ALL_USED_ORGANIZATION_XML}}
{{ALL_USED_PRODUCT_XML}}
{{ALL_USED_ART_XML}}
{{ALL_USED_BUILDING_XML}}
{{ALL_USED_EVENT_XML}}
{{ALL_USED_MISCELLANEOUS_XML}}
</entities>

Process the outline by following these steps:

1. Carefully review the list of entities provided in the <entities> section. Each entity will have an associated ID and a name.

2. Search the outline for all occurrences of each entity in the list.

3. For each occurrence found, replace it with the format: {full name|ID}
   Where "full name" is the full name as provided via the "name" property of the entity.
   
4. Maintain the original structure and formatting of the outline, only changing the entities as described.

5. After processing all entities, review the entire outline to ensure all occurrences have been properly marked and no entities were missed.

6. Output the processed outline, maintaining its original structure but with all entity occurrences replaced as instructed.

Important points to remember:
- Be thorough in your search for entities, including variations or partial mentions.
- Always use the ID and name as provided in the entity list, even:
    - If an entity is referred to by full name
    - If an entity is referred to by an abbreviation
    - If an entity is referred to using parts of the full name

Format your output as follows:
- Enclose the entire processed outline within <outline> tags.
- Place each sentence of the outline within separate <storyitem> tags.

Provide your final output without any additional commentary or explanations. Focus solely on processing the outline as instructed.
"""

def get_instructions(version):
    if version == 'v1':
        out = INSTRUCTIONS_V1
    elif version == 'full1':
        out = INSTRUCTIONS_FULL1
    else:
        raise ValueError(version)
    return out.strip()