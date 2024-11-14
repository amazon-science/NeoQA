from typing import Dict, List, Optional

from src.mglockne_story_line.llm.critiques.base_critique import BaseCritique
from src.mglockne_story_line.llm.critiques.modules.output_format_critique import OutputFormatCritique
from src.mglockne_story_line.llm.modules.parsable_base_module import ParsableBaseModule
from src.mglockne_story_line.llm.prompting.modules.nested_parsable_output_prompt import BasicNestedXMLParser
from src.mglockne_story_line.llm.prompting.parsable_prompt import ParsablePrompt
from src.mglockne_story_line.llm.wrapper.base_llm_wrapper import BaseLLMWrapper
from src.mglockne_story_line.util.entity_util import get_entity_categories
from src.mglockne_story_line.util.xml_util import dict_to_xml

EXPECTED_OUTPUT_FORMAT: str = """
The output format is incorrect. Please output the results in the following format:
<news>
<passage>First passage</passage>
<passage>Second passage</passage>
...
<passage>Last passage</passage>
</news>
""".strip()

class IdfyNewsArticleModule(ParsableBaseModule):


    def __init__(self, llm: BaseLLMWrapper, name: str, instruction_name: str):
        super().__init__(
            llm,
            name,
            instruction_name,
            get_instructions(instruction_name),
            max_critiques=5
        )

    def _create_formatting_critique(self, parsers: List[BasicNestedXMLParser]) -> Optional[BaseCritique]:
        return OutputFormatCritique('format-idfy-news', parsers, EXPECTED_OUTPUT_FORMAT)

    def _postprocess_values(self, values: Dict) -> Optional[Dict]:
        return super()._postprocess_values(values)

    def _get_parsers(self) -> List[BasicNestedXMLParser]:
        return [
            BasicNestedXMLParser('paragraphs', './/passage', is_object=False, result_node='news'),
        ]

    def _preprocess_values(self, values) -> Dict:

        for entity_type in get_entity_categories():
            entities: List[Dict] = values[f'used_{entity_type}']
            values[f'used_{entity_type}s_xml'] = '\n'.join([
                f'<{entity_type}>{dict_to_xml(ent)}</{entity_type}>'
                for ent in entities
            ])

        values['passages_xml'] = '\n'.join([
            f'<passage>{passage["text"]}</passage>' for passage in values['paragraphs']
        ])

        return values

    def get_file_name(self, prompt: ParsablePrompt, values: Dict):
        node_idx = values['CREATED_AT']
        newspaper = values['NEWSPAPER_PROFILE']
        return f'N{node_idx:02d}-{self.name}-{newspaper}_{self.instruction_name}.json'



INSTRUCTIONS_V1 = """
You are an AI assistant tasked with processing news passages by identifying and marking named entities. Follow these instructions carefully:

First, you will be provided with a list of fictional named entities:
<entities>
<LOCATIONS>
{{USED_LOCATIONS_XML}}
</LOCATIONS>

<PERSONS>
{{USED_PERSONS_XML}}
</PERSONS>

<ORGANIZATIONS>
{{USED_ORGANIZATIONS_XML}}
</ORGANIZATIONS>

<PRODUCTS>
{{USED_PRODUCTS_XML}}
</PRODUCTS>

<ARTS>
{{USED_ARTS_XML}}
</ARTS>

<EVENTS>
{{USED_EVENTS_XML}}
</EVENTS>

<BUILDINGS>
{{USED_BUILDINGS_XML}}
</BUILDINGS>

<MISCELLANEOUS>
{{USED_MISCELLANEOUSS_XML}}
</MISCELLANEOUS>
</entities>

Next, you will be given news article passages to process:
<passages>
{{PASSAGES_XML}}
</passages>

Your task is to process these passages by following these steps:

1. Carefully review the list of entities provided in the <entities> section. Each entity will have an associated ID.

2. Search the passages for all occurrences of each entity in the list.

3. For each occurrence found, replace it with the format: {phrase|ID}
   Where "phrase" is exactly how the entity appears in the text (maintaining any abbreviations or variations), and "ID" is the entity's identifier from the entities list.

4. Maintain the original structure and formatting of the passages, only changing the entities as described.

5. After processing all entities, review the entire passage to ensure all occurrences have been properly marked and no entities were missed.

6. Output the processed passages, maintaining its original structure but with all entity occurrences replaced as instructed.

Important points to remember:
- Be thorough in your search for entities, including variations or partial mentions.
- Preserve the original text exactly as it appears, only adding the entity markup.
- Keep the COMPLETE ORIGINAL phrase that you are replacing with {phrase|ID}. The sentence should be identical to how it was before, except for the added markup.
- If an entity is referred to by full name, the "phrase" is the full name.
- If an entity is referred to by an abbreviation, the "phrase" is the used abbreviation.
- If an entity is referred to using parts of the full name, then the "phrase" would be the same parts of the full name.

Examples:
1. "Renowned novelist Elara Vance and celebrated philanthropist Rohan Kapoor exchanged vows." 
   Should be replaced with:
   "Renowned novelist {Elara Vance|PERSON-1} and celebrated philanthropist {Rohan Kapoor|PERSON-2} exchanged vows."
   (When Elara Vance has ID PERSON-1 and Rohan Kapoor has ID PERSON-2)

2. "Renowned novelist Elara and celebrated philanthropist R. Kapoor exchanged vows." 
   Should be replaced with:
   "Renowned novelist {Elara|PERSON-1} and celebrated philanthropist {R. Kapoor|PERSON-2} exchanged vows."

Format your output as follows:
- Enclose the entire processed news within <news> tags.
- Place each passage of the outline within separate <passage> tags.

Provide your final output without any additional commentary or explanations. Focus solely on processing the outline as instructed.

Provide all output in an overall <results> root node.
"""


INSTRUCTIONS_V2 = """
You are an AI assistant tasked with processing news passages by identifying and marking named entities. Follow these instructions carefully:

First, review the list of fictional named entities provided below:

<entities>
<LOCATIONS>
{{USED_LOCATIONS_XML}}
</LOCATIONS>

<PERSONS>
{{USED_PERSONS_XML}}
</PERSONS>

<ORGANIZATIONS>
{{USED_ORGANIZATIONS_XML}}
</ORGANIZATIONS>

<PRODUCTS>
{{USED_PRODUCTS_XML}}
</PRODUCTS>

<ARTS>
{{USED_ARTS_XML}}
</ARTS>

<EVENTS>
{{USED_EVENTS_XML}}
</EVENTS>

<BUILDINGS>
{{USED_BUILDINGS_XML}}
</BUILDINGS>

<MISCELLANEOUS>
{{USED_MISCELLANEOUSS_XML}}
</MISCELLANEOUS>
</entities>

Next, you will process the following news article passages:

<passages>
{{PASSAGES_XML}}
</passages>

Your task is to process these passages by following these steps:

1. Carefully review the list of entities provided in the <entities> section. Each entity will have an associated ID.

2. Search the passages for all occurrences of each entity in the list.

3. For each occurrence found, replace it with the format: {phrase|ID}
   Where "phrase" is exactly how the entity appears in the text (maintaining any abbreviations or variations), and "ID" is the entity's identifier from the entities list.

4. Maintain the original structure and formatting of the passages, only changing the entities as described.

5. After processing all entities, review the entire passage to ensure all occurrences have been properly marked and no entities were missed.

6. Output the processed passages, maintaining its original structure but with all entity occurrences replaced as instructed.

Important points to remember:
- Be thorough in your search for entities, including variations or partial mentions.
- Preserve the original text exactly as it appears, only adding the entity markup.
- Keep the COMPLETE ORIGINAL phrase that you are replacing with {phrase|ID}. The sentence should be identical to how it was before, except for the added markup.
- If an entity is referred to by full name, the "phrase" is the full name.
- If an entity is referred to by an abbreviation, the "phrase" is the used abbreviation.
- If an entity is referred to using parts of the full name, then the "phrase" would be the same parts of the full name.

Examples:
1. "Renowned novelist Elara Vance and celebrated philanthropist Rohan Kapoor exchanged vows." 
   Should be replaced with:
   "Renowned novelist {Elara Vance|PERSON-1} and celebrated philanthropist {Rohan Kapoor|PERSON-2} exchanged vows."
   (When Elara Vance has ID PERSON-1 and Rohan Kapoor has ID PERSON-2)

2. "Renowned novelist Elara and celebrated philanthropist R. Kapoor exchanged vows." 
   Should be replaced with:
   "Renowned novelist {Elara|PERSON-1} and celebrated philanthropist {R. Kapoor|PERSON-2} exchanged vows."

3. "Anna Peters told Tim that he should stop talking."
   should be written as:
   "{Anna Peters|PERSON-3} told {Tim|PERSON-4} that {he|PERSON-4} should stop talking."
   (When Anna Peters has ID PERSON-3 and Tim Laurens has ID PERSON-4 and is referred to here)

If multiple entities are referred to by the same word, use this format:
"{Both|PERSON-3,PERSON-4} liked the chocolate."

Format your output as follows:
- Enclose the entire processed news within <news> tags.
- Place each passage of the outline within separate <passage> tags.

Provide your final output without any additional commentary or explanations. Focus solely on processing the outline as instructed.

Provide all output in an overall <results> root node.
"""





def get_instructions(version):
    if version == 'v1':
        out = INSTRUCTIONS_V1
    elif version == 'v2':
        out = INSTRUCTIONS_V2
    else:
        raise ValueError(version)
    return out.strip()