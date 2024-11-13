from collections import defaultdict
from typing import Dict, List, Set

from data_gen.llm.critiques.base_critique import BaseCritique
from data_gen.llm.critiques.output_format_critique import OutputFormatCritique
from data_gen.llm.critiques.wiki_field_critique import WikiFieldCritique
from data_gen.llm.modules.parsable_base_module import ParsableBaseModule
from data_gen.llm.prompting.modules.nested_parsable_output_prompt import BasicNestedXMLParser
from data_gen.llm.prompting.parsable_prompt import ParsablePrompt
from data_gen.llm.wrapper.base_llm_wrapper import BaseLLMWrapper
from data_gen.timelines.event_sequence.modules.fictive_entities.entity_critiques.entity_name_formatting_critique import \
    EntityNameFormattingCritique
from data_gen.timelines.event_sequence.modules.fictive_entities.entity_critiques.fixed_entity_names_disjunct_critique import \
    CheckThatDifferentNamedEntitiesHaveDifferentNamesCritique
from data_gen.timelines.event_sequence.modules.fictive_entities.entity_critiques.fixed_entity_names_disjunct_with_previous_critique import \
    CheckThatDifferentNamedEntitiesHaveDifferentNamesAsPreviousNamedEntitiesCritique
from data_gen.timelines.event_sequence.modules.fictive_entities.entity_critiques.fixed_entity_names_not_too_long_critique import \
    FixedNameWordCountCritique
from data_gen.util.entity_util import get_entity_categories
from data_gen.util.misc import find_object_by_prop


def _make_xml_entities_from_start(values: Dict, issues: List[Dict]) -> Dict:
    for key in get_entity_categories():
        entity_issues: List[str] = [err['obj']['name'] for issue in issues for err in issue['errors'] if key in issue['name']]
        entity_issues = list(set(entity_issues))
        names_xml: List[str] = sorted([f'<{key}>{e}</{key}>' for e in entity_issues])
        values[f'{key}s_name_xml'] = '\n'.join(names_xml)
    return values


EXPECTED_OUTPUT_FORMAT = """
<results>
  <location>
    <name>[New Location Name]</name>
    <old_name>[Original Location Name]</old_name>
  </location>
  <organization>
    <name>[New Organization Name]</name>
    <old_name>[Original Organization Name]</old_name>
  </organization>
  <person>
    <name>[New Person Name]</name>
    <old_name>[Original Person Name]</old_name>
  </person>
  <product>
    <name>[New Product Name]</name>
    <old_name>[Original Product Name]</old_name>
  </product>
  <art>
    <name>[New Art Name]</name>
    <old_name>[Original Art Name]</old_name>
  </art>
  <building>
    <name>[New Building Name]</name>
    <old_name>[Original Building Name]</old_name>
  </building>
  <event>
    <name>[New Event Name]</name>
    <old_name>[Original Event Name]</old_name>
  </event>
  <miscellaneous>
    <name>[New Miscellaneous Item Name]</name>
    <old_name>[Original Miscellaneous Item Name]</old_name>
  </miscellaneous>
</results>
""".strip()


class ChangeNamedEntityNamesModule(ParsableBaseModule):
    """
    This module changes the name of the named entities to be disjunct with Wikipedia.
    """

    def __init__(self, llm: BaseLLMWrapper, name: str, instruction_name: str):
        super().__init__(
            llm,
            name,
            instruction_name,
            get_instructions(instruction_name),
            is_correction_module=True,
            max_critiques=10
        )
        self.output_instructions: str = "Output all the new entities. For entities that didn't require adjustment, keep the original name and set old_name to name."
        self.old_names: Dict[str, Set[str]] = defaultdict(set)
        self.print_prompt = False

    def _create_formatting_critique(self, parsers: List[BasicNestedXMLParser]) -> BaseCritique:
        return OutputFormatCritique('format-entity-fix-names', parsers, EXPECTED_OUTPUT_FORMAT)

    def reset(self, history_enabled: bool = False):
        super().reset(history_enabled)
        self.old_names: Dict[str, Set[str]] = defaultdict(set)

    def _preprocess_values(self, values) -> Dict:
        # Initialize the corrected with the new entities.
        # The corrected entities will be verified and updated
        # The new_entities will be checked each time.
        for key in get_entity_categories():
            values[f'corrected_{key}_name'] = []

            unique_names: Set[str] = set()
            for new_entity in values[f'new_{key}_name']:
                self.old_names[key].add(new_entity['name'])
                if new_entity['name'].strip() not in unique_names:
                    values[f'corrected_{key}_name'].append({
                        'name': new_entity['name'], 'old_name': new_entity['name']
                    })
                    unique_names.add(new_entity['name'].strip())

        return super()._preprocess_values(values)

    def _on_start_validated_found_errors(self, values: Dict, issues: List[Dict]):
        # Prepare variables for prompting
        values = _make_xml_entities_from_start(values, issues)

        return values

    def on_called(self, values: Dict) -> Dict:
        for key in get_entity_categories():
            corrected_entities: List[Dict] = values[f'corrected_{key}_name']
            for new_entity in values[f'new_{key}_name']:
                print('new_entity >>>', new_entity)
                corrected: Dict = find_object_by_prop(corrected_entities, 'old_name', new_entity['old_name'])
                corrected['name'] = new_entity['name']

        return values

    def _create_critiques(self) -> List[BaseCritique]:

        wiki_disjunct_critiques: List[BaseCritique] = [
            WikiFieldCritique('name', f'entity-{entity_type}', f'corrected_{entity_type}_name', entity_type)
            for entity_type in get_entity_categories()
        ]

        wiki_name_formatting_critique: List[BaseCritique] = [
            EntityNameFormattingCritique('name', f'format-{entity_type}', f'corrected_{entity_type}_name', entity_type)
            for entity_type in get_entity_categories()
        ]

        return wiki_disjunct_critiques + wiki_name_formatting_critique + [
            CheckThatDifferentNamedEntitiesHaveDifferentNamesAsPreviousNamedEntitiesCritique(),
            CheckThatDifferentNamedEntitiesHaveDifferentNamesCritique(),
            FixedNameWordCountCritique()
        ]

    def get_file_name(self, prompt: ParsablePrompt, values: Dict):
        summary = values['EVENT_SUMMARY_FOR_NAME'].lower().replace(' ', '-')
        node_idx = values['CREATED_AT']
        return f'N{node_idx:02d}-{self.name}-{summary}_{self.instruction_name}.json'

    def _get_parsers(self) -> List[BasicNestedXMLParser]:
        return [
            BasicNestedXMLParser(
                f'new_{entity_type}_name', f'.//{entity_type}', is_object=True, additional_locators_for_robustness=[
                    f'.//{entity_type}/{entity_type}',
                    f'.//{entity_type}s/{entity_type}'
                ]
            )
            for entity_type in get_entity_categories()
        ]



INSTRUCTIONS_V1 = """
You are an AI assistant tasked with renaming a list of entities to ensure they are distinct from any known real-world or fictional names. This task is crucial for creating original content that doesn't infringe on existing intellectual property or cause confusion with real entities.

You will be provided with eight lists of names to be renamed: locations, organizations, persons, products, art, buildings, events, and miscellaneous items. These are presented in XML format as follows:

Entity names to change:
<entity_names>
{{LOCATIONS_NAME_XML}}
{{ORGANIZATIONS_NAME_XML}}
{{PERSONS_NAME_XML}}
{{PRODUCTS_NAME_XML}}
{{ARTS_NAME_XML}}
{{BUILDINGS_NAME_XML}}
{{EVENTS_NAME_XML}}
{{MISCELLANEOUSS_NAME_XML}}
</entity_names>

Follow these steps to complete the task:

1. For each entity in the lists, create a new name that is different from the original but maintains a similar style or feel. The new name must be fictional, but it must sound realistic. Avoid names that are clearly fictional.

2. Ensure that the new names are not associated with any known real-world or fictional entities. This includes names of people, places, organizations, products, artworks, buildings, events, or characters from books, movies, or other media.

3. When creating new names:
   - For locations: Maintain a geographical feel appropriate to the original name's region.
   - For organizations: Keep a professional or institutional tone similar to the original.
   - For persons: Preserve the cultural or ethnic flavor of the original name if applicable. If only a first name is provided, consider adding the lastname. If only a first name is provided, consider adding a last name. Ensure consistency in naming, particularly with inter-personal relations. For example, children should have the same last name as their parents, and married people often share the same last name.
   - For products: Retain a similar market appeal and product category feel.
   - For art: Maintain the artistic style or genre suggested by the original name.
   - For buildings: Keep architectural or functional implications of the original name.
   - For events: Preserve the nature or purpose of the event in the new name.
   - For miscellaneous items: Retain the essence or category of the original item.

4. Avoid using common words, phrases, or combinations that might accidentally reference existing entities.

5. For each renamed entity, provide both the new name and the old name.

6. Output your results in the following XML format:

<results>
  <location>
    <name>[New Location Name]</name>
    <old_name>[Original Location Name]</old_name>
  </location>
  <organization>
    <name>[New Organization Name]</name>
    <old_name>[Original Organization Name]</old_name>
  </organization>
  <person>
    <name>[New Person Name]</name>
    <old_name>[Original Person Name]</old_name>
  </person>
  <product>
    <name>[New Product Name]</name>
    <old_name>[Original Product Name]</old_name>
  </product>
  <art>
    <name>[New Art Name]</name>
    <old_name>[Original Art Name]</old_name>
  </art>
  <building>
    <name>[New Building Name]</name>
    <old_name>[Original Building Name]</old_name>
  </building>
  <event>
    <name>[New Event Name]</name>
    <old_name>[Original Event Name]</old_name>
  </event>
  <miscellaneous>
    <name>[New Miscellaneous Item Name]</name>
    <old_name>[Original Miscellaneous Item Name]</old_name>
  </miscellaneous>
</results>

Here's an example of how your output should look:

<results>
  <location>
    <name>Emerald Heights</name>
    <old_name>Green Valley</old_name>
  </location>
  <organization>
    <name>Quantum Dynamics Corporation</name>
    <old_name>Particle Physics Institute</old_name>
  </organization>
  <person>
    <name>Zara Blackwood</name>
    <old_name>Emma Stone</old_name>
  </person>
  <product>
    <name>SonicWave X1</name>
    <old_name>iPod</old_name>
  </product>
  <art>
    <name>Whispers of Eternity</name>
    <old_name>Starry Night</old_name>
  </art>
  <building>
    <name>Pinnacle Tower</name>
    <old_name>Empire State Building</old_name>
  </building>
  <event>
    <name>Global Harmony Festival</name>
    <old_name>Woodstock</old_name>
  </event>
  <miscellaneous>
    <name>LumiGlow Orb</name>
    <old_name>Lava Lamp</old_name>
  </miscellaneous>
</results>

Remember to create unique names for each entity and ensure they don't match any known entities. Provide your complete list of renamed entities in the specified XML format. When coming up with new names, try to keep them sounding realistic and appropriate to their category (location, organization, person, product, art, building, event, or miscellaneous).

Begin your renaming process now, and present your results in the format specified above. You may use a <scratchpad> section within the <results> tags to show your thinking process if needed. All actual results should be listed in <location>, <organization>, <person>, <product>, <art>, <building>, <event>, or <miscellaneous> nodes within the <results> node.

Do not include any content outside of the <results> tags in your response.

ONLY change the names of the entities listed under entity names to change. Do not invent any other entities. Do not change the names of any other entities.
"""

def get_instructions(version):
    if version == 'v1':
        out = INSTRUCTIONS_V1
    else:
        raise ValueError(version)
    return out.strip()