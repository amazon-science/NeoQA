from typing import Dict, List, Optional

from data_gen.llm.critiques.base_critique import BaseCritique
from data_gen.llm.critiques.output_format_critique import OutputFormatCritique
from data_gen.llm.modules.parsable_base_module import ParsableBaseModule
from data_gen.llm.prompting.modules.nested_parsable_output_prompt import BasicNestedXMLParser
from data_gen.llm.prompting.parsable_prompt import ParsablePrompt
from data_gen.llm.wrapper.base_llm_wrapper import BaseLLMWrapper
from data_gen.news.news_profiles.get_newspaper_profile import get_newspaper_profile_prompt

EXPECTED_OUTPUT_FORMAT: str = """
<result>
<scratchpad>
[Plan your approach here]
</scratchpad>
<headline>
[Write a headline here]
</headline>
<article>
<paragraph>
<text>[First paragraph text]</text>
</paragraph>
<paragraph>
<text>[Second paragraph text]</text>
</paragraph>
<paragraph>
<text>[Third paragraph text (if needed)]</text>
</paragraph>
</article>
</result>
""".strip()


class WriteNewsArticleModule(ParsableBaseModule):

    def _create_formatting_critique(self, parsers: List[BasicNestedXMLParser]) -> BaseCritique:
        return OutputFormatCritique('write-news-article', parsers, EXPECTED_OUTPUT_FORMAT)

    def _preprocess_values(self, values) -> Dict:
        return super()._preprocess_values(values)

    def __init__(self, llm: BaseLLMWrapper, name: str, instruction_name: str):
        super().__init__(
            llm,
            name,
            instruction_name,
            get_instructions(instruction_name),
            max_critiques=5
        )

    def _get_parsers(self) -> List[BasicNestedXMLParser]:
        return [
            BasicNestedXMLParser(
                'headline', './/headline',
                is_object=False, to_single=True, result_node='result', remove_node='scratchpad'
            ),
            BasicNestedXMLParser(
                'paragraphs', './/paragraph',
                is_object=True, to_single=False, result_node='result', remove_node='scratchpad'
            )
        ]

    def get_file_name(self, prompt: ParsablePrompt, values: Dict):
        node_idx = values['CREATED_AT']
        newspaper = values['NEWSPAPER_PROFILE']
        subset_index: int = values['SUBSET_IDX']
        return f'N{node_idx:02d}-{self.name}-{newspaper}_{self.instruction_name}_subset-{subset_index}.json'

    def _get_system_prompt(self, values: Dict) -> Optional[str]:
        return get_newspaper_profile_prompt(values['NEWSPAPER_PROFILE'])


INSTRUCTIONS_V1 = """
You are tasked with writing a news article about a fictional event based on provided information. Your goal is to create a realistic news article using the given details. Follow these instructions carefully:

1. First, review the background information about the fictional entities involved in the event:

<entities>
<LOCATIONS>
{{LOCATIONS_XML}}
</LOCATIONS>

<PERSONS>
{{PERSONS_XML}}
</PERSONS>

<ORGANIZATIONS>
{{ORGANIZATIONS_XML}}
</ORGANIZATIONS>

<PRODUCTS>
{{PRODUCTS_XML}}
</PRODUCTS>

<ARTS>
{{ARTS_XML}}
</ARTS>

<EVENTS>
{{EVENTS_XML}}
</EVENTS>

<BUILDINGS>
{{BUILDINGS_XML}}
</BUILDINGS>

<MISCELLANEOUS>
{{MISCELLANEOUSS_XML}}
</MISCELLANEOUS>
</entities>

<event_info>
{{EVENT_INFO}}
</event_info>

Your task is to create a news article about this fictional event. Follow these guidelines:

Your article must contain all of the information provided in <event_info>
Your article must align with your newspaper's profile.
After writing, double-check that your article contains all the information outlined in the event_info.
When writing the article, follow this format:

<result>
<scratchpad>
[Plan your approach here]
</scratchpad>
<headline>
[Write a headline here]
</headline>
<article>
<paragraph>
<text>[First paragraph text]</text>
</paragraph>
<paragraph>
<text>[Second paragraph text]</text>
</paragraph>
<paragraph>
<text>[Third paragraph text (if needed)]</text>
</paragraph>
</article>
</result>


Remember, your goal is to create a realistic news article based on the provided fictional event information. Good luck!
"""

INSTRUCTIONS_V2: str = """
You are an AI assistant tasked with writing a fictional news article based on provided information. Your goal is to create a realistic and engaging news piece using the given details while adhering to specific guidelines. Follow these instructions carefully:

1. Review the background information about the fictional entities involved in the event. This information is provided in XML format for various categories:

<entities>
<LOCATIONS>
{{LOCATIONS_XML}}
</LOCATIONS>

<PERSONS>
{{PERSONS_XML}}
</PERSONS>

<ORGANIZATIONS>
{{ORGANIZATIONS_XML}}
</ORGANIZATIONS>

<PRODUCTS>
{{PRODUCTS_XML}}
</PRODUCTS>

<ARTS>
{{ARTS_XML}}
</ARTS>

<EVENTS>
{{EVENTS_XML}}
</EVENTS>

<BUILDINGS>
{{BUILDINGS_XML}}
</BUILDINGS>

<MISCELLANEOUS>
{{MISCELLANEOUSS_XML}}
</MISCELLANEOUS>
</entities>

2. Next, carefully read the event information provided:

<event_info>
{{EVENT_INFO}}
</event_info>

3. Consider the profile of the newspaper you're writing for:

4. Write a news article about this fictional event following these guidelines:
   a. Include ALL the information provided in the <event_info> section.
   b. Ensure your article aligns with the newspaper's profile.
   c. Maintain a tone that aligns with your newspaper's established style.
   d. Organize the information logically, starting with the most important details.
   e. Create a compelling headline that captures the essence of the story and fits your newspaper’s style.
   f. Write at least two paragraphs, but no more than four.
   g. Only use information from the provided <entities> to maintain consistency with the known fictional world.

5. When referring to entities in your article, use the following format: {[phrase]|[entity-id]}
   - [phrase] is the actual text that appears in the sentence.
   - [entity-id] is the ID of the entity as provided in the background information.

   For example:
   "Anna Peters told Tim that he should stop talking."
   should be written as:
   "{Anna Peters|PERSON-1} told {Tim|PERSON-2} that {he|PERSON-2} should stop talking."

   If multiple entities are referred to by the same word, use this format:
   "{Both|PERSON-1,PERSON-2} liked the chocolate."

   Ensure that the phrase is natural to the underlying text. Replace "Anna" with {Anna|PERSON-1}, not the full name "{Anna Peters|PERSON-1}".

6. Present your news article in the following format:

<result>
<scratchpad>
[Plan your approach here]
</scratchpad>
<headline>
[Write a headline here]
</headline>
<article>
<paragraph>
<text>[First paragraph text]</text>
</paragraph>
<paragraph>
<text>[Second paragraph text]</text>
</paragraph>
<paragraph>
<text>[Third paragraph text (if needed)]</text>
</paragraph>
</article>
</result>

7. After writing the article, double-check that you've included all the information from the <event_info> section and that you've correctly referenced all entities using the {[phrase]|[entity-id]} format.

Remember, your goal is to create a realistic and engaging news article based on the provided fictional event information while adhering to the newspaper's profile. Good luck!
"""

INSTRUCTIONS_V3: str = """
You are an AI assistant tasked with writing a fictional news article based on provided information. Your goal is to create a realistic and engaging news piece using the given details while adhering to specific guidelines. Follow these instructions carefully:

1. First, review the background information about the fictional entities involved in the event. This information is provided in XML format for various categories:

<entities>
<LOCATIONS>
{{LOCATIONS_XML}}
</LOCATIONS>

<PERSONS>
{{PERSONS_XML}}
</PERSONS>

<ORGANIZATIONS>
{{ORGANIZATIONS_XML}}
</ORGANIZATIONS>

<PRODUCTS>
{{PRODUCTS_XML}}
</PRODUCTS>

<ARTS>
{{ARTS_XML}}
</ARTS>

<EVENTS>
{{EVENTS_XML}}
</EVENTS>

<BUILDINGS>
{{BUILDINGS_XML}}
</BUILDINGS>

<MISCELLANEOUS>
{{MISCELLANEOUSS_XML}}
</MISCELLANEOUS>
</entities>

2. Next, carefully read the event information provided with links to the provided entities as background information:

<event_info>
{{EVENT_INFO}}
</event_info>

3. Consider the profile of the newspaper you're writing for.

4. Write a news article about this fictional event following these guidelines:
   a. Include ALL the information provided in the event_info section.
   b. Ensure your article aligns with the newspaper's profile.
   c. Maintain a professional tone that aligns with your newspaper's profile.
   d. Organize the information logically, starting with the most important details.
   e. Create a compelling headline that captures the essence of the story and fits your newspaper's style.
   f. Write at least two paragraphs, but no more than four.
   g. Only use information from the provided entities to maintain consistency with the known fictional world.

6. Present your news article in the following format:

<result>
<scratchpad>
[Plan your approach here]
</scratchpad>
<headline>
[Write a headline here]
</headline>
<article>
<paragraph>
<text>[First paragraph text]</text>
</paragraph>
<paragraph>
<text>[Second paragraph text]</text>
</paragraph>
<paragraph>
<text>[Third paragraph text (if needed)]</text>
</paragraph>
</article>
</result>

7. After writing the article, double-check that you've included all the information from the event_info section. 

Remember, your goal is to create a realistic and engaging news article based on the provided fictional event information while adhering to the newspaper's profile. Good luck!
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
