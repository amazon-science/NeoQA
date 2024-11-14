from typing import Optional, Dict, List, Set

from src.mglockne_story_line.llm.modules.parsable_base_module import ParsableBaseModule
from src.mglockne_story_line.llm.prompting.modules.nested_parsable_output_prompt import BasicNestedXMLParser
from src.mglockne_story_line.llm.prompting.parsable_prompt import ParsablePrompt
from src.mglockne_story_line.llm.wrapper.base_llm_wrapper import BaseLLMWrapper
from src.mglockne_story_line.story.event_sequence.elements.entity import Entity
from src.mglockne_story_line.util.entity_util import get_entity_categories, get_entity_by_id


class IdfyEntities(ParsableBaseModule):
    def reset(self, history_enabled: bool = False):
        super().reset(history_enabled)
        i=1

    def __init__(self, llm: BaseLLMWrapper, name: str, instruction_name: str):
        super().__init__(
            llm,
            name,
            instruction_name,
            get_instructions(instruction_name)
        )


    def _postprocess_values(self, values: Dict) -> Dict:
        for entity_type in get_entity_categories():
            idfy_entries: List[Dict] = values[f'idfy_{entity_type}']
            entities: List[Entity] = values[entity_type]
            for entry in idfy_entries:
                entity: Entity = get_entity_by_id(entities, entry['id'])
                entity.idfy_last_update(entry)
        return values


    def _get_parsers(self) -> List[BasicNestedXMLParser]:
        return [
            BasicNestedXMLParser(f'idfy_{entity_type}', f'.//{entity_type}', is_object=True, result_node='results')
            for entity_type in get_entity_categories()
        ]

    def _preprocess_values(self, values) -> Dict:
        for entity_type in get_entity_categories():
            # We only update the used entities with ALL previous entities
            used_entities: List[Entity] = values[f'used-all-{entity_type}']
            values[f'all_used_{entity_type}_xml'] = '\n'.join(
                [e.last_update_xml() for e in used_entities]
            )
            all_entities: List[Entity] = values[entity_type]
            values[f'{entity_type}s_xml'] = '\n'.join([
                ent.xml() for ent in all_entities
            ])
        self.print_prompt =  True

        return values

    def get_file_name(self, prompt: ParsablePrompt, values: Dict):
        summary = values['EVENT_SUMMARY_FOR_NAME'].lower().replace(' ', '-')
        node_idx = values['CREATED_AT']
        return f'N{node_idx:02d}-entity-props-idfy-{summary}_{self.instruction_name}.json'


INSTRUCTIONS_V2 = """
You are an AI assistant tasked with updating references to entities within a subset of fictional entities. Follow these instructions carefully:

1. First, you will be given a full list of fictional entities:

<full_entity_list>
{{LOCATIONS_XML}}
{{PERSONS_XML}}
{{ORGANIZATIONS_XML}}
{{PRODUCTS_XML}}
{{ARTS_XML}}
{{EVENTS_XML}}
{{BUILDINGS_XML}}
{{MISCELLANEOUSS_XML}}
</full_entity_list>

2. Next, you will be given a subset of these entities that need to be processed:

<current_subset_entities>
{{ALL_USED_LOCATION_XML}}
{{ALL_USED_PERSON_XML}}
{{ALL_USED_ORGANIZATION_XML}}
{{ALL_USED_PRODUCT_XML}}
{{ALL_USED_ART_XML}}
{{ALL_USED_BUILDING_XML}}
{{ALL_USED_EVENT_XML}}
{{ALL_USED_MISCELLANEOUS_XML}}
</current_subset_entities>

3. Your task is to go through each entity in the current subset and update certain properties to include references to other known entities. Here's what you need to do:

   a. For each entity in the current subset, examine all properties except for ID, name, entity_class, type, last_updated, and created_at.
   
   b. In each of these properties, look for phrases that refer to any of the known entities (including the entity itself) from the full entity list.
   
   c. If you find a reference to a known entity, replace the phrase with the format: "{[phrase]|[ID of entity]}".
   
   d. Do not change any content that is not a reference to a known entity.
   
   e. If an entity already uses the "{[phrase]|[ID of entity]}" format, do not modify it.
   
   f. Double-check in all fields that each known entity for which an [ID] was provided is properly formatted as "{[phrase]|[ID of entity]}"

4. Here's an example of how to process an entity:

   Original entity:
   <building>
   <id>BUILDING-1</id>
   <name>Eiffel Bridge</name>
   <description>The Eiffel Bridge was destroyed by Marco Ludano during the Great War.</description>
   </building>

   Known entities:
   <person>
   <id>PERSON-12</id>
   <name>Marco Ludano</name>
   </person>
   <event>
   <id>EVENT-3</id>
   <name>Great War</name>
   </event>

   Updated entity:
   <building>
   <id>BUILDING-1</id>
   <name>Eiffel Bridge</name>
   <description>The {Eiffel Bridge|BUILDING-1} was destroyed by {Marco Ludano|PERSON-12} during the {Great War|EVENT-3}.</description>
   </building>

5. Provide your output in the following format:

   <processed_entities>
   [Include all processed entities here, with updated references]
   </processed_entities>

6. Additional instructions:
   - Only modify the entities in the current subset.
   - Only update references to known entities from the full list.
   - Maintain all other content and formatting exactly as provided.
   - Output everything in a single root node called <results>

Remember to carefully review each entity in the current subset and update all relevant references to known entities from the full list.
"""

def get_instructions(version):
    if version == 'v2':
        out = INSTRUCTIONS_V2
    else:
        raise ValueError(version)
    return out.strip()