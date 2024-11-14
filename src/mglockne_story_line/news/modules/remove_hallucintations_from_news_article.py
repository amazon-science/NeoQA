from collections import defaultdict
from typing import Dict, List, Optional, Set

from src.mglockne_story_line.llm.critiques.base_critique import BaseCritique
from src.mglockne_story_line.llm.critiques.modules.output_format_critique import OutputFormatCritique
from src.mglockne_story_line.llm.critiques.modules.parsable_root_node_critique import ParsableRootNodeCritique
from src.mglockne_story_line.llm.modules.parsable_base_module import ParsableBaseModule
from src.mglockne_story_line.llm.prompting.modules.nested_parsable_output_prompt import BasicNestedXMLParser
from src.mglockne_story_line.llm.prompting.parsable_prompt import ParsablePrompt
from src.mglockne_story_line.llm.wrapper.base_llm_wrapper import BaseLLMWrapper
from src.mglockne_story_line.news.news_profiles.get_newspaper_profile import get_newspaper_profile_prompt
from src.mglockne_story_line.news.newspaper import news_article_to_xml

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


class RemoveHallucinationsModule(ParsableBaseModule):

    def _create_formatting_critique(self, parsers: List[BasicNestedXMLParser]) -> BaseCritique:
        return OutputFormatCritique('rm-hallucinations-news-article', parsers, EXPECTED_OUTPUT_FORMAT)

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
You are tasked with improving a news article about a fictional event. Your goal is to ensure the article is faithful to the provided ground truth information while maintaining the general style of the original news article. Follow these instructions carefully:

1. First, review the ground truth information about the fictional named entities:

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

2. Next, review the ground truth information about the fictional event:

<event_info>
{{EVENT_INFO}}
</event_info>

3. Now, read the generated news article that needs to be revised:

<news-article>
{{CURRENT_NEWS_ARTICLE_XML}}
</news-article>

4. To revise the news article, follow these steps. Only revise the content of the article paragraphs. Do not revise the article title:

a) Analyze the style of the original news article. Pay attention to tone, vocabulary, and sentence structure. Any changes you make should maintain this style.

b) Carefully examine all factual statements in the article. Determine if each statement can be verified based on the ground truth information provided.

c) Identify any factual statements that are:
   - Expressed as facts but are unverifiable based on the ground truth
   - Incorrect according to the ground truth information

d) For each problematic statement, choose one of the following actions:
   - Remove the unverifiable or incorrect factual statement entirely.
   - Rephrase the statement to clearly indicate that it is not a verified fact (e.g., by using hedging language or attributing the information to an unnamed source).

e) Ensure that no information beyond what is provided in the ground truth is introduced as fact. However, you may include unverified information if it is presented as speculation, question, rumor or involves appropriate hedging.

f) Make any necessary adjustments to improve the flow and coherence of the article after your revisions.

g) Make minimal edits to the news article. Only make necessary revisions to avoid problematic factual statements. Explain and justify each change you make.

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
