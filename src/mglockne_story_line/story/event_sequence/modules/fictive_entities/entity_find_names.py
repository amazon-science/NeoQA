from datetime import datetime
from typing import Optional, List, Dict, Set

from src.mglockne_story_line.llm.critiques.base_critique import BaseCritique
from src.mglockne_story_line.llm.critiques.modules.parsable_root_node_critique import ParsableRootNodeCritique
from src.mglockne_story_line.llm.modules.parsable_base_module import ParsableBaseModule
from src.mglockne_story_line.llm.prompting.modules.nested_parsable_output_prompt import BasicNestedXMLParser
from src.mglockne_story_line.llm.prompting.parsable_prompt import ParsablePrompt
from src.mglockne_story_line.llm.wrapper.base_llm_wrapper import BaseLLMWrapper
from src.mglockne_story_line.story.event_sequence.elements.entity import Entity
from src.mglockne_story_line.story.event_sequence.modules.fictive_entities.entity_critiques.entity_duplicate_found_name_critique import \
    NewEntityNameFoundTwiceCritique
from src.mglockne_story_line.story.event_sequence.modules.fictive_entities.entity_critiques.avoid_problematic_entity_names_critique import \
    AvoidProblematicEntityNamesCritique
from src.mglockne_story_line.story.event_sequence.modules.fictive_entities.entity_critiques.max_word_entity_name_critique import \
    MaxNameWordCountCritique
from src.mglockne_story_line.story.event_sequence.modules.fictive_entities.entity_critiques.new_entity_name_critique import \
    NewEntityNameCritique
from src.mglockne_story_line.util.entity_util import get_entity_categories
from src.mglockne_story_line.util.story_tools import renew_outline


class IdentifyNewNamedEntitiesModule(ParsableBaseModule):
    """
    This module identifies newly introduced named entities from the outline.
    """

    def spy_on_output(self, output: Dict):
        print(output['response'])
        super().spy_on_output(output)

    def on_main_called(self, values: Dict):
        return super().on_main_called(values)

    def _create_formatting_critique(self, parsers: List[BasicNestedXMLParser]) -> Optional[BaseCritique]:
        return ParsableRootNodeCritique('results')

    def _create_critiques(self) -> List[BaseCritique]:
        return [
            NewEntityNameCritique('find-names-critique'),
            MaxNameWordCountCritique(),
            AvoidProblematicEntityNamesCritique(),
            NewEntityNameFoundTwiceCritique()
        ]

    def _postprocess_values(self, values: Dict) -> Optional[Dict]:
        for key in get_entity_categories():
            new_list: List[Dict] = []
            added_names: Set[str] = set()
            for name in values[f'new_{key}_name']:
                if name not in added_names:
                    new_list.append({'name': name, 'old_name': name})
                    added_names.add(name)
            values[f'new_{key}_name'] = new_list
        return values


    def _preprocess_values(self, values) -> Dict:
        start_find_preprocess = datetime.now()
        for key in get_entity_categories():
            if key not in values:
                values[f'{key}s_xml'] = ''
            else:
                entities: List[Entity] = values[key]
                values[f'{key}s_xml'] = '\n'.join([
                    ent.xml() for ent in entities
                ])
        values = renew_outline(values)
        print('Find names preprocess', datetime.now() - start_find_preprocess)
        return values

    def _get_parsers(self) -> List[BasicNestedXMLParser]:
        start_get_parser = datetime.now()
        parsers = [
            BasicNestedXMLParser(f'new_{entity_type}_name', f'.//output/{entity_type}', is_object=False, result_node='results', remove_node='scratchpad ')
            for entity_type in get_entity_categories()
        ]
        print('Find names preprocess', datetime.now() - start_get_parser)
        return parsers

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
            max_critiques=5
        )


INSTRUCTIONS_V8 = """
You are an AI assistant tasked with identifying new named entities from a given outline of a fictional event description. Your goal is to identify any new named entities mentioned in the OUTLINE that are not already present in the provided lists of existing entities.

First, carefully read and analyze the following OUTLINE:

Date: {{DATE}}
<OUTLINE>
{{OUTLINE}}
</OUTLINE>

Now, review the existing named entities in the following XML structures. Note that these lists may be empty or contain partial information:

<entities>
{{LOCATIONS_XML}}
{{PERSONS_XML}}
{{ORGANIZATIONS_XML}}
{{PRODUCTS_XML}}
{{ARTS_XML}}
{{EVENTS_XML}}
{{BUILDINGS_XML}}
{{MISCELLANEOUSS_XML}}
</entities>

The definitions with examples for each named entity category are listed here:
- Person
Definition: Individual human beings, including fictional figures.
Examples: Barack Obama, William Shakespeare, Harry Potter, Marie Curie

-Organization
Definition: Groups of people working together for a common purpose, including companies, institutions, ethnic groups, communities and government bodies.
Examples: United Nations, Apple Inc., Harvard University, Greenpeace, Maori

- Location
Definition: Geographical or political areas, locations, countries (together with their nationalities), cities, natural landmarks, and regions.
Examples: Paris, Mount Everest, California, Amazon Rainforest, Japan, Australia, Australian

- Product
Definition: Goods or services created for consumer use or commercial purposes.
Examples: iPhone, Coca-Cola, Microsoft Office, Tesla Model 3

- Art
Definition: Creative works in various forms, including artifacts, ornaments, visual arts, literature, music, and performance.
Examples: Mona Lisa, To Kill a Mockingbird, Beethoven's Symphony No. 9, Hamilton (musical)

 - Building
Definition: Structures designed for human occupancy or use, including residential, commercial, and public structures.
Examples: Empire State Building, Taj Mahal, Sydney Opera House, Buckingham Palace

 - Event
Definition: Significant occurrences or planned gatherings, including historical moments, celebrations, and competitions.
Examples: World War II, Olympic Games, Woodstock Music Festival, Super Bowl

 - Miscellaneous
Definition: Other named entities that don't fit into the above categories, such as abstract concepts, unique identifiers.
Examples: Theory of Relativity, Morse Code, Brexit, Zodiac Signs

IMPORTANT: You must ONLY identify a named entity if the outline explicitly refers to the entity by name.
DO NOT list entities for events which are not explicitly referred to by name. 
DO NOT list entities for buildings that are not explicitly referred to by name (e.g. a big Chicago villa)

Example: "On the 27th birthday of Carla Short"
- "Carla Short" is a named entity (Person)
- No named event is in this statement

Example: "On the third day of the Banana Split Festival I left my keys"
- National Banana Split Festival is a named entity (Event)

Example: "I sold my $13M Chicago villa."
- "Chicago" is a named entity (Location)
- "$13M Chicago villa" is NOT a named entity. However, this phrase contains the named entity Chicago (location)

Example: "I bought tickets to go on the Sky Needle, the highest skyscraper in town!"
- "Sky Needle" is a named entity (building)

Example: "Aboriginal people from a well known Australian city."
- "Aboriginal" is a named entity (Organization)
- "Australia" is a named entity (Location)

To complete this task, follow these steps:

1. Identification of named entities: Carefully read through the OUTLINE and identify all named entities (locations, persons, organizations, products, art, events, buildings, or miscellaneous) that are mentioned by name. Consider all named entities. Carefully follow the definition and examples provided for each entity type above. DO NOT ignore named entities from the outline that exist in the real world. Carefully double-check that you did not miss any named entities. If you are in doubt about some named entities, epxlain why you bare not sure.

2. Remove entities that are already known and only keep new named entities:
   a. For each named entity you identify, check if it already exists in the <entities>. If <entities> is empty, consider all named entities as new.
   b. Only keep new named entities which cannot be found in the <entities> list of known named entities.
   c. Ensure that each new named entity is explicitly mentioned by name in the <outline>. The outline may refer to various entities (such as events, buildings, products) that are described generally but not by a specific name. These should not be identified as named entities.

3. Verification and refinement of new named entities:
   a. Review your preliminary list of new named entities.
   b. Double-check each named entity against the existing XML structures to ensure it is truly new and not already present.
   c. For each new named entity, determine its full name as it appears in the OUTLINE. Do not infer or create additional information.
   d. Ensure that the full name of each named entity is distinct. Two different entities MUST NOT share the same full name.
   e. Examine your list of verified new named entities for any redundancies. If any entities refer to the same person, place, organization, product, art piece, event, building, or miscellaneous item but are mentioned with slight variations in the OUTLINE, keep only the most complete or accurate version and remove the others.
   f. Do not list abbreviations as separate entities. If an abbreviation is used, do not include it with the full name of the entity, and do not create a separate entry for it.
   g. Ensure that each identified named entity refers to an actual identifiable entity mentioned in the OUTLINE.

4. Formatting and outputting the final list:
   a. Categorize each verified new named entity as either a location, person, organization, product, art, event, building, or miscellaneous.
   b. Format your output for each new named entity using the appropriate XML tag based on its category:
      - For locations: <location>Full Name of Location</location>
      - For persons: <person>Full Name of Person</person>
      - For organizations: <organization>Full Name of Organization</organization>
      - For products: <product>Full Name of Product</product>
      - For art: <art>Full Name of Art Piece</art>
      - For events: <event>Full Name of Event</event>
      - For buildings: <building>Full Name of Building</building>
      - For miscellaneous: <miscellaneous>Full Name of Miscellaneous Entity</miscellaneous>
   c. If no new named entities are found after verification and redundancy removal, output <no_new_entities>No new named entities identified</no_new_entities>

5. Double-check miscellaneous
   a. If you classified any new entity as miscellaneous:
       - Compare the entity and how it is used in context with all other named entity types
       - Check if any of the other entity types fits this named entity (it does not need to fit 100%)
       - If any of these entities seem applicable to the entity, list the named entity with the newly found entity and NOT as miscellaneous entity.

Sometimes the difference between the named entities is blurry. To help you make decisions in borderline cases follow these rules:
- Organization or Building: If in doubt, use "organization" instead of "building". Only use "building" if the name alone clearly identifies the entity as a building.  

Important notes:
- All entities in this task should be fictional and should be treated as distinct from any existing real-world or fictional entities. However, you must identify the names exactly as they appear in the OUTLINE, even if they are similar to real-world entities.
- Remember not to list abbreviations as separate entities. 
- Include the names of any real-world entities from the outline.
- Only list NAMED entities. Do not create names for all entities that occur within the story.
- Make sure that you have an output for EACH NEW named entity that you have identified!

Use a <scratchpad> node within the <results> root node for all your reasoning. DO NOT include any XML tags in the reasoning process.

Present your final list of new named entities in this format:

<output>
[Your list of new named entities in XML format goes here]
</output>

If you need to think through your process or make notes, use UPPERCASE variable names for your thinking process. Your final output should only include the new named entities or the no_new_entities tag if applicable.

List all output including your thinking process within a single <results> node.

Before finalizing your output, double-check that you did not miss any named entities from the outline and that each named entity has a distinct full name.
"""


INSTRUCTIONS_V7 = """
You are an AI assistant tasked with identifying new named entities from a given outline of a fictional event description. Your goal is to identify any new named entities mentioned in the OUTLINE that are not already present in the provided lists of existing entities.

First, carefully read and analyze the following OUTLINE:

Date: {{DATE}}
<OUTLINE>
{{OUTLINE}}
</OUTLINE>

Now, review the existing named entities in the following XML structures. Note that these lists may be empty or contain partial information:

<entities>
{{LOCATIONS_XML}}
{{PERSONS_XML}}
{{ORGANIZATIONS_XML}}
{{PRODUCTS_XML}}
{{ARTS_XML}}
{{EVENTS_XML}}
{{BUILDINGS_XML}}
{{MISCELLANEOUSS_XML}}
</entities>

The definitions with examples for each named entity category are listed here:
IMPORTANT: You must ONLY identify a named entity if the outline explicitly refers to the entity by name.
DO NOT list entities for events which are not explicitly referred to by name. 
Example: "On the 27th birthday of Carla Short"
- Carla Short is a named entity (Person)
- No named event is in this statement

Example: "On the third day of the Banana Split Festival I left my keys"
National Banana Split Festival is a named entity (Event)

DO NOT list entities for buildings that are not explicitly referred to by name (e.g. a big Chicago villa)
Example: "I sold my $13M Chicago villa."
- Chicago is a named entity (Location)
- "$13M villa in Chicago" is NOT a named entity (building). However, this phrase contains the named entity Chicago (location)

Example: "I bought tickets to go on the Sky Needle, the highest skyscraper in town!"
- Sky Needle is a named entity (building)

- Person
Definition: Individual human beings, including fictional figures.
Examples: Barack Obama, William Shakespeare, Harry Potter, Marie Curie

-Organization
Definition: Groups of people working together for a common purpose, including companies, institutions, and government bodies.
Examples: United Nations, Apple Inc., Harvard University, Greenpeace

- Location
Definition: Geographical or political areas, including countries, cities, natural landmarks, and regions.
Examples: Paris, Mount Everest, California, Amazon Rainforest

- Product
Definition: Goods or services created for consumer use or commercial purposes.
Examples: iPhone, Coca-Cola, Microsoft Office, Tesla Model 3

- Art
Definition: Creative works in various forms, including visual arts, literature, music, and performance.
Examples: Mona Lisa, To Kill a Mockingbird, Beethoven's Symphony No. 9, Hamilton (musical)

 - Building
Definition: Structures designed for human occupancy or use, including residential, commercial, and public structures.
Examples: Empire State Building, Taj Mahal, Sydney Opera House, Buckingham Palace

 - Event
Definition: Significant occurrences or planned gatherings, including historical moments, celebrations, and competitions.
Examples: World War II, Olympic Games, Woodstock Music Festival, Super Bowl

 - Miscellaneous
Definition: Other named entities that don't fit into the above categories, often including abstract concepts or unique identifiers.
Examples: Theory of Relativity, Morse Code, Brexit, Zodiac Signs

To complete this task, follow these steps:

1. Identification of new named entities:
   a. Carefully read through the OUTLINE and identify all named entities (locations, persons, organizations, products, art, events, buildings, or miscellaneous) that are mentioned.
   b. For each named entity you identify, check if it already exists in the corresponding XML structure. If an XML structure is empty, consider all named entities of that type as new.
   c. Create a preliminary list of new named entities that are not found in the existing lists.
   d. Review the list of created named entities. Ensure that each named entity is explicitly mentioned by name in the OUTLINE. Remove any named entities not specifically stated by name in the outline. The outline may refer to various entities (such as events, buildings, products) that are described generally but not by a specific name. These should not be identified as named entities. In summary: Discard any entities for which there is insufficient information to locate them by name in an encyclopedia.

2. Verification and refinement of new named entities:
   a. Review your preliminary list of new named entities.
   b. Double-check each named entity against the existing XML structures to ensure it is truly new and not already present.
   c. For each new named entity, determine its full name as it appears in the OUTLINE. Do not infer or create additional information.
   d. Ensure that the full name of each named entity is distinct. Two different entities MUST NOT share the same full name.
   e. Examine your list of verified new named entities for any redundancies. If any entities refer to the same person, place, organization, product, art piece, event, building, or miscellaneous item but are mentioned with slight variations in the OUTLINE, keep only the most complete or accurate version and remove the others.
   f. Do not list abbreviations as separate entities. If an abbreviation is used, do not include it with the full name of the entity, and do not create a separate entry for it.
   g. Ensure that each identified named entity refers to an actual identifiable entity mentioned in the OUTLINE.

3. Formatting and outputting the final list:
   a. Categorize each verified new named entity as either a location, person, organization, product, art, event, building, or miscellaneous.
   b. Format your output for each new named entity using the appropriate XML tag based on its category:
      - For locations: <location>Full Name of Location</location>
      - For persons: <person>Full Name of Person</person>
      - For organizations: <organization>Full Name of Organization</organization>
      - For products: <product>Full Name of Product</product>
      - For art: <art>Full Name of Art Piece</art>
      - For events: <event>Full Name of Event</event>
      - For buildings: <building>Full Name of Building</building>
      - For miscellaneous: <miscellaneous>Full Name of Miscellaneous Entity</miscellaneous>
   c. If no new named entities are found after verification and redundancy removal, output <no_new_entities>No new named entities identified</no_new_entities>

4. Double-check miscellaneous
   a. If you classified any new entity as miscellaneous:
       - Compare the entity and how it is used in context with all other named entity types
       - Check if any of the other entity types fits this named entity (it does not need to fit 100%)
       - If any of these entities seem applicable to the entity, list the named entity with the newly found entity and NOT as miscellaneous entity.

Sometimes the difference between the named entities is blurry. To help you make decisions in borderline cases follow these rules:
- Organization or Building: If in doubt, use "organization" instead of "building". Only use "building" if the name alone clearly identifies the entity as a building.  

Important notes:
- All entities in this task are fictional and should be treated as distinct from any existing real-world or fictional entities. However, you must identify the names exactly as they appear in the OUTLINE, even if they seem similar to real-world entities.
- If any of the input variables (LOCATIONS, PERSONS, ORGANIZATIONS, PRODUCTS, ART, EVENTS, BUILDINGS, MISCELLANEOUS) are empty, treat them as if no information was provided for that category and proceed with identifying new named entities accordingly.
- Remember not to list abbreviations as separate entities. 
- Include the names of any real-world entities from the outline.
- Only list NAMED entities. Do not create names for all entities that occur within the story.
- Make sure that you have an output for EACH NEW named entity that you have identified!

Use a <scratchpad> node within the <results> root node for all your reasoning. DO NOT include any XML tags in the reasoning process.

Present your final list of new named entities in this format:

<output>
[Your list of new named entities in XML format goes here]
</output>

If you need to think through your process or make notes, use UPPERCASE variable names for your thinking process. Your final output should only include the new named entities or the no_new_entities tag if applicable.

List all output including your thinking process within a single <results> node.

Before finalizing your output, double-check that you did not miss any named entities from the outline and that each named entity has a distinct full name.

Do not reply with ANY CONTENT outside of the <results> tags.
"""


INSTRUCTIONS_V6 = """
You are an AI assistant tasked with identifying new named entities from a given outline of a fictional event description. Your goal is to identify any new named entities mentioned in the OUTLINE that are not already present in the provided lists of existing entities.

First, carefully read and analyze the following OUTLINE:

Date: {{DATE}}
<OUTLINE>
{{OUTLINE}}
</OUTLINE>

Now, review the existing entities in the following XML structures. Note that these lists may be empty or contain partial information:

<entities>
{{LOCATIONS_XML}}
{{PERSONS_XML}}
{{ORGANIZATIONS_XML}}
{{PRODUCTS_XML}}
{{ARTS_XML}}
{{EVENTS_XML}}
{{BUILDINGS_XML}}
{{MISCELLANEOUSS_XML}}
</entities>


The definitions with examples for each named entity category are listed here:
IMPORTANT: You must ONLY identify a named entity if the outline explicitly refers to the entity by name.
DO NOT list entities for events which are not explicitly referred to by name. 
Example: "On the 27th birthday of Carla Short"
- Carla Short is a named entity (Person)
- No named event is in this statement

Example: "On the third day of the Banana Split Festival I left my keys"
National Banana Split Festival is a named entity (Event)

DO NOT list entities for buildings that are not explicitly referred to by name (e.g. a big Chicago villa)
Example: "I sold my $13M Chicago villa."
- Chicago is a named entity (Location)
- $13M Chicago villa is not a named entity

Example: "I bought tickets to go on the Sky Needle, the highest skyscraper in town!"
- Sky Needle is a named entity (building)

- Person
Definition: Individual human beings, including fictional or historical figures.
Examples: Barack Obama, William Shakespeare, Harry Potter, Marie Curie

-Organization
Definition: Groups of people working together for a common purpose, including companies, institutions, and government bodies.
Examples: United Nations, Apple Inc., Harvard University, Greenpeace

- Location
Definition: Geographical or political areas, such as countries (also countries when only the nationality is mentioned), cities, natural landmarks, and regions.
Examples: Paris, Mount Everest, California, Amazon Rainforest, Japan, Australia

- Product
Definition: Goods or services created for consumer use or commercial purposes.
Examples: iPhone, Coca-Cola, Microsoft Office, Tesla Model 3

- Art
Definition: Creative works in various forms, including visual arts, literature, music, and performance.
Examples: Mona Lisa, To Kill a Mockingbird, Beethoven's Symphony No. 9, Hamilton (musical)

 - Building
Definition: Structures designed for human occupancy or use, including residential, commercial, and public structures.
Examples: Empire State Building, Taj Mahal, Sydney Opera House, Buckingham Palace

 - Event
Definition: Significant occurrences or planned gatherings, including historical moments, celebrations, and competitions.
Examples: World War II, Olympic Games, Woodstock Music Festival, Super Bowl

 - Miscellaneous
Definition: Other named entities that don't fit into the above categories, such as abstract concepts, unique identifiers or ethnic groups.
Examples: Theory of Relativity, Morse Code, Brexit, Zodiac Signs, Maori, Aboriginal

To complete this task, follow these steps:

1. Identification of new named entities:
   a. Carefully read through the OUTLINE and identify all named entities (locations, persons, organizations, products, art, events, buildings, or miscellaneous) that are mentioned.
   b. For each named entity you identify, check if it already exists in the corresponding XML structure. If an XML structure is empty, consider all named entities of that type as new.
   c. Create a preliminary list of new named entities that are not found in the existing lists.
   d. Review the list of created named entities. Ensure that each named entity is explicitly mentioned by name in the OUTLINE. Remove any named entities not specifically stated by name in the outline. The outline may refer to various entities (such as events, buildings, products) that are described generally but not by a specific name. These should not be identified as named entities. In summary: Discard any entities for which there is insufficient information to locate them by name in an encyclopedia.

2. Verification and refinement of new named entities:
   a. Review your preliminary list of new named entities.
   b. Double-check each named entity against the existing XML structures to ensure it is truly new and not already present.
   c. For each new named entity, determine its full name as it appears in the OUTLINE. Do not infer or create additional information.
   d. Ensure that the full name of each named entity is distinct. Two different entities MUST NOT share the same full name.
   e. Examine your list of verified new named entities for any redundancies. If any entities refer to the same person, place, organization, product, art piece, event, building, or miscellaneous item but are mentioned with slight variations in the OUTLINE, keep only the most complete or accurate version and remove the others.
   f. Do not list abbreviations as separate entities. If an abbreviation is used, do not include it with the full name of the entity, and do not create a separate entry for it.
   g. Ensure that each identified named entity refers to an actual identifiable entity mentioned in the OUTLINE.

3. Formatting and outputting the final list:
   a. Categorize each verified new named entity as either a location, person, organization, product, art, event, building, or miscellaneous.
   b. Format your output for each new named entity using the appropriate XML tag based on its category:
      - For locations: <location>Full Name of Location</location>
      - For persons: <person>Full Name of Person</person>
      - For organizations: <organization>Full Name of Organization</organization>
      - For products: <product>Full Name of Product</product>
      - For art: <art>Full Name of Art Piece</art>
      - For events: <event>Full Name of Event</event>
      - For buildings: <building>Full Name of Building</building>
      - For miscellaneous: <miscellaneous>Full Name of Miscellaneous Entity</miscellaneous>
   c. If no new named entities are found after verification and redundancy removal, output <no_new_entities>No new named entities identified</no_new_entities>

4. Double-check miscellaneous
   a. If you classified any new entity as miscellaneous:
       - Compare the entity and how it is used in context with all other named entity types
       - Check if any of the other entity types fits this named entity (it does not need to fit 100%)
       - If any of these entities seem applicable to the entity, list the named entity with the newly found entity and NOT as miscellaneous entity.

Important notes:
- All entities in this task are fictional and should be treated as distinct from any existing real-world or fictional entities. However, you must identify the names exactly as they appear in the OUTLINE, even if they seem similar to real-world entities.
- If any of the input variables (LOCATIONS, PERSONS, ORGANIZATIONS, PRODUCTS, ART, EVENTS, BUILDINGS, MISCELLANEOUS) are empty, treat them as if no information was provided for that category and proceed with identifying new named entities accordingly.
- Remember not to list abbreviations as separate entities. 
- Include the names of any real-world entities from the outline.
- Only list NAMED entities. Do not create names for all entities that occur within the story.
- Make sure that you have an output for EACH NEW named entity that you have identified!

Use a <scratchpad> node within the <results> root node for all your reasoning. DO NOT include any XML tags in the reasoning process.

Present your final list of new named entities in this format:

<output>
[Your list of new named entities in XML format goes here]
</output>

If you need to think through your process or make notes, use UPPERCASE variable names for your thinking process. Your final output should only include the new named entities or the no_new_entities tag if applicable.

List all output including your thinking process within a single <results> node.

Before finalizing your output, double-check that you did not miss any named entities from the outline and that each named entity has a distinct full name.

Do not reply with ANY CONTENT outside of the <results> tags.
"""

def get_instructions(version):
    if version == 'v6':
        out = INSTRUCTIONS_V6
    elif version == 'v7':
        out = INSTRUCTIONS_V7
    elif version == 'v8':
        out = INSTRUCTIONS_V8
    else:
        raise ValueError(version)
    return out.strip()