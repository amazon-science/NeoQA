import random
from typing import Optional, List, Dict

from src.mglockne_story_line.llm.critiques.base_critique import BaseCritique
from src.mglockne_story_line.llm.critiques.modules.output_format_critique import OutputFormatCritique
from src.mglockne_story_line.llm.modules.parsable_base_module import ParsableBaseModule
from src.mglockne_story_line.llm.prompting.modules.nested_parsable_output_prompt import BasicNestedXMLParser
from src.mglockne_story_line.llm.prompting.parsable_prompt import ParsablePrompt
from src.mglockne_story_line.llm.wrapper.base_llm_wrapper import BaseLLMWrapper
from src.mglockne_story_line.story.event_sequence.elements.entity import Entity
from src.mglockne_story_line.story.event_sequence.elements.event import Continuation
from src.mglockne_story_line.util.entity_util import get_entity_categories
from src.mglockne_story_line.util.story_tools import create_history_xml


EXPECTED_OUTPUT_FORMAT = """
<results>
<thought_process>
[This includes the thought process for all summaries.]
</thought_process>

<summaries>
<summary>
<text>[Your first summary text here]</text>
<date>[Date for the first summary]</date>
</summary>

<summary>
<text>[Your second summary text here]</text>
<date>[Date for the second summary]</date>
</summary>

[... continue for all summaries ...]
</summaries>
</results>
""".strip()


class StoryContinuationModule(ParsableBaseModule):
    """
    This module creates various seed summaries that guide the generation of the followup event.
    We generate multiple possible continuations to steer the LLM into generating diverse continuations regarding various
    dimensions (level of impact, positive or negative story continuation, different subplots).
    We sample one to avoid LLMs following similar patterns of how the story evolves.
    """

    def _create_formatting_critique(self, parsers: List[BasicNestedXMLParser]) -> BaseCritique:
        return OutputFormatCritique('format-entity-update', parsers, EXPECTED_OUTPUT_FORMAT)

    def _preprocess_values(self, values) -> Dict:
        values['NUMBER_SUMMARIES'] = self.num_summaries

        # Make updated entities
        for key in get_entity_categories():
            if key not in values:
                values[f'{key}s_xml'] = ''
            else:
                entities: List[Entity] = values[key]
                values[f'{key}s_xml'] = '\n'.join([
                    ent.xml() for ent in entities
                ])

        # Make updated history
        last_date: str = values['date']
        if values['created_at'] > 1:
            assert len(values.get('history_xml', [])) > 0
        values['histories'] = values.get('histories', []) + [
            create_history_xml(last_date, values['story_item'])
        ]
        values['history_xml'] = '\n'.join(values['histories'])

        return super()._preprocess_values(values)

    def _postprocess_values(self, values: Dict) -> Dict:
        continuations: List[Continuation] = [
            Continuation.create(cont['text'], values['date'], cont['date']) for cont in values['continuations']
        ]

        random.shuffle(continuations)
        values['continuation'] = continuations[0]

        return values

    def __init__(self, llm: BaseLLMWrapper,name: str, instruction_name: str, num_summaries: int = 3):
        super().__init__(
            llm,
            name,
            instruction_name,
            get_instructions(instruction_name)
        )
        self.num_summaries: int = num_summaries

    def _get_parsers(self) -> List[BasicNestedXMLParser]:
        return [
            BasicNestedXMLParser('continuations', './/summary', is_object=True, allow_empty_list=False),
        ]


    def get_file_name(self, prompt: ParsablePrompt, values: Dict):
        init_headline = values['EVENT_SUMMARY_FOR_NAME'].lower().replace(' ', '-')
        node_idx = values['CREATED_AT']
        return f'N{node_idx:02d}-{self.name}-{self.num_summaries}-{init_headline}_{self.instruction_name}.json'





INSTRUCTIONS_V5 = """
You are an AI tasked with creating fictional future news summaries based on provided information. Your goal is to generate plausible and engaging continuations of an existing narrative. Follow these instructions carefully:

1. First, you will be given known entities in this fictional world. These will be provided in the following XML format:

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

3. Your task is to create {{NUMBER_SUMMARIES}} new summaries that describe future fictional events following the last event from the <history>. These new summaries should be consistent with the existing story and represent plausible continuations or developments of the original narrative.

4. For each summary, create:
   a. A summary text (a single concise sentence)
   b. The date on which this fictional next event happens

5. Before starting, check if the history of events indicates specific dates for followup events. Ensure your continuations are consistent with these expected followup events:
   - If the continuation happens before the specified date: The status of the outlined future event is unchanged and will still happen in the future.
   - If the continuation discusses the event at the specified date: The event is discussed as expected.
   - If the continuation happens after the expected event but includes a reason why the expected event did not happen.

6. Follow these guidelines when creating your summaries:
   a. Ensure all summaries are fictional and not based on real events or real people.
   b. Make the summaries sound realistic and plausible as follow-up stories to the previous outlines.
   c. Create summaries that are unbiased and objective in tone.
   d. Each summary MUST BE ONLY A SINGLE concise sentence.
   e. Each summary should follow a different substory or development stemming from the original article.
   f. Summaries may focus on different personas or organizations from the provided lists.
   g. Ensure a balance of positive and negative news stories, developments, and alternative scenarios.
   h. Consider various dimensions or personas that could be varied when generating diverse summaries.
   i. Multiple summaries may focus on the same aspect but describe diverse plausible scenarios of how the future plays out.

7. Output format:
   - Enclose each summary in <summary> tags.
   - Each summary must have two child properties:
     <text>[The generated summary]</text>
     <date>[The date for the next event]</date>
   - Before each summary, explain your thought process in <thought_process> tags. Make sure to identify all known followup events based on the provided history first, and verify that your continuations are consistent with these known followup events regarding the date.
   - Output everything within a <results> root node.

8. Special instructions:
   - The history and entities have special formatting. They sometimes include statements like {[PHRASE]|[ID]}. Read it as [PHRASE], while the [ID] specifies the ID of the linked entity.
   - Example: "I met {Boris Bowman|PERSON-1} yesterday." Read as: "I met Boris Bowman yesterday." (The ID of Boris Bowman is PERSON-1).
   - DO NOT use the {[PHRASE]|[ID]} formulation when generating new summaries.

9. Final reminders:
   - Repeat this process for all {{NUMBER_SUMMARIES}} summaries.
   - Ensure that each summary explores a different aspect or potential next step of the fictional situation presented in the HISTORY.
   - Each summary text MUST BE ONLY A SINGLE concise sentence.
   - The continuations should be diverse and can cover different alternatives of how the future event can play out.
   - Do not enumerate over the summaries.

Remember to maintain the desired format and brevity of the event summaries while creating plausible and engaging continuations of the narrative. Begin your response with the <results> tag.

Here's an example of the desired output format:

<results>
<thought_process>
[This includes the thought process for all summaries.]
</thought_process>

<summaries>
<summary>
<text>[Your first summary text here]</text>
<date>[Date for the first summary]</date>
</summary>

<summary>
<text>[Your second summary text here]</text>
<date>[Date for the second summary]</date>
</summary>

[... continue for all summaries ...]
</summaries>
</results>
"""

INSTRUCTIONS_V4 = """
You are an AI tasked with creating fictional future news summaries based on provided information. Your goal is to generate plausible and engaging continuations of an existing narrative. Here's what you have to work with:

First, here are the known entities in this fictional world:

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

Now, here is the history of events that have already occurred in this fictional world:

<history>
{{HISTORY_XML}}
</history>

Your task is to create new summaries that describe future newsworthy fictional events that follow the last event from the HISTORY. These new summaries should be consistent with the existing story and represent plausible continuations or developments of the original narrative.

Follow these guidelines when creating your summaries:

1. Ensure all summaries are fictional and not based on real events or real people.
2. Make the summaries sound realistic and plausible as follow-up stories to the previous outlines. Ensure each summary is a plausible continuation to the last outline in the HISTORY. 
3. Create summaries that are unbiased and objective in tone.
4. Each summary MUST BE ONLY A SINGLE concise sentence.
5. Each summary should follow a different substory or development stemming from the original article.
6. Summaries may focus on different personas or organizations from the provided lists.
7. Ensure a balance of positive and negative news stories.
8. Consider various dimensions or personas that could be varied when generating diverse summaries.

Please generate {{NUMBER_SUMMARIES}} different summaries. Each summary should be enclosed in <summary> tags. Before each summary, briefly explain your thought process for creating that particular summary in <thought_process> tags.

Output everything within a <results> root node.

Special instructions:
- The history and the entities have some special formatting. They sometimes include statements like {[PHRASE]|[ID]}. You should read it as [PHRASE], while the [ID] specifies the ID of the linked entity.
  Example: "I met {Boris Bowman|PERSON-1} yesterday." Read as: "I met Boris Bowman yesterday." (The ID of Boris Bowman is PERSON-1).
- DO NOT use the {[PHRASE]|[ID]} formulation when generating new summaries.

Here's an example of the desired output format:

<results>
<thought_process>
[This includes the thought process for all summaries.]
</thought_process>

<summaries>
<summary>[Your first single-sentence fictional future event summary here]</summary>
<summary>[Your second single-sentence fictional future event summary here]</summary>
</summaries>
</results>

Repeat this process for all {{NUMBER_SUMMARIES}} summaries. Ensure that each summary explores a different aspect or potential next step of the fictional situation presented in the HISTORY.

Remember, each summary MUST BE ONLY A SINGLE concise sentence. This is crucial for maintaining the desired format and brevity of the event summaries. Summaries do not need to be conclusive and can also cover only small events. Do not enumerate over the summaries.
"""


INSTRUCTIONS_V1_DIVERSE = """
You are an AI tasked with creating fictional future news summaries based on provided information. Your goal is to generate plausible continuations of an existing narrative. Follow these instructions carefully:

1. First, you will be given known entities in this fictional world. These will be provided in the following format:

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

3. Your task is to create {{NUMBER_SUMMARIES}} new summaries that describe future fictional events following the last event from the <history>. These new summaries should be consistent with the existing story and represent plausible continuations or developments of the original narrative.

4. For each summary, create:
   a. A summary text (a single concise sentence)
   b. The date on which this fictional next event happens

5. Before starting, check if the history of events indicates specific dates for followup events. Ensure your continuations are consistent with these expected followup events. All your summaries must either concern this event, or happen before this event.

6. Make sure that each summary you generate focuses on at least one of the main named entities from the history of events.

7. Follow these guidelines when creating your summaries:
   a. Ensure all summaries are fictional and not based on real events or real people.
   b. Make the summaries sound realistic and plausible as follow-up stories to the previous outlines.
   c. Create summaries that are unbiased and objective in tone.
   d. Each summary MUST BE ONLY A SINGLE concise sentence.
   e. Each summary must be contradictory to at least one other generated summary.
   f. Summaries may focus on different personas or organizations from the provided lists.
   g. Ensure a balance of positive and negative news stories, developments, and alternative scenarios.
   h. Consider various dimensions or personas that could be varied when generating diverse summaries.

Try to be diverse in the summaries you generate. Consider different plausible substories and vary between high impact and low impact next events, as well as positive or negative developments of the events.

8. Output format:
   - Enclose each summary in <summary> tags.
   - Each summary must have two child properties:
     <text>[The generated summary]</text>
     <date>[The date for the next event]</date>
   - Before each summary, explain your thought process in <thought_process> tags. Make sure to identify all known followup events based on the provided history first, and verify that your continuations are consistent with these known followup events regarding the date.
   - Output everything within a <results> root node.

9. Special instructions:
   - The history and entities have special formatting. They sometimes include statements like {[PHRASE]|[ID]}. Read it as [PHRASE], while the [ID] specifies the ID of the linked entity.
   - Example: "I met {Boris Bowman|PERSON-1} yesterday." Read as: "I met Boris Bowman yesterday." (The ID of Boris Bowman is PERSON-1).
   - DO NOT use the {[PHRASE]|[ID]} formulation when generating new summaries.

10. Final reminders:
   - Repeat this process for all {{NUMBER_SUMMARIES}} summaries.
   - Ensure that each summary explores a different aspect or potential next step of the fictional situation presented in the HISTORY.
   - Each summary text MUST BE ONLY A SINGLE concise sentence.
   - The continuations should be diverse in terms of high (at most one), medium and low impact, positive and negative story developments, etc., and can cover different alternatives of how the future event can play out.
   - Do not enumerate over the summaries.

Remember to maintain the desired format and brevity of the event summaries while creating plausible and engaging continuations of the narrative. Begin your response with the <results> tag.

Here's an example of the desired output format:

<results>
<thought_process>
[This includes the thought process for all summaries.]
</thought_process>

<summaries>
<summary>
<text>[Your first summary text here]</text>
<date>[Date for the first summary]</date>
</summary>

<summary>
<text>[Your second summary text here]</text>
<date>[Date for the second summary]</date>
</summary>

[... continue for all summaries ...]
</summaries>
</results>

"""



INSTRUCTIONS_V2_DIVERSE = """
You are an AI tasked with creating fictional future news summaries based on provided information. Your goal is to generate plausible continuations of an existing narrative. Follow these instructions carefully:

1. First, you will be given known entities in this fictional world. These will be provided in the following format:
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

3. Your task is to create {{NUMBER_SUMMARIES}} new summaries that describe future fictional events following the last event from the <history>. These new summaries should be consistent with the existing story and represent plausible continuations or developments of the original narrative.

4. For each summary, create:
   a. A summary text (a single concise sentence)
   b. The date on which this fictional next event happens

5. Before starting, check if the history of events indicates specific dates for followup events. Ensure your continuations are consistent with these expected followup events. All your summaries must either concern this event, or happen before this event.

6. Make sure that each summary you generate focuses on at least one of the main named entities from the history of events.

7. Follow these guidelines when creating your summaries:
   a. Ensure all summaries are fictional and not based on real events or real people.
   b. Make the summaries sound realistic and plausible as follow-up stories to the previous outlines. 
   c. Think about plausible next events based on the fictional named entities, the history of the past fictional events and the genre {{GENRE}}. 
   d. Create summaries that are unbiased and objective in tone.
   e. Each summary MUST BE ONLY A SINGLE concise sentence.
   f. Summaries may focus on different personas or organizations from the provided lists.
   g. Ensure a balance of positive and negative news stories, developments, and alternative scenarios.
   h. Consider various dimensions or personas that could be varied when generating diverse summaries.

Try to be diverse in the summaries you generate. Consider different plausible substories and vary:
- between impact: Try to create various low-impact next events, but you may also at times mix in an event with a slightly higher impact.
- between directions: Vary between positive and negative story developments. Think about how stories in the {{GENRE}} genre progress in the real-world, NOT in a novel. Provide various realistic alternatives for how the story may progress in either direction.
- between different key named entities of the fictional story.

8. Output format:
   - Enclose each summary in <summary> tags.
   - Each summary must have two child properties:
     <text>[The generated summary]</text>
     <date>[The date for the next event]</date>
   - Before each summary, explain your thought process in <thought_process> tags. Make sure to identify all known followup events based on the provided history first, and verify that your continuations are consistent with these known followup events regarding the date.
   - Output everything within a <results> root node.

9. Special instructions:
   - The history and entities have special formatting. They sometimes include statements like {[PHRASE]|[ID]}. Read it as [PHRASE], while the [ID] specifies the ID of the linked entity.
   - Example: "I met {Boris Bowman|PERSON-1} yesterday." Read as: "I met Boris Bowman yesterday." (The ID of Boris Bowman is PERSON-1).
   - DO NOT use the {[PHRASE]|[ID]} formulation when generating new summaries.

10. Final reminders:
   - Repeat this process for all {{NUMBER_SUMMARIES}} summaries.
   - Ensure that each summary explores a different aspect or potential next step of the fictional situation presented in the HISTORY.
   - Each summary text MUST BE ONLY A SINGLE concise sentence.
   - The continuations should be diverse in terms of high (at most one), medium and low impact, positive and negative story developments, etc., and can cover different alternatives of how the future event can play out.
   - Do not enumerate over the summaries.
   - When brainstorming future event summaries, carefully consider whether each continuation aligns with the provided history of events, provided named entities, and the genre {{GENRE}}. Before creating summaries with global or large-scale impact, double-check if such developments seem plausible based on how real-world events of this type would typically unfold. Focus on what fits the genre and provided history, ensuring that every dimension feels realistic and consistent with the context.

Remember to maintain the desired format and brevity of the event summaries while creating plausible and engaging continuations of the narrative. Begin your response with the <results> tag.

Here's an example of the desired output format:

<results>
<thought_process>
[This includes the thought process for all summaries.]
</thought_process>

<summaries>
<summary>
<text>[Your first summary text here]</text>
<date>[Date for the first summary]</date>
</summary>

<summary>
<text>[Your second summary text here]</text>
<date>[Date for the second summary]</date>
</summary>

[... continue for all summaries ...]
</summaries>
</results>
"""


INSTRUCTIONS_V3_DIVERSE = """
You are an AI tasked with creating fictional future news summaries based on provided information. Your goal is to generate plausible continuations of an existing narrative. Follow these instructions carefully:

1. First, you will be given known entities in this fictional world. These will be provided in the following format:
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

3. Your task is to create {{NUMBER_SUMMARIES}} new summaries that describe future fictional events following the last event from the <history>. These new summaries should be consistent with the existing story and represent plausible continuations or developments of the original narrative.

4. For each summary, create:
   a. A summary text (a single concise sentence)
   b. The date on which this fictional next event happens

5. Before starting, check if the history of events indicates specific dates for followup events. Ensure your continuations are consistent with these expected followup events. All your summaries must either concern this event, or happen before this event.

6. Make sure that each summary you generate focuses on at least one of the main named entities from the history of events.

7. Follow these guidelines when creating your summaries:
   a. Ensure all summaries are fictional and not based on real events or real people.
   b. Make the summaries sound realistic and plausible as follow-up stories to the previous outlines. 
   c. Think about plausible next events based on the fictional named entities, the history of the past fictional events and the genre {{GENRE}}. 
   d. Create summaries that are unbiased and objective in tone.
   e. Each summary MUST BE ONLY A SINGLE concise sentence.
   f. Summaries may focus on different personas or organizations from the provided lists.
   g. Ensure a balance of positive and negative news stories, developments, and alternative scenarios.
   h. Consider various dimensions or personas that could be varied when generating diverse summaries.

Try to be diverse in the summaries you generate. Consider different plausible substories and vary:
- between impact: Try to create various low-impact next events, but you may also at times mix in an event with a slightly higher impact.
- between directions: Vary between positive and negative story developments. Think about how stories in the {{GENRE}} genre progress in the real-world, NOT in a novel. Provide various realistic alternatives for how the story may progress in either direction.
- between different key named entities of the fictional story.

8. Output format:
   - Enclose each summary in <summary> tags.
   - Each summary must have two child properties:
     <text>[The generated summary]</text>
     <date>[The date for the next event]</date>
   - Before each summary, explain your thought process in <thought_process> tags. Make sure to identify all known followup events based on the provided history first, and verify that your continuations are consistent with these known followup events regarding the date.
   - Output everything within a <results> root node.

9. Special instructions:
   - The history and entities have special formatting. They sometimes include statements like {[PHRASE]|[ID]}. Read it as [PHRASE], while the [ID] specifies the ID of the linked entity.
   - Example: "I met {Boris Bowman|PERSON-1} yesterday." Read as: "I met Boris Bowman yesterday." (The ID of Boris Bowman is PERSON-1).
   - DO NOT use the {[PHRASE]|[ID]} formulation when generating new summaries.
   - Do not exaggerate the summaries. Avoid using words like "groundbreaking", "worldwide", "global". Keep the summaries realistic.
   - Do not create summaries with global or national impact unless the genre specifically requires it. Instead, focus on smaller or local developments.
   - Do not focus on technological discoveries or topics like AI tools, virtual reality, augmented reality, 3D-modelling, quantum computing, etc. You may include such topics only if they are HIGHLY relevant to the genre {{GENRE}} AND the provided history of events.
   - Focus on realistic, meaningful summaries with specific details and developments that align with typical, realistic scenarios of the genre {{GENRE}}.

10. Final reminders:
   - Repeat this process for all {{NUMBER_SUMMARIES}} summaries.
   - Ensure that each summary explores a different aspect or potential next step of the fictional situation presented in the HISTORY.
   - Each summary text MUST BE ONLY A SINGLE concise sentence.
   - The continuations should be diverse in terms of high (at most one), medium and low impact, positive and negative story developments, etc., and can cover different alternatives of how the future event can play out.
   - Do not enumerate over the summaries.
   - When brainstorming future event summaries, carefully consider whether each continuation aligns with the provided history of events, provided named entities, and the genre {{GENRE}}. Before creating summaries with global or large-scale impact, double-check if such developments seem plausible based on how real-world events of this type would typically unfold. Focus on what fits the genre and provided history, ensuring that every dimension feels realistic and consistent with the context.

Remember to maintain the desired format and brevity of the event summaries while creating plausible and engaging continuations of the narrative.

Here's an example of the desired output format:

<results>
<thought_process>
[This includes the thought process for all summaries.]
</thought_process>

<summaries>
<summary>
<text>[Your first summary text here]</text>
<date>[Date for the first summary]</date>
</summary>

<summary>
<text>[Your second summary text here]</text>
<date>[Date for the second summary]</date>
</summary>

[... continue for all summaries ...]
</summaries>
</results>
"""


def get_instructions(version: str) -> str:
    if version == 'v4':
        out = INSTRUCTIONS_V4
    elif version == 'v5':
        out = INSTRUCTIONS_V5
    elif version == 'v1-diverse':
        out = INSTRUCTIONS_V1_DIVERSE
    elif version == 'v2-diverse':
        out = INSTRUCTIONS_V2_DIVERSE
    elif version == 'v3-diverse':
        out = INSTRUCTIONS_V3_DIVERSE
    else:
        raise ValueError(version)

    return out.strip()