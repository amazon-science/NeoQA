from typing import Dict, List

from data_gen.llm.critiques.base_critique import BaseCritique
from data_gen.llm.critiques.output_format_critique import OutputFormatCritique
from data_gen.llm.modules.parsable_base_module import ParsableBaseModule
from data_gen.llm.prompting.modules.nested_parsable_output_prompt import BasicNestedXMLParser
from data_gen.llm.prompting.parsable_prompt import ParsablePrompt
from data_gen.llm.wrapper.base_llm_wrapper import BaseLLMWrapper
from data_gen.news.newspaper import news_article_to_xml

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


class AddMissingDetailsToNewsArticleModule(ParsableBaseModule):

    def _create_formatting_critique(self, parsers: List[BasicNestedXMLParser]) -> BaseCritique:
        return OutputFormatCritique('add-details-news-article', parsers, EXPECTED_OUTPUT_FORMAT)

    def _preprocess_values(self, values) -> Dict:
        values['CURRENT_NEWS_ARTICLE_XML'] = news_article_to_xml(values)
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
            BasicNestedXMLParser('headline', './/headline', is_object=False, to_single=True, result_node='result', remove_node='scratchpad'),
            BasicNestedXMLParser('paragraphs', './/paragraph', is_object=True, to_single=False, result_node='result', remove_node='scratchpad')
        ]

    def get_file_name(self, prompt: ParsablePrompt, values: Dict):
        node_idx = values['CREATED_AT']
        newspaper = values['NEWSPAPER_PROFILE']
        subset_index: int = values['SUBSET_IDX']
        return f'N{node_idx:02d}-{self.name}-{newspaper}_{self.instruction_name}_subset-{subset_index}.json'


INSTRUCTIONS_V1 = """
You are an AI assistant tasked with improving a news article about a fictional event. Your goal is to ensure the article contains all specific details and information from a provided ground-truth outline of the fictional event. Follow these instructions carefully:

1. First, review the list of fictional named entities as background information:

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

2. Next, review the ground truth outline of the fictional event, including all details that must be communicated in the news article:

<event_info>
{{EVENT_INFO}}
</event_info>

3. Now, read the generated news article that needs to be revised:

<news-article>
{{CURRENT_NEWS_ARTICLE_XML}}
</news-article>

4. To revise the news article, follow these steps. Only revise the content of the article paragraphs. Do not revise the article title:
a) Analyze the style of the original news article. Pay attention to tone, vocabulary, and sentence structure. Any changes you make should maintain this style.
b) Go over each individual sentence from the ground truth outline.
c) Each sentence contains many details. Make sure that each of the details is communicated within the news article.
   - The details do not need to be communicated verbatim. It is okay if the same content is communicated in different terms.
   - Focus on all details from the sentence of the ground truth outline (numbers, dates, relations, relevant attributes and adjectives, etc). Consider every specific detail you can find.
d) Make subtle adjustments to the news article for each detail that is not yet communicated:
   - Add the information with minimal edits
   - Do not revise additional information from the news article such as speculations, rumors etc. Focus only on the missing information that must be integrated in the article.
e) Make any necessary adjustments to improve the flow and coherence of the article after your revisions.

5. Output the revised news article in the following format:

<result>
<scratchpad>
[Plan your approach here, outlining the main changes you intend to make]
</scratchpad>
<headline>
[Write a revised headline that accurately reflects the content of the article]
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
[Add more paragraphs as necessary, following the same format]
</article>
</result>

Remember to maintain the original style of the article while ensuring all factual statements are accurate according to the provided ground truth information.
"""


def get_instructions(version):
    if version == 'v1':
        out = INSTRUCTIONS_V1
    else:
        raise ValueError(version)

    return out.strip()
