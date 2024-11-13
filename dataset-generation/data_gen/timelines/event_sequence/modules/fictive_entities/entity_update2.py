from copy import deepcopy
from typing import Optional, List, Dict


from data_gen.llm.critiques.base_critique import BaseCritique
from data_gen.llm.critiques.critique_result import CritiqueResult
from data_gen.llm.critiques.output_format_critique import OutputFormatCritique
from data_gen.llm.critiques.wiki_field_critique import CustomWikiFieldCritique
from data_gen.llm.modules.parsable_base_module import ParsableBaseModule
from data_gen.llm.prompting.modules.nested_parsable_output_prompt import BasicNestedXMLParser
from data_gen.llm.prompting.parsable_prompt import ParsablePrompt
from data_gen.llm.wrapper.base_llm_wrapper import BaseLLMWrapper
from data_gen.timelines.event_sequence.elements.entity import Entity
from data_gen.timelines.event_sequence.modules.fictive_entities.entity_critiques.ensure_all_entities_updated_critique import \
    EnsureAllEntitiesUpdatedCritique
from data_gen.timelines.event_sequence.modules.fictive_entities.entity_critiques.object_list_property_critique import \
    ObjectListPropertyCritique
from data_gen.util.entity_util import get_entity_categories, get_entity_fields, get_entity_by_id
from data_gen.util.misc import find_object_position_by_prop

EXPECTED_OUTPUT_FORMAT = """
<results>
<[entity_type]>
<entity_id>[Insert entity id here]</entity_id>
<update>[Insert your update sentence here]</update>
[List any properties that were changed, with their new values, using the format:]
<[property_name]>[new value]</[property_name]>
</[entity_type]>
[Repeat for each entity]
</results>
""".strip()


class UpdatedNameLengthCritique(BaseCritique):
    """
    Ensures that a filled entity object includes all required properties.
    """

    def __init__(self, name: str, selector: str, max_word_count: int = 5):
        super().__init__(name)
        self.selector: str = selector
        self.max_word_count: int = max_word_count

    def process(self, values: Dict) -> CritiqueResult:
        error_message: str = f"Please review the identified named entity names to ensure they are indeed unique and clearly defined names. Keep in mind that a named entity should not exceed {self.max_word_count} words:\n"
        errors: List[Dict] = []
        for entry in values[self.selector]:
            if 'name' in entry:
                name_len: int  = len(entry['name'].strip().split(' '))
                if name_len > self.max_word_count:
                    errors.append(entry)
                    error_message += f'\t- {entry["name"]}\n'
        if len(errors) == 0:
            return CritiqueResult.correct(self.name)
        else:
            return CritiqueResult(
                self.name, False, errors, error_message
            )


class UpdateNamedEntityEntriesModule(ParsableBaseModule):
    """
    This module updates all named entity entries based on what has happened in the outline.
    - Various properties of the named entities *may* change if this is a result of the outline.
    - One update sentence is *always* added to the named entity, describing their involvement in the outline.
    """

    def __init__(self, llm: BaseLLMWrapper, name: str, instruction_name: str):
        super().__init__(
            llm,
            name,
            instruction_name,
            get_instructions(instruction_name)
        )

    def _create_formatting_critique(self, parsers: List[BasicNestedXMLParser]) -> BaseCritique:
        return OutputFormatCritique('format-entity-update', parsers, EXPECTED_OUTPUT_FORMAT)

    def _create_critiques(self) -> List[BaseCritique]:
        # Wiki unique ritiques
        critiques: List[BaseCritique] = [
            CustomWikiFieldCritique(
                field_name, f'entity-{entity_type}-{field_name}', f'tmp_{entity_type}_updates', entity_type
            )
            for entity_type in get_entity_categories()
            for field_name in get_entity_fields(entity_type)

            # Allow name changes for person with conflicts.
            if not (entity_type == 'person' and field_name == 'name')
        ]

        critiques += [
            ObjectListPropertyCritique(f'entity-{entity_type}-properies', f'tmp_{entity_type}_updates', [
                'entity_id', 'update'
            ], field_id='entity_id', field_name=None)
            for entity_type in get_entity_categories()
        ]

        critiques += [EnsureAllEntitiesUpdatedCritique('all-entities-updated-critique')]

        critiques += [
            UpdatedNameLengthCritique(
                'check-name-length', f'tmp_{entity_type}_updates', 5)
            for entity_type in get_entity_categories()
        ]

        return critiques

    def _preprocess_values(self, values) -> Dict:

        for entity_type in get_entity_categories():
            values[f'used-all-{entity_type}'] = values[f'used_pre-existing-{entity_type}'] + values[f'fictional_new_{entity_type}s']
            values[f'used_{entity_type}_xml'] = '\n'.join([ent.xml() for ent in values[f'used-all-{entity_type}']])

        all_used_entities: List[Entity] = [
            ent for entity_type in get_entity_categories() for ent in values[f'used-all-{entity_type}']
        ]
        values['used_entities'] = [
            {
                "id": ent.entity_id,
                "name": ent.name,
                "entity_type": ent.entity_class,
                "new": ent.created_at == values['created_at']
            } for ent in all_used_entities
        ]

        return values

    def on_main_called(self, values: Dict):
        # COPY initially created values (will be checked)
        for entity_type in get_entity_categories():
            values[f'{entity_type}_updates'] = [deepcopy(update) for update in values[f'tmp_{entity_type}_updates']]
        return values

    def on_critique_called(self, values: Dict):
        # UPDATE only
        for entity_type in get_entity_categories():
            final_updates: List[Dict] = values[f'{entity_type}_updates']
            for update in values[f'tmp_{entity_type}_updates']:
                # Changed to "entity_id"
                final_update_pos: int = find_object_position_by_prop(final_updates, 'entity_id', update['entity_id'], allow_missing=True)
                if final_update_pos >= 0:
                    for key in update:
                        final_updates[final_update_pos][key] = update[key]
                else:
                    final_updates.append(deepcopy(update))
        return super().on_critique_called(values)

    def _postprocess_values(self, values: Dict) -> Optional[Dict]:

        date: str = values['date']
        created_at: int = values['created_at']

        for entity_type in get_entity_categories():
            updates: List[Dict] = values[f'{entity_type}_updates']
            entities: List[Entity] = values[f'used-all-{entity_type}']

            for update in updates:
                entity_id: str = update["entity_id"]
                entity: Entity = get_entity_by_id(entities, entity_id)
                update_message: str = update.pop('update')
                entity.update(
                    update_message, date, created_at, update
                )
                if entity.created_at == created_at:
                    values[entity_type].append(entity)
                else:
                    assert get_entity_by_id(values[entity_type], entity.entity_id) is not None, entity.entity_id

        return values

    def _get_parsers(self) -> List[BasicNestedXMLParser]:
        return [
            BasicNestedXMLParser(f'tmp_{entity_type}_updates', f'.//{entity_type}', is_object=True, result_node='results')
            for entity_type in get_entity_categories()
        ]

    def get_file_name(self, prompt: ParsablePrompt, values: Dict):
        summary = values['EVENT_SUMMARY_FOR_NAME'].lower().replace(' ', '-')
        node_idx = values['CREATED_AT']
        return f'N{node_idx:02d}-{self.name}-{summary}_{self.instruction_name}.json'



INSTRUCTIONS_V1 = """
You are an AI assistant tasked with updating a list of fictional entities based on an outline of events. Follow these instructions carefully to complete the task:

1. First, read the outline of the fictional event:
<outline>
{{OUTLINE}}
</outline>

2. Next, review the list of fictional entities:
<entities>
{{USED_LOCATION_XML}}
{{USED_PERSON_XML}}
{{USED_ORGANIZATION_XML}}
{{USED_PRODUCT_XML}}
{{USED_ART_XML}}
{{USED_EVENT_XML}}
{{USED_BUILDING_XML}}
{{USED_MISCELLANEOUS_XML}}
</entities>

3. For each entity in the list, follow these steps:
   a. Identify the entity's role in the outline. Create an update sentence describing how the entity was affected by or involved in the events described in the outline.
   b. Review all properties of the entity EXCEPT for "id", "created_at", "history", and "entity_class".
   c. For each property:
      - If the property does not need to be updated based on the outline, leave it as-is.
      - If the events or the time difference since the last update (last_updated) indicate that the value has changed, update it accordingly.
      - Ensure the new value is consistent with the outline, other entities, and plausible given the time difference.
   d. Do not alter the "description" field unless the current description is no longer valid after the events in the outline.

4. Output your results for each entity in the following format:
<results>
<[entity_type]>
<entity_id>[Insert entity id here]</entity_id>
<update>[Insert your update sentence here]</update>
[List any properties that were changed, with their new values, using the format:]
<[property_name]>[new value]</[property_name]>
</[entity_type]>
[Repeat for each entity]
</results>

5. Important reminders:
   - Stick to the information provided in the outline and entities list. Do not invent new details or events.
   - Ensure all updates and changes are consistent with the outline and with each other.
   - Be concise in your updates, focusing only on relevant changes.
   - If no properties need to be changed for an entity, do not include any property tags.
   - Process each entity in the order they are presented in the list.
   - Use the appropriate entity type tag (e.g., <location>, <person>, etc.) instead of <entity_update>.
   - Begin your response with the first entity update immediately, without any preamble.

All actual results should be listed in <location>, <organization>, <person>, <product>, <art>, <building>, <event>, or <miscellaneous> nodes within the <results> node.
Do not include any content outside of the <results> tags in your response.

Start processing the entities now, following the instructions and format provided above.
"""
def get_instructions(version):
    if version == 'v1':
        out = INSTRUCTIONS_V1
    else:
        raise ValueError(version)
    return out.strip()