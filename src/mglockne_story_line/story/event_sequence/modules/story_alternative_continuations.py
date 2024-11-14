import random
from typing import List, Dict

from src.mglockne_story_line.llm.critiques.base_critique import BaseCritique
from src.mglockne_story_line.llm.critiques.modules.output_format_critique import OutputFormatCritique
from src.mglockne_story_line.llm.modules.parsable_base_module import ParsableBaseModule
from src.mglockne_story_line.llm.prompting.modules.nested_parsable_output_prompt import BasicNestedXMLParser
from src.mglockne_story_line.llm.prompting.parsable_prompt import ParsablePrompt
from src.mglockne_story_line.llm.wrapper.base_llm_wrapper import BaseLLMWrapper
from src.mglockne_story_line.story.event_sequence.elements.event import Continuation

EXPECTED_OUTPUT_FORMAT = """
<results>
<thought_process>
[Your explanation of the thought process, including identification of known followup events and verification of consistency]
</thought_process>
<summaries>
<summary>
<text>[First alternative summary]</text>
<date>[Date of the event]</date>
</summary>
<summary>
<text>[Second alternative summary]</text>
<date>[Date of the event]</date>
</summary>
[Additional summaries as needed]
</summaries>
</results>
""".strip()


class AlternativeStoryContinuationModule(ParsableBaseModule):
    """
    This module generates contradictory story continuations based on a selected s tory continuation.
    Any of the generated continuations makes the other story continuations impossible.
    This helps to reduce the risk of generating identical plots to real-world stories, as each real-world story can only
    be based on one of the contradictory continuations.
    """

    def _create_formatting_critique(self, parsers: List[BasicNestedXMLParser]) -> BaseCritique:
        return OutputFormatCritique('format-entity-update', parsers, EXPECTED_OUTPUT_FORMAT)

    def _preprocess_values(self, values) -> Dict:
        continuation: Continuation = values['continuation']
        values['CONTINUATION_TEXT'] = continuation.summary
        values['CONTINUATION_DATE'] = continuation.continuation_date
        values['NUM_ALTERNATIVES'] = self.num_alternatives
        return super()._preprocess_values(values)

    def _postprocess_values(self, values: Dict) -> Dict:
        continuations: List[Continuation] = [
            Continuation.create(cont['text'], values['date'], cont['date']) for cont in values['alt_continuations']
        ]
        continuations.append(values['continuation'])
        random.shuffle(continuations)
        values['continuation'] = continuations[0]
        return values

    def __init__(self, llm: BaseLLMWrapper,name: str, instruction_name: str, num_alternatives: int = 3):
        super().__init__(
            llm,
            name,
            instruction_name,
            get_instructions(instruction_name)
        )
        self.num_alternatives: int = num_alternatives

    def _get_parsers(self) -> List[BasicNestedXMLParser]:
        return [
            BasicNestedXMLParser('alt_continuations', './/summary', is_object=True, allow_empty_list=False),
        ]


    def get_file_name(self, prompt: ParsablePrompt, values: Dict):
        init_headline = values['EVENT_SUMMARY_FOR_NAME'].lower().replace(' ', '-')
        node_idx = values['CREATED_AT']
        return f'N{node_idx:02d}-{self.name}-{self.num_alternatives}-{init_headline}_{self.instruction_name}.json'


INSTRUCTIONS_V1: str = """
You are an AI tasked with creating alternative fictional future news summaries based on provided information. Your goal is to generate summaries of plausible alternative continuations of an existing narrative. Follow these instructions carefully:

1. First, you will be given known entities in this fictional world:

<known_entities>
{{LOCATIONS_XML}}
{{PERSONS_XML}}
{{ORGANIZATIONS_XML}}
{{PRODUCTS_XML}}
{{ARTS_XML}}
{{EVENTS_XML}}
{{BUILDINGS_XML}}
{{MISCELLANEOUSS_XML}}
</known_entities>

2. Next, you will be provided with the history of events that have already occurred in this fictional world:

<history>
{{HISTORY_XML}}
</history>

3. You will be given the following plausible summary of how the fictional event evolves:
<continuation_summary>
<text>{{CONTINUATION_TEXT}}</text>
<date>{{CONTINUATION_DATE}}</date>
</continuation_summary>

4. Your task is to create {{NUM_ALTERNATIVES}} contradictory alternative summaries of how the fictional event can progress based on the provided continuation summary. Each of these continuation summaries must make subtle changes to the continuation summary such that they are contradictory alternatives to one another. If the story evolves with one of the continuation summaries, the other ones cannot happen anymore.

5. When changing the provided continuation summary, maintain these key properties:
   a) The central topic and involved main entity
   b) The stance (whether this is a positive, neutral or negative story evolvement)
   c) The impact (whether this is a high impact, medium impact or low impact evolvement)
   d) The same date

6. Guidelines for creating alternative summaries:
   - Ensure each new continuation summary is consistent with the existing story and represents a plausible continuation or development of the original narrative.
   - Write each continuation summary as a single concise sentence in an objective tone.
   - Make sure your continuations are consistent with any known followup events regarding the date.

7. Output format:
   - Enclose your entire response in <results> tags.
   - Before the summaries, explain your thought process in <thought_process> tags. Make sure to identify all known followup events based on the provided history first, and verify that your continuations are consistent with these known followup events regarding the date.
   - Enclose all summaries in <summaries> tags.
   - For each summary:
     <summary>
       <text>[The generated summary]</text>
       <date>[The date for the next event]</date>
     </summary>

8. Special instructions:
   - The history and entities have special formatting. They sometimes include statements like {[PHRASE]|[ID]}. Read it as [PHRASE], while the [ID] specifies the ID of the linked entity.
   - Example: "I met {Boris Bowman|PERSON-1} yesterday." Read as: "I met Boris Bowman yesterday." (The ID of Boris Bowman is PERSON-1).
   - DO NOT use the {[PHRASE]|[ID]} formulation when generating new summaries.

9. Here's an example of the desired output format:

<results>
<thought_process>
[Your explanation of the thought process, including identification of known followup events and verification of consistency]
</thought_process>
<summaries>
<summary>
<text>[First alternative summary]</text>
<date>[Date of the event]</date>
</summary>
<summary>
<text>[Second alternative summary]</text>
<date>[Date of the event]</date>
</summary>
[Additional summaries as needed]
</summaries>
</results>

Remember to maintain the desired format and brevity of the event continuations while creating plausible and engaging continuations of the narrative. Begin your response with the <results> tag and end it with the </results> tag.
"""

INSTRUCTIONS_V2: str = """
You are an AI tasked with creating alternative fictional future news summaries based on provided information. 
Your goal is to generate summaries of plausible alternative continuations of an existing narrative. Follow these instructions carefully:

1. First, you will be given known entities in this fictional world:

<known_entities>
{{LOCATIONS_XML}}
{{PERSONS_XML}}
{{ORGANIZATIONS_XML}}
{{PRODUCTS_XML}}
{{ARTS_XML}}
{{EVENTS_XML}}
{{BUILDINGS_XML}}
{{MISCELLANEOUSS_XML}}
</known_entities>

2. Next, you will be provided with the history of events that have already occurred in this fictional world:

<history>
{{HISTORY_XML}}
</history>

3. You will be given the following plausible summary of how the fictional event evolves:
<continuation_summary>
<text>{{CONTINUATION_TEXT}}</text>
<date>{{CONTINUATION_DATE}}</date>
</continuation_summary>

4. Your task is to create {{NUM_ALTERNATIVES}} contradictory alternative summaries of how the fictional event can progress based on the provided continuation summary. 
Each of these continuation summaries must make subtle changes to the continuation summary such that they are contradictory alternatives to one another.
This means, if the story evolves with one of the continuation summaries, the other ones cannot happen anymore.

5. When changing the provided continuation summary, maintain these key properties:
   a) The central topic and involved main entity
   b) The stance (whether this is a positive, neutral or negative story evolvement)
   c) The impact (whether this is a high impact, medium impact or low impact evolvement)
   d) The same date

6. Guidelines for creating alternative summaries:
   - Ensure each new continuation summary is consistent with the existing story and represents a plausible continuation or development of the original narrative.
   - Write each continuation summary as a single concise sentence in an objective tone.
   - Make sure your continuations are consistent with any known followup events regarding the date.

7. Output format:
   - Enclose your entire response in <results> tags.
   - Before the summaries, explain your thought process in <thought_process> tags. Make sure to identify all known followup events based on the provided history first, and verify that your continuations are consistent with these known followup events regarding the date.
   - Enclose all summaries in <summaries> tags.
   - For each summary:
     <summary>
       <text>[The generated summary]</text>
       <date>[The date for the next event]</date>
     </summary>

8. Special instructions:
   - The history and entities have special formatting. They sometimes include statements like {[PHRASE]|[ID]}. Read it as [PHRASE], while the [ID] specifies the ID of the linked entity.
   - Example: "I met {Boris Bowman|PERSON-1} yesterday." Read as: "I met Boris Bowman yesterday." (The ID of Boris Bowman is PERSON-1).
   - DO NOT use the {[PHRASE]|[ID]} formulation when generating new summaries.
   - When brainstorming alternative event summaries, carefully consider whether each continuation aligns with the provided history of events, provided named entities, and the genre {{GENRE}}. Before creating summaries with global or large-scale impact, double-check if such developments seem plausible based on how real-world events of this type would typically unfold. Focus on what fits the genre and provided history, ensuring that every dimension feels realistic and consistent with the context.


9. Here's an example of the desired output format:

<results>
<thought_process>
[Your explanation of the thought process, including identification of known followup events and verification of consistency]
</thought_process>
<summaries>
<summary>
<text>[First alternative summary]</text>
<date>[Date of the event]</date>
</summary>
<summary>
<text>[Second alternative summary]</text>
<date>[Date of the event]</date>
</summary>
[Additional summaries as needed]
</summaries>
</results>

Remember to maintain the desired format and brevity of the event continuations while creating plausible and engaging continuations of the narrative. Begin your response with the <results> tag and end it with the </results> tag.
"""


INSTRUCTIONS_V3: str = """
You are an AI tasked with creating alternative fictional future news summaries based on provided information. 
Your goal is to generate summaries of plausible alternative continuations of an existing narrative. Follow these instructions carefully:

1. First, you will be given known entities in this fictional world:

<known_entities>
{{LOCATIONS_XML}}
{{PERSONS_XML}}
{{ORGANIZATIONS_XML}}
{{PRODUCTS_XML}}
{{ARTS_XML}}
{{EVENTS_XML}}
{{BUILDINGS_XML}}
{{MISCELLANEOUSS_XML}}
</known_entities>

2. Next, you will be provided with the history of events that have already occurred in this fictional world:

<history>
{{HISTORY_XML}}
</history>

3. You will be given the following plausible summary of how the fictional event evolves:
<continuation_summary>
<text>{{CONTINUATION_TEXT}}</text>
<date>{{CONTINUATION_DATE}}</date>
</continuation_summary>

4. Your task is to create {{NUM_ALTERNATIVES}} contradictory alternative summaries of how the fictional event can progress based on the provided continuation summary. 
Each of these continuation summaries must make subtle changes to the continuation summary such that they are contradictory alternatives to one another.
This means, if the story evolves with one of the continuation summaries, the other ones cannot happen anymore.

5. When changing the provided continuation summary, maintain these key properties:
   a) The central topic and involved main entity
   b) The stance (whether this is a positive, neutral or negative story evolvement)
   c) The impact (whether this is a high impact, medium impact or low impact evolvement)
   d) The same date

6. Guidelines for creating alternative summaries:
   - Ensure each new continuation summary is consistent with the existing story and represents a plausible continuation or development of the original narrative.
   - Write each continuation summary as a single concise sentence in an objective tone.
   - Make sure your continuations are consistent with any known followup events regarding the date.

7. Output format:
   - Enclose your entire response in <results> tags.
   - Before the summaries, explain your thought process in <thought_process> tags. Make sure to identify all known followup events based on the provided history first, and verify that your continuations are consistent with these known followup events regarding the date.
   - Enclose all summaries in <summaries> tags.
   - For each summary:
     <summary>
       <text>[The generated summary]</text>
       <date>[The date for the next event]</date>
     </summary>

8. Special instructions:
   - The history and entities have special formatting. They sometimes include statements like {[PHRASE]|[ID]}. Read it as [PHRASE], while the [ID] specifies the ID of the linked entity.
   - Example: "I met {Boris Bowman|PERSON-1} yesterday." Read as: "I met Boris Bowman yesterday." (The ID of Boris Bowman is PERSON-1).
   - DO NOT use the {[PHRASE]|[ID]} formulation when generating new summaries.
   - When brainstorming alternative event summaries, carefully consider whether each continuation aligns with the provided history of events, provided named entities, and the genre {{GENRE}}. Before creating summaries with global or large-scale impact, double-check if such developments seem plausible based on how real-world events of this type would typically unfold. Focus on what fits the genre and provided history, ensuring that every dimension feels realistic and consistent with the context.
   - Do not exaggerate the summaries. Avoid making summaries "groundbreaking." Keep the summaries realistic.
   - Do not create summaries with global or national impact unless the genre specifically requires it. Instead, focus on smaller or local developments.
   - Do not focus on technological discoveries or topics like AI tools, virtual reality, quantum computing, etc. You may include such topics only if they are HIGHLY relevant to the genre {{GENRE}} AND the provided history of events.
   - Focus on realistic, meaningful summaries with specific details and developments that align with typical, realistic scenarios of the genre {{GENRE}}.

9. Here's an example of the desired output format:

<results>
<thought_process>
[Your explanation of the thought process, including identification of known followup events and verification of consistency]
</thought_process>
<summaries>
<summary>
<text>[First alternative summary]</text>
<date>[Date of the event]</date>
</summary>
<summary>
<text>[Second alternative summary]</text>
<date>[Date of the event]</date>
</summary>
[Additional summaries as needed]
</summaries>
</results>

Remember to maintain the desired format and brevity of the event continuations while creating plausible and engaging continuations of the narrative. Begin your response with the <results> tag and end it with the </results> tag.
"""



def get_instructions(version: str) -> str:
    if version == 'v1':
        out = INSTRUCTIONS_V1
    elif version == 'v2':
        out = INSTRUCTIONS_V2
    elif version == 'v3':
        out = INSTRUCTIONS_V3
    else:
        raise ValueError(version)

    return out.strip()