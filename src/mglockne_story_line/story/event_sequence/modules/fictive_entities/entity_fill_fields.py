from copy import deepcopy
from typing import Optional, Dict, List, Set, Tuple

from src.mglockne_story_line.llm.critiques.base_critique import BaseCritique
from src.mglockne_story_line.story.event_sequence.modules.fictive_entities.entity_critiques.object_list_property_critique import ObjectListPropertyCritique
from src.mglockne_story_line.llm.critiques.modules.parsable_root_node_critique import ParsableRootNodeCritique
from src.mglockne_story_line.llm.critiques.modules.wiki_field_critique import CustomWikiFieldCritique
from src.mglockne_story_line.llm.modules.parsable_base_module import ParsableBaseModule
from src.mglockne_story_line.llm.prompting.modules.nested_parsable_output_prompt import BasicNestedXMLParser
from src.mglockne_story_line.llm.prompting.parsable_prompt import ParsablePrompt
from src.mglockne_story_line.llm.wrapper.base_llm_wrapper import BaseLLMWrapper
from src.mglockne_story_line.story.event_sequence.elements.entity import Entity
from src.mglockne_story_line.story.event_sequence.modules.fictive_entities.entity_critiques.ensure_all_entities_filled_critique import \
    EnsureAllEntitiesFilledCritique
from src.mglockne_story_line.story.event_sequence.modules.fictive_entities.entity_critiques.entry_field_format_heuristic_critique import \
    EntryFieldFormatHeuristics
from src.mglockne_story_line.util.entity_util import get_entity_categories, get_entity_category_from_id, \
    get_entity_fields
from src.mglockne_story_line.util.misc import find_object_position_by_prop
from src.mglockne_story_line.util.story_tools import renew_outline
from src.mglockne_story_line.util.xml_util import dict_to_xml


class PopulateNewNamedEntitiesModule(ParsableBaseModule):
    """
    This module fills the KB entries for all newly identified named entities.
    """

    def _create_formatting_critique(self, parsers: List[BasicNestedXMLParser]) -> Optional[BaseCritique]:
        return ParsableRootNodeCritique(root_node='results')

    def _preprocess_values(self, values) -> Dict:
        # To check if we can skip this module
        has_new: bool = False

        # Prepare updated list of all NEW entities for the prompt.
        for entity_type in get_entity_categories():

            # ALL known entities as XML
            all_known_entities: List[Entity] = values[entity_type]
            values[f'{entity_type}s_xml'] = '\n'.join([
                ent.xml() for ent in all_known_entities
            ])

            # Check if we have new entities
            num_new_entities: int = len(values[f'used_new-{entity_type}'])
            values[f'used_new-{entity_type}s_xml'] = '\n'.join([
                f'<{entity_type}>' + dict_to_xml(ent) + f'</{entity_type}>' for ent in values[f'used_new-{entity_type}']
            ])
            has_new = has_new or num_new_entities > 0

        # Update outline
        values = renew_outline(values)
        if not has_new:
            self.skip = True
            for key in get_entity_categories():
                values[f'fictional_new_{key}s'] = []
        else:
            self.skip = False
        return values

    def _postprocess_values(self, values: Dict) -> Optional[Dict]:
        # Create new entities!
        for entity_type in get_entity_categories():
            new_ids: Set[Tuple[str, str]] = {
                (ent['id'], ent['name']) for ent in values[f'used_new-{entity_type}']
            }
            values[f'fictional_new_{entity_type}s'] = [
                Entity.create_new(entity_type, ent, values['created_at'], ent['id'], values['date'])
                for ent in values[f'fictional_new_{entity_type}s']
                if len(ent) > 0 and (ent['id'], ent['name']) in new_ids
            ]
        return values

    def on_main_called(self, values: Dict):
        # COPY initially created values (will be checked)
        for key in get_entity_categories():
            values[f'fictional_new_{key}s'] = []
        for key in get_entity_categories():
            for ent in values[f'new_{key}']:
                entity_category: str = get_entity_category_from_id(key, ent['id'])
                values[f'fictional_new_{entity_category}s'].append(deepcopy(ent))
        return values

    def on_call_critiques(self, values: Dict, prompt: str) -> Dict:
        print('Call CRITIQUE:')
        print(prompt)
        print('--------\n')
        return values

    def on_critique_called(self, values: Dict):
        print('Critique DONE.')
        # UPDATE only
        for key in get_entity_categories():
            for ent in values[f'new_{key}']:
                corrected_key: str = get_entity_category_from_id(key, ent['id'])
                final_entities: List[Dict] = values[f'fictional_new_{corrected_key}s']
                final_ent_pos: int = find_object_position_by_prop(final_entities, 'id', ent['id'], allow_missing=True)
                if final_ent_pos < 0:
                    print('Entity:', ent)
                    raise ValueError('Double check if this is not just a renamed entity!')
                else:
                    # if final_entities[final_ent_pos]['name'] != ent['name']:
                    #     name1 = final_entities[final_ent_pos]['name']
                    #     name2 = ent['name']
                    #     raise ValueError(f'Name mismatch: "{name1}" vs "{name2}"!')
                    final_entities[final_ent_pos] = ent
        return super().on_critique_called(values)

    def _create_critiques(self) -> List[BaseCritique]:
        critiques: List[BaseCritique] = [
            CustomWikiFieldCritique(field_name, f'entity-{entity_type}-{field_name}', f'fictional_new_{entity_type}s', entity_type)
            for entity_type in get_entity_categories()
            for field_name in get_entity_fields(entity_type)
        ] + [EnsureAllEntitiesFilledCritique('all-entities-filled-critique')] + [
            ObjectListPropertyCritique(f'entity-{entity_type}-properies', f'fictional_new_{entity_type}s', [
                'id', 'name', 'description'
            ])
            for entity_type in get_entity_categories()
        ] + [
            EntryFieldFormatHeuristics(field_name, f'heuristics-{entity_type}-{field_name}', f'fictional_new_{entity_type}s', entity_type)
            for entity_type in get_entity_categories()
            for field_name in get_entity_fields(entity_type)
        ]
        return critiques

    def _get_parsers(self) -> List[BasicNestedXMLParser]:
        return [
            BasicNestedXMLParser(f'new_{entity_type}', f'.//{entity_type}', is_object=True, result_node='results')
            for entity_type in get_entity_categories()
        ]
        # return [
        #     BasicNestedXMLParser('new_location', './/location', is_object=True, result_node='results'),
        #     BasicNestedXMLParser('new_persona', './/persona', is_object=True, result_node='results'),
        #     BasicNestedXMLParser('new_organization', './/organization', is_object=True, result_node='results')
        # ]

    def get_file_name(self, prompt: ParsablePrompt, values: Dict):
        summary = values['EVENT_SUMMARY_FOR_NAME'].lower().replace(' ', '-')
        node_idx = values['CREATED_AT']
        return f'N{node_idx:02d}-{self.name}-{summary}_{self.instruction_name}.json'

    def __init__(self, llm: BaseLLMWrapper, name: str, instruction_name: str):
        super().__init__(
            llm,
            name,
            instruction_name,
            get_instructions(instruction_name),
            max_critiques=10
        )
        self.print_prompt = True



INSTRUCTIONS_V3 = """
You are an AI assistant tasked with creating fictional entities based on provided information. 
Your goal is to generate detailed, coherent, and realistic descriptions for new locations, persons, organizations, products, art, buildings, events, and miscellaneous entities. 
Follow these instructions carefully:

1. Review the existing entities (if provided):

<existing_entities>
{{LOCATIONS_XML}}
{{PERSONS_XML}}
{{ORGANIZATIONS_XML}}
{{PRODUCTS_XML}}
{{ARTS_XML}}
{{EVENTS_XML}}
{{BUILDINGS_XML}}
{{MISCELLANEOUSS_XML}}
</existing_entities>

2. Review the names of new entities to be created:
<new_entity_names>
{{USED_NEW-LOCATIONS_XML}}
{{USED_NEW-PERSONS_XML}}
{{USED_NEW-ORGANIZATIONS_XML}}
{{USED_NEW-PRODUCTS_XML}}
{{USED_NEW-ARTS_XML}}
{{USED_NEW-EVENTS_XML}}
{{USED_NEW-BUILDINGS_XML}}
{{USED_NEW-MISCELLANEOUSS_XML}}
</new_entity_names>

3. Carefully read the provided outline:

Date: {{DATE}}
<outline>
{{OUTLINE}}
</outline>

Based on the information provided, create detailed descriptions for each new entity following these guidelines:

General instructions:
- Ensure all created entities are entirely fictional and not similar to any real or known fictional entities.
- Maintain realism and coherence with the provided outline and other entities.
- Create a believable and consistent fictional world that aligns with the context of the outline.
- For entity descriptions, focus on providing a solid background that remains valid throughout the story, rather than basing it centrally on the outline itself.
- Develop well-rounded entities with backgrounds and characteristics that can support various potential story developments beyond the specific outline provided.
- Strictly derive all entities from the outline. Do not invent entities that are not mentioned in the outline.
- Do not alter the name of the entities.
- Some properties (e.g., place, city, country, spouse, architect, country, nationality) must be filled with named entities. Make sure to use FICTIONAL named entities ( fictional places, cities, countries, spouse names, architects, countries, nationalities, etc.). Check if you should use one of the existing fictional named entities (from <new_entity_names> and <existing_entities>) or create a fictional name instead. DO NOT say that any of the entities or properties are fictional. It is important that everything seems realistic!
- Avoid exaggerating the named entities. They can be ordinary and don’t need to be world-class or state-of-the-art.
- Ensure the details of the named entities are realistic. If global impact isn’t necessary, adjust the details to be more modest and appropriate.

Specific instructions for each entity type:

1. For each new location:
   - Use the provided name and ID
   - Determine an appropriate type (city, village, country, region, etc.)
   - Write a concise single-sentence description that:
     * Does not refer to any other entities
     * Provides only background information, not related to the event in the outline
     * Is general and serves as background for this event
   - Include at least five additional properties from: population, area, founded, climate, elevation, country
   - Format the output as follows:
     <location>
     <id>[Provided ID]</id>
     <name>[Fictional name]</name>
     <type>[city/village/country/region]</type>
     <description>[One-sentence concise description]</description>
     [Include at least 5 of: population, area, founded, climate, elevation, country]
     </location>

2. For each new person:
   - Use the provided name and ID
   - Create fictional details for: date_of_birth, gender, profession, nationality, education
   - Write a concise single-sentence description that:
     * Focuses on background, personality, and motivations
     * Does not refer to any other entities
     * Provides only background information, not related to the event in the outline
     * Is general and serves as background for this event
   - Include at least five additional properties from: height, weight, eye_color, hair_color, political_affiliation, marital_status, spouse
   - Format the output as follows:
     <person>
     <id>[Provided ID]</id>
     <name>[Full name]</name>
     <date_of_birth>[Date]</date_of_birth>
     <gender>[Gender]</gender>
     <profession>[Job title]</profession>
     <nationality>[Country]</nationality>
     <education>[Highest level of education]</education>
     <description>[One-sentence concise description]</description>
     [Include at least 5 of: height, weight, eye_color, hair_color, political_affiliation, marital_status]
     </person>

3. For each new organization:
   - Use the provided name and ID
   - Determine an appropriate type (company, non-profit, educational institution, government agency, etc.)
   - Write a concise single-sentence description that:
     * Does not refer to any other entities
     * Provides only background information, not related to the event in the outline
     * Is general and serves as background for this event
   - Include at least five additional properties from: founded, headquarters, industry, mission_statement, number_of_employees, annual_revenue
   - Format the output as follows:
     <organization>
     <id>[Provided ID]</id>
     <name>[Fictional name]</name>
     <type>[company/non-profit/educational institution/government agency]</type>
     <description>[One-sentence concise description]</description>
     [Include at least 5 of: founded, headquarters, industry, mission_statement, number_of_employees, annual_revenue]
     </organization>

4. For each new product:
   - Use the provided name and ID
   - Determine an appropriate type (consumer good, software, service, etc.)
   - Write a concise single-sentence description that:
     * Does not refer to any other entities
     * Provides only background information, not related to the event in the outline
     * Is general and serves as background for this event
   - Include at least five additional properties from: manufacturer, release_date, price, weight, warranty
   - Format the output as follows:
     <product>
     <id>[Provided ID]</id>
     <name>[Fictional name]</name>
     <type>[consumer good/software/service]</type>
     <description>[One-sentence concise description]</description>
     [Include at least 5 of: manufacturer, release_date, price, weight, warranty]
     </product>

5. For each new art piece:
   - Use the provided name and ID
   - Determine an appropriate type (painting, sculpture, novel, film, etc.)
   - Write a concise single-sentence description that:
     * Does not refer to any other entities
     * Provides only background information, not related to the event in the outline
     * Is general and serves as background for this event
   - Include at least five additional properties from: creator, year_created, current_location_country, current_location_city, current_location_place
   - Format the output as follows:
     <art>
     <id>[Provided ID]</id>
     <name>[Fictional name]</name>
     <type>[painting/sculpture/novel/film]</type>
     <description>[One-sentence concise description]</description>
     [Include at least 5 of: creator, year_created, current_location_country, current_location_city, current_location_place]
     </art>

6. For each new building:
   - Use the provided name and ID
   - Determine an appropriate type (residential, commercial, public, etc.)
   - Write a concise single-sentence description that:
     * Does not refer to any other entities
     * Provides only background information, not related to the event in the outline
     * Is general and serves as background for this event
   - Include at least five additional properties from: place, city, country, architect, year_built, height, floors, material, capacity
   - Format the output as follows:
     <building>
     <id>[Provided ID]</id>
     <name>[Fictional name]</name>
     <type>[residential/commercial/public]</type>
     <description>[One-sentence concise description]</description>
     [Include at least 5 of: place, city, country, architect, year_built, height, floors, material, capacity]
     </building>

7. For each new event:
   - Use the provided name and ID
   - Determine an appropriate type (historical, cultural, sporting, etc.)
   - Write a concise single-sentence description that:
     * Does not refer to any other entities
     * Provides only background information, not related to the event in the outline
     * Is general and serves as background for this event
   - Include at least five additional properties from: date, place, city, country, duration, organizer, number_of_participants, budget
   - Format the output as follows:
     <event>
     <id>[Provided ID]</id>
     <name>[Fictional name]</name>
     <type>[historical/cultural/sporting]</type>
     <description>[One-sentence concise description]</description>
     [Include at least 5 of: date, place, city, country, duration, organizer, number_of_participants, budget]
     </event>

8. For each new miscellaneous entity:
   - Use the provided name and ID
   - Determine an appropriate type (concept, theory, phenomenon, etc.)
   - Write a concise single-sentence description that:
     * Does not refer to any other entities
     * Provides only background information, not related to the event in the outline
     * Is general and serves as background for this event
   - Format the output as follows:
     <miscellaneous>
     <id>[Provided ID]</id>
     <name>[Fictional name]</name>
     <type>[concept/theory/phenomenon]</type>
     <description>[One-sentence concise description]</description>
     </miscellaneous>

Present your final output in the following format:
<results>
[Insert all created entities here, grouped by type]
</results>

Remember to create detailed, coherent, and realistic descriptions for each entity while adhering to the guidelines provided. Ensure that all descriptions are single, short, and concise sentences that do not refer to other entities and only discuss background information unrelated to the event described in the outline.
"""


INSTRUCTIONS_V2 = """
You are an AI assistant tasked with creating fictional entities based on provided information. Your goal is to generate detailed, coherent, and realistic descriptions for new locations, persons, organizations, products, art, buildings, events, and miscellaneous entities. Follow these instructions carefully:

1. Review the existing entities (if provided):

<existing_entities>
{{LOCATIONS_XML}}
{{PERSONS_XML}}
{{ORGANIZATIONS_XML}}
{{PRODUCTS_XML}}
{{ARTS_XML}}
{{EVENTS_XML}}
{{BUILDINGS_XML}}
{{MISCELLANEOUSS_XML}}
</existing_entities>

2. Review the names of new entities to be created:
<new_entity_names>
{{USED_NEW-LOCATIONS_XML}}
{{USED_NEW-PERSONS_XML}}
{{USED_NEW-ORGANIZATIONS_XML}}
{{USED_NEW-PRODUCTS_XML}}
{{USED_NEW-ARTS_XML}}
{{USED_NEW-EVENTS_XML}}
{{USED_NEW-BUILDINGS_XML}}
{{USED_NEW-MISCELLANEOUSS_XML}}
</new_entity_names>

3. Carefully read the provided outline:

Date: {{DATE}}
<outline>
{{OUTLINE}}
</outline>

Based on the information provided, create detailed descriptions for each new entity following these guidelines:

General instructions:
- Ensure all created entities are entirely fictional and not similar to any real or known fictional entities.
- Maintain realism and coherence with the provided outline and other entities.
- Create a believable and consistent fictional world that aligns with the context of the outline.
- For entity descriptions, focus on providing a solid background that remains valid throughout the story, rather than basing it centrally on the outline itself.
- Develop well-rounded entities with backgrounds and characteristics that can support various potential story developments beyond the specific outline provided.
- Strictly derive all entities from the outline. Do not invent entities that are not mentioned in the outline.
- Do not alter the name of the entities.
- Some properties (e.g., place, city, country, spouse, architect, country, nationality) must be filled with named entities. Make sure to use FICTIONAL named entities ( fictional places, cities, countries, spouse names, architects, countries, nationalities, etc.). Check if you should use one of the existing fictional named entities (from <new_entity_names> and <existing_entities>) or create a fictional name instead. DO NOT say that any of the entities or properties are fictional. It is important that everything seems realistic!

Specific instructions for each entity type:

1. For each new location:
   - Use the provided name and ID
   - Determine an appropriate type (city, village, country, region, etc.)
   - Write a concise single-sentence description that:
     * Does not refer to any other entities
     * Provides only background information, not related to the event in the outline
     * Is general and serves as background for this event
   - Include at least five additional properties from: population, area, founded, climate, elevation, country
   - Format the output as follows:
     <location>
     <id>[Provided ID]</id>
     <name>[Fictional name]</name>
     <type>[city/village/country/region]</type>
     <description>[One-sentence concise description]</description>
     [Include at least 5 of: population, area, founded, climate, elevation, country]
     </location>

2. For each new person:
   - Use the provided name and ID
   - Create fictional details for: date_of_birth, gender, profession, nationality, education
   - Write a concise single-sentence description that:
     * Focuses on background, personality, and motivations
     * Does not refer to any other entities
     * Provides only background information, not related to the event in the outline
     * Is general and serves as background for this event
   - Include at least five additional properties from: height, weight, eye_color, hair_color, political_affiliation, marital_status, spouse
   - Format the output as follows:
     <person>
     <id>[Provided ID]</id>
     <name>[Full name]</name>
     <date_of_birth>[Date]</date_of_birth>
     <gender>[Gender]</gender>
     <profession>[Job title]</profession>
     <nationality>[Country]</nationality>
     <education>[Highest level of education]</education>
     <description>[One-sentence concise description]</description>
     [Include at least 5 of: height, weight, eye_color, hair_color, political_affiliation, marital_status]
     </person>

3. For each new organization:
   - Use the provided name and ID
   - Determine an appropriate type (company, non-profit, educational institution, government agency, etc.)
   - Write a concise single-sentence description that:
     * Does not refer to any other entities
     * Provides only background information, not related to the event in the outline
     * Is general and serves as background for this event
   - Include at least five additional properties from: founded, headquarters, industry, mission_statement, number_of_employees, annual_revenue
   - Format the output as follows:
     <organization>
     <id>[Provided ID]</id>
     <name>[Fictional name]</name>
     <type>[company/non-profit/educational institution/government agency]</type>
     <description>[One-sentence concise description]</description>
     [Include at least 5 of: founded, headquarters, industry, mission_statement, number_of_employees, annual_revenue]
     </organization>

4. For each new product:
   - Use the provided name and ID
   - Determine an appropriate type (consumer good, software, service, etc.)
   - Write a concise single-sentence description that:
     * Does not refer to any other entities
     * Provides only background information, not related to the event in the outline
     * Is general and serves as background for this event
   - Include at least five additional properties from: manufacturer, release_date, price, weight, warranty
   - Format the output as follows:
     <product>
     <id>[Provided ID]</id>
     <name>[Fictional name]</name>
     <type>[consumer good/software/service]</type>
     <description>[One-sentence concise description]</description>
     [Include at least 5 of: manufacturer, release_date, price, weight, warranty]
     </product>

5. For each new art piece:
   - Use the provided name and ID
   - Determine an appropriate type (painting, sculpture, novel, film, etc.)
   - Write a concise single-sentence description that:
     * Does not refer to any other entities
     * Provides only background information, not related to the event in the outline
     * Is general and serves as background for this event
   - Include at least five additional properties from: creator, year_created, current_location_country, current_location_city, current_location_place
   - Format the output as follows:
     <art>
     <id>[Provided ID]</id>
     <name>[Fictional name]</name>
     <type>[painting/sculpture/novel/film]</type>
     <description>[One-sentence concise description]</description>
     [Include at least 5 of: creator, year_created, current_location_country, current_location_city, current_location_place]
     </art>

6. For each new building:
   - Use the provided name and ID
   - Determine an appropriate type (residential, commercial, public, etc.)
   - Write a concise single-sentence description that:
     * Does not refer to any other entities
     * Provides only background information, not related to the event in the outline
     * Is general and serves as background for this event
   - Include at least five additional properties from: place, city, country, architect, year_built, height, floors, material, capacity
   - Format the output as follows:
     <building>
     <id>[Provided ID]</id>
     <name>[Fictional name]</name>
     <type>[residential/commercial/public]</type>
     <description>[One-sentence concise description]</description>
     [Include at least 5 of: place, city, country, architect, year_built, height, floors, material, capacity]
     </building>

7. For each new event:
   - Use the provided name and ID
   - Determine an appropriate type (historical, cultural, sporting, etc.)
   - Write a concise single-sentence description that:
     * Does not refer to any other entities
     * Provides only background information, not related to the event in the outline
     * Is general and serves as background for this event
   - Include at least five additional properties from: date, place, city, country, duration, organizer, number_of_participants, budget
   - Format the output as follows:
     <event>
     <id>[Provided ID]</id>
     <name>[Fictional name]</name>
     <type>[historical/cultural/sporting]</type>
     <description>[One-sentence concise description]</description>
     [Include at least 5 of: date, place, city, country, duration, organizer, number_of_participants, budget]
     </event>

8. For each new miscellaneous entity:
   - Use the provided name and ID
   - Determine an appropriate type (concept, theory, phenomenon, etc.)
   - Write a concise single-sentence description that:
     * Does not refer to any other entities
     * Provides only background information, not related to the event in the outline
     * Is general and serves as background for this event
   - Format the output as follows:
     <miscellaneous>
     <id>[Provided ID]</id>
     <name>[Fictional name]</name>
     <type>[concept/theory/phenomenon]</type>
     <description>[One-sentence concise description]</description>
     </miscellaneous>

Present your final output in the following format:
<results>
[Insert all created entities here, grouped by type]
</results>

Remember to create detailed, coherent, and realistic descriptions for each entity while adhering to the guidelines provided. Ensure that all descriptions are single, short, and concise sentences that do not refer to other entities and only discuss background information unrelated to the event described in the outline.
"""

def get_instructions(version):
    if version == 'v2':
        out = INSTRUCTIONS_V2
    elif version == 'v3':
        out = INSTRUCTIONS_V3
    else:
        raise ValueError(version)

    return out.strip()