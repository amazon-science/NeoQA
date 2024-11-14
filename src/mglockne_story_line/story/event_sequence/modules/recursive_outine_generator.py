from typing import List, Dict

from src.mglockne_story_line.llm.critiques.base_critique import BaseCritique
from src.mglockne_story_line.story.seeds.critiques.crazy_topic_critique import CrazyTopicCritique
from src.mglockne_story_line.llm.critiques.modules.output_format_critique import OutputFormatCritique
from src.mglockne_story_line.llm.modules.parsable_base_module import ParsableBaseModule
from src.mglockne_story_line.llm.prompting.modules.nested_parsable_output_prompt import BasicNestedXMLParser
from src.mglockne_story_line.llm.prompting.parsable_prompt import ParsablePrompt
from src.mglockne_story_line.llm.verifiers.named_unified_output_verifier import NamedUnifiedOutputVerifier
from src.mglockne_story_line.llm.wrapper.base_llm_wrapper import BaseLLMWrapper

EXPECTED_OUTPUT_FORMAT = """
The output format is incorrect. Please output the results in the following format:
<results>
<date>Month Day, Year</date>
<outline>
<storyitem>First story item</storyitem>
<storyitem>Second story item</storyitem>
...
<storyitem>Last story item</storyitem>
</outline>
</results>
""".strip()

class OutlineGenerationModule(ParsableBaseModule):
    """
    This module generates the fictional outline.
    """

    def _create_critiques(self) -> List[BaseCritique]:
        return [CrazyTopicCritique('story_item', 'list')]

    def _create_formatting_critique(self, parsers: List[BasicNestedXMLParser]) -> BaseCritique:
        return OutputFormatCritique('format-seed-outline', parsers, EXPECTED_OUTPUT_FORMAT)

    def __init__(self, llm: BaseLLMWrapper, name: str, instruction_name: str, num_story_items: int):
        super().__init__(
            llm,
            name,
            instruction_name,
            get_instructions(instruction_name),
            max_critiques=5
        )
        self.num_story_items: int = num_story_items

    def _preprocess_values(self, values) -> Dict:
        values['num_storyitems'] = self.num_story_items
        values['history_xml'] = '\n'.join(values['histories'])
        return values

    def _get_verifiers(self) -> List[NamedUnifiedOutputVerifier]:
        return []

    def _get_parsers(self) -> List[BasicNestedXMLParser]:
        return [
            BasicNestedXMLParser('story_item', './/storyitem', is_object=False, result_node='results', remove_node='scratchpad'),
            BasicNestedXMLParser('date', 'date', is_object=False, to_single=True, result_node='results', remove_node='scratchpad')
        ]

    def get_file_name(self, prompt: ParsablePrompt, values: Dict):
        summary = values['EVENT_SUMMARY_FOR_NAME'].lower().replace(' ', '-')
        node_idx = values['CREATED_AT']
        return f'N{node_idx:02d}-{self.name}-{summary}_{self.instruction_name}.json'


def get_instructions(version: str) -> str:
    if version == 'v1':
        out: str = INSTRUCTIONS_V1
    elif version == 'v2':
        out: str = INSTRUCTIONS_V2
    elif version == 'v3':
        out: str = INSTRUCTIONS_V3
    elif version == 'v4':
        out: str = INSTRUCTIONS_V4
    elif version == 'v5':
        out: str = INSTRUCTIONS_V5
    else:
        raise ValueError(version)
    return out.strip()

INSTRUCTIONS_V5 = """
You are an AI assistant tasked with generating an outline for a fictional event. Your goal is to create a realistic, entirely fictional event that does not overlap with real-world named entities or known fictional named entities. Follow these instructions carefully:

First, review the list of already known fictional named entities of this fictional world:

<known_entities>
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
</known_entities>
Next, review the outline of previous events that have occurred in this fictional world:

<history>
{{HISTORY_XML}}
</history>

Now, consider the following information about the new event you need to generate as a continuation of the past events:

Date: {{PROVIDED_DATE}}

Event Summary: {{EVENT_SUMMARY}}

Genre: {{GENRE}}

Follow these guidelines to generate the event outline:

1. Create an entirely fictional event based on the given genre, event summary, and history of previous events. The event must be realistic but must not reference any existing real-world or known fictional named entities.
2. Invent new named entities as needed, ensuring they don't exist in the real world or in existing works of fiction. When creating names, use unique combinations unlikely to match real named entities.
3. Construct the outline using short, concise, factual, and objective statements. Each statement must discuss only one fact or sub-event, structured sequentially in a logical temporal order when applicable.
4. Ensure all statements form a coherent outline.
5. Output each statement within a <storyitem> tag.
6. Generate exactly {{NUM_STORYITEMS}} distinct story items.
7. Ensure logical progression, with each statement following chronologically when applicable. Include a mix of main events, reactions, consequences, and contextual information.
8. Make storyitems as atomic as possible, communicating only a single piece of relevant information per item. Do not merge multiple pieces of information into one storyitem.
9. Ensure the story sounds realistic without explicitly stating it's fictional.
10. Maintain consistency with the provided <history> that discusses past events fictional events. The outline must logically follow chronological events described in the history.
11. Incorporate some or all of the provided named entities in your outline. Ensure that any mention of these entities is consistent with the information you have about the named entity. You may introduce additional fictional entities as needed, but they must not conflict with the existing ones.
12. When referencing any named entities from the provided inputs, maintain consistency in their descriptions and roles within the story.
13. If no date is provided: Generate a complete date for the event, including the year. The date should be formatted as "year-month-day" (e.g., "2024-12-03" or "2025-06-13"). This date should be consistent with the timeline established in the <history>.
14. If a date is provided: Use the provided date.
15. The outline can include quotes from the named entities where applicable.
16. Do not repeat the information from the previous events from the <history>.
17. Refer to all named entities (the new named entities and the known named entities) by their full "name" property. DO NOT refer to the named entities using the ID.
18. Make sure that you refer to all named entities within each storyitem per full name at least once. DO NOT use pronouns to refer to a named entity from the previous story item.
19. Think about the content that is appropriate for the event summary given the genre, provided history: Think about which dimensions align with all of those, and sound like a realistic event.

Your output should be formatted as follows:
<scratchpad>[Your thoughts go here]</scratchpad>
<results>
<date>year-month-day</date>
<outline>
<storyitem>First story item</storyitem>
<storyitem>Second story item</storyitem>
<storyitem>Third story item</storyitem>
...
</outline>
</results>

IMPORTANT:
- The event must be entirely realistic, even though it is fictional. Do not include any science fiction or fantasy elements. The story should read like a plausible current event.
- Do not use any galactic events. The fictional world should be similar to our world but not about galaxies or outer space.
- Each story item must only discuss one fact or subevent. Ensure that each story item is specific, concise, and focused on a single piece of information.
- Begin your response with <results> and end it with </results>. Do not include any text outside of these tags.
- Do not exaggerate the outline. Avoid using words like "groundbreaking", "worldwide", "global". Keep the outline and the scope and influence of the event realistic.
- Do not create outlines with global or national impact unless the genre specifically requires it. Instead, focus on smaller or local developments.
- Do not focus on technological discoveries or topics like AI tools, virtual reality, augmented reality, 3D-modelling, quantum computing, etc. You may include such topics only if they are HIGHLY relevant to the genre {{GENRE}} AND the provided history of events.
- Focus on realistic, meaningful outlines with specific details and events that align with typical, realistic scenarios of the genre {{GENRE}}.

Remember:
The outline should center on a fictional but realistic event, keeping its scale aligned with the event summary and provided <history> without exaggerating its impact. Rather than overstating the event's significance, the outline should stay within the scope appropriate to the genre, provided history, and provided summary. When in doubt, focus on detailed, localized developments instead of amplifying global effects.

Ensure that the outline is coherent, follows a logical sequence, and offers a unique perspective on the given event while maintaining consistency with the provided background information.
"""


INSTRUCTIONS_V4 = """
You are an AI assistant tasked with generating an outline for a fictional event. Your goal is to create a realistic, entirely fictional event that does not overlap with real-world named entities or known fictional named entities. Follow these instructions carefully:

First, review the list of already known fictional named entities of this fictional world:

<known_entities>
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
</known_entities>
Next, review the outline of previous events that have occurred in this fictional world:

<history>
{{HISTORY_XML}}
</history>

Now, consider the following information about the new event you need to generate as a continuation of the past events:

Date: {{PROVIDED_DATE}}

Event Summary: {{EVENT_SUMMARY}}

Genre: {{GENRE}}

Follow these guidelines to generate the event outline:

1. Create an entirely fictional event based on the given genre, event summary, and history of previous events. The event must be realistic but must not reference any existing real-world or known fictional named entities.
2. Invent new named entities as needed, ensuring they don't exist in the real world or in existing works of fiction. When creating names, use unique combinations unlikely to match real named entities.
3. Construct the outline using short, concise, factual, and objective statements. Each statement must discuss only one fact or sub-event, structured sequentially in a logical temporal order when applicable.
4. Ensure all statements form a coherent outline.
5. Output each statement within a <storyitem> tag.
6. Generate exactly {{NUM_STORYITEMS}} distinct story items.
7. Ensure logical progression, with each statement following chronologically when applicable. Include a mix of main events, reactions, consequences, and contextual information.
8. Make storyitems as atomic as possible, communicating only a single piece of relevant information per item. Do not merge multiple pieces of information into one storyitem.
9. Ensure the story sounds realistic without explicitly stating it's fictional.
10. Maintain consistency with the provided <history> that discusses past events fictional events. The outline must logically follow chronological events described in the history.
11. Incorporate some or all of the provided named entities in your outline. Ensure that any mention of these entities is consistent with the information you have about the named entity. You may introduce additional fictional entities as needed, but they must not conflict with the existing ones.
12. When referencing any named entities from the provided inputs, maintain consistency in their descriptions and roles within the story.
13. If no date is provided: Generate a complete date for the event, including the year. The date should be formatted as "year-month-day" (e.g., "2024-12-03" or "2025-06-13"). This date should be consistent with the timeline established in the <history>.
14. If a date is provided: Use the provided date.
15. The outline can include quotes from the named entities where applicable.
16. Do not repeat the information from the previous events from the <history>.
17. Refer to all named entities (the new named entities and the known named entities) by their full "name" property. DO NOT refer to the named entities using the ID.
18. Make sure that you refer to all named entities within each storyitem per full name at least once. DO NOT use pronouns to refer to a named entity from the previous story item.
19. Think about the content that is appropriate for the event summary given the genre, provided history: Think about which dimensions align with all of those, and sound like a realistic event.

Your output should be formatted as follows:
<scratchpad>[Your thoughts go here]</scratchpad>
<results>
<date>year-month-day</date>
<outline>
<storyitem>First story item</storyitem>
<storyitem>Second story item</storyitem>
<storyitem>Third story item</storyitem>
...
</outline>
</results>

IMPORTANT:
- The event must be entirely realistic, even though it is fictional. Do not include any science fiction or fantasy elements. The story should read like a plausible current event.
- Do not use any galactic events. The fictional world should be similar to our world but not about galaxies or outer space.
- Each story item must only discuss one fact or subevent. Ensure that each story item is specific, concise, and focused on a single piece of information.
- Begin your response with <results> and end it with </results>. Do not include any text outside of these tags.

Remember:
The outline should center on a fictional but realistic event, keeping its scale aligned with the event summary and provided <history> without exaggerating its impact. Rather than overstating the event's significance, the outline should stay within the scope appropriate to the genre, provided history, and provided summary. When in doubt, focus on detailed, localized developments instead of amplifying global effects.

Ensure that the outline is coherent, follows a logical sequence, and offers a unique perspective on the given event while maintaining consistency with the provided background information.
"""


INSTRUCTIONS_V3 = """
You are an AI assistant tasked with generating an outline for a fictional event and a corresponding date. Your goal is to create a realistic, entirely fictional event that does not overlap with real-world entities or known fictional entities. Follow these instructions carefully:

First, review the list of already known fictional named entities of this fictional world:

<known_entities>
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
</known_entities>

Next, review the outline of previous events that have occurred in this fictional world.

<history>
{{HISTORY_XML}}
</history>

Now, consider the following information about the new event you need to generate as a continuation of the past events:

Date:
{{PROVIDED_DATE}}

Event Summary: 
{{EVENT_SUMMARY}}

Genre: 
{{GENRE}}

Keywords: 
{{KEYWORDS}}

Follow these guidelines to generate the event outline:

1. Create an entirely fictional event based on the given genre, event summary, and history of previous events. The event must be realistic but must not reference any existing real-world or known fictional named entities.
2. Invent new entities as needed, ensuring they don't exist in the real world or in existing works of fiction. When creating names, use unique combinations unlikely to match real entities.
3. Construct the outline using short, concise, factual, and objective statements. Each statement must discuss only one fact or sub-event, structured sequentially in a logical temporal order when applicable.
4. Ensure all statements form a coherent outline.
5. Output each statement within a <storyitem> tag.
6. Generate exactly {{NUM_STORYITEMS}} distinct story items.
7. Use the provided keywords as inspiration for characters, settings, locations, subevents, etc., without necessarily including them verbatim in your outline.
8. Ensure logical progression, with each statement following chronologically when applicable. Include a mix of main events, reactions, consequences, and contextual information.
9. Make storyitems as atomic as possible, communicating only a single piece of relevant information per item. Do not merge multiple pieces of information into one storyitem.
10. Ensure the story sounds realistic without explicitly stating it's fictional.
11. Maintain consistency with the provided <history>. The outline must logically follow chronological events described in the history.
12. Incorporate some or all of the entities provided in your outline. Ensure that any mention of these entities is consistent with the information given. You may introduce additional fictional entities as needed, but they must not conflict with the existing ones.
13. When referencing locations, organizations, or other entities from the provided inputs, maintain consistency in their descriptions and roles within the story. 
14. If no date is provided:Generate a complete date for the event, including the year. The date should be formatted as "year-month-day" (e.g., "2024-12-03" or "2025-06-13"). This date should be consistent with the timeline established in the <history>.
15. If a date is provided: Use the provided date.
16. The outline can include quotes from the entities where applicable.
17. Do not repeat the information from the previous events from the <history>.
18. Refer to all named entities (the new named entities and the known named entities) by their full "name" property. DO NOT refer to the named entities using the ID.

Your output should be formatted as follows:

<results>
<date>year-month-day</date>
<outline>
<storyitem>First story item</storyitem>
<storyitem>Second story item</storyitem>
<storyitem>Third story item</storyitem>
...
</outline>
</results>

IMPORTANT:
- The event must be entirely realistic, even though it is fictional. Do not include any science fiction or fantasy elements. The story should read like a plausible current event.
- Do not use any galactic events. The fictional world should be similar to our world but not about galaxies or outer space.
- Each story item must only discuss one fact or subevent. Ensure that each story item is specific, concise, and focused on a single piece of information.
- Begin your response with <results> and end it with </results>. Do not include any text outside of these tags.

Ensure that the outline is coherent, follows a logical sequence, and offers a unique perspective on the given event while maintaining consistency with the provided background information.

"""


INSTRUCTIONS_V2 = """
You are an AI assistant tasked with generating an outline for a fictional event and a corresponding date. Your goal is to create a realistic, entirely fictional event that does not overlap with real-world entities or known fictional entities. Follow these instructions carefully:

First, review the list of already known fictional named entities of this fictional world:

<known_entities>
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
</known_entities>

Next, review the outline of previous events that have occurred in this fictional world:

<history>
{{HISTORY_XML}}
</history>

Now, consider the following information about the new event you need to generate as a continuation of the past events:

Event Summary: 
{{EVENT_SUMMARY}}

Genre: 
{{GENRE}}

Keywords: 
{{KEYWORDS}}


Follow these guidelines to generate the event outline:

1. Create an entirely fictional event based on the given genre, event summary, and history of previous events. The event must be realistic but must not reference any existing real-world or known fictional named entities.
2. Invent new entities as needed, ensuring they don't exist in the real world or in existing works of fiction. When creating names, use unique combinations unlikely to match real entities.
3. Construct the outline using short, concise, factual, and objective statements. Each statement must discuss only one fact or sub-event, structured sequentially in a logical temporal order when applicable.
4. Ensure all statements form a coherent outline.
5. Output each statement within a <storyitem> tag.
6. Generate exactly {{NUM_STORYITEMS}} distinct story items.
7. Use the provided keywords as inspiration for characters, settings, locations, subevents, etc., without necessarily including them verbatim in your outline.
8. Ensure logical progression, with each statement following chronologically when applicable. Include a mix of main events, reactions, consequences, and contextual information.
9. Make storyitems as atomic as possible, communicating only a single piece of relevant information per item. Do not merge multiple pieces of information into one storyitem.
10. Ensure the story sounds realistic without explicitly stating it's fictional.
11. Maintain consistency with the provided <history>. The outline must logically follow chronological events described in the history.
12. Incorporate some or all of the entities provided in your outline. Ensure that any mention of these entities is consistent with the information given. You may introduce additional fictional entities as needed, but they must not conflict with the existing ones.
13. When referencing locations, organizations, or other entities from the provided inputs, maintain consistency in their descriptions and roles within the story.
14. Generate a complete date for the event, including the year. The date should be formatted as "Month Day, Year" (e.g., "March 12, 2024" or "June 3, 2025"). This date should be consistent with the timeline established in the <history>.
15. The outline can include quotes from the entities where applicable.
16. Do not repeat the information from the previous events from the <history>.

Your output should be formatted as follows:

<results>
<date>Month Day, Year</date>
<outline>
<storyitem>First story item</storyitem>
<storyitem>Second story item</storyitem>
<storyitem>Third story item</storyitem>
...
</outline>
</results>

IMPORTANT:
- The event must be entirely realistic, even though it is fictional. Do not include any science fiction or fantasy elements. The story should read like a plausible current event.
- Do not use any galactic events. The fictional world should be similar to our world but not about galaxies or outer space.
- Each story item must only discuss one fact or subevent. Ensure that each story item is specific, concise, and focused on a single piece of information.
- Begin your response with <results> and end it with </results>. Do not include any text outside of these tags.

Ensure that the outline is coherent, follows a logical sequence, and offers a unique perspective on the given event while maintaining consistency with the provided background information.
"""


INSTRUCTIONS_V1 = """
You are an AI assistant tasked with generating an outline for a fictional news article based on given inputs. Your goal is to create a realistic, entirely fictional news story that does not overlap with real-world entities or known fictional entities, while maintaining consistency with provided background information.

You will be provided with the following inputs:

<known_entities>
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
</known_entities>

<history>
{{HISTORY_XML}}
</history>

<genre>{{GENRE}}</genre>
<summary>{{EVENT_SUMMARY}}</summary>
<keywords>{{KEYWORDS}}</keywords>
<num_storyitems>{{NUM_STORYITEMS}}</num_storyitems>

Follow these guidelines to generate the news article outline:

1. Create an entirely fictional story based on the given genre, event summary, and history of previous events. The story must be realistic but should not reference any existing real-world or known fictional entities.

2. Invent new entities (names, places, organizations, currencies) as needed, ensuring they don't exist in the real world or in existing works of fiction. When creating names, use unique combinations unlikely to match real entities.

3. Construct the outline using short, concise, factual, and objective statements. Each statement should discuss only one fact or sub-event, structured sequentially in a logical temporal order when applicable.

4. Ensure all statements form a coherent outline with a clear beginning, middle, and end, building upon previous ones to create a complete narrative.

5. Output each statement within a <storyitem> tag.

6. Generate exactly one outline with the number of distinct story items specified in NUM_STORYITEMS. If NUM_STORYITEMS is not provided or is less than 5, generate at least 5 distinct story items.

7. If keywords are provided, do not include them verbatim in your outline. Instead, think about associations with these keywords and how they connect with the provided summary of the event. Use these associations to guide you in creating a unique event outline. They can serve as inspiration for characters, settings, locations, subevents, etc.

8. Ensure logical progression, with each statement following chronologically when applicable. Include a mix of main events, reactions, consequences, and contextual information.

9. Make storyitems as atomic as possible, communicating only a single piece of relevant information per item. Do not merge multiple pieces of information into one storyitem.

10. Ensure the story sounds realistic without explicitly stating it's fictional.

11. Maintain consistency with the provided HISTORY. The outline must logically follow and build upon the chronological events described in the HISTORY.

12. Incorporate some or all of the entities provided in your outline. Ensure that any mention of these entities is consistent with the information given. You may introduce additional fictional entities as needed, but they must not conflict with the existing ones.

13. When referencing locations, organizations, or other entities from the provided inputs, maintain consistency in their descriptions and roles within the story.

14. Generate a complete date for the news article, including the year. The date should be formatted as "Month Day, Year" (e.g., "March 12, 2024" or "June 3, 2025"). This date should be consistent with the timeline established in the HISTORY.

15. Note that fields within the provided entities can discuss content in the following form: "{[Mention]|[ID]}". This simply means that the text should be read as if only [Mention] was written. The [Id] represents the entity ID of the mentioned entity.

Your output should be formatted as follows:

<result>
<date>Month Day, Year</date>
<outline>
<storyitem>First story item</storyitem>
<storyitem>Second story item</storyitem>
<storyitem>Third story item</storyitem>
...
</outline>
</result>

Here's an example of how your output should look:

<result>
<date>June 15, 2024</date>
<outline>
<storyitem>Zephyrian President Elara Voss unveils "Green Horizon" initiative.</storyitem>
<storyitem>Initiative aims for 100% renewable energy use by 2040.</storyitem>
<storyitem>Announcement made in capital city Aethoria.</storyitem>
<storyitem>Opposition leader Kael Nyx criticizes plan.</storyitem>
<storyitem>Nyx calls initiative "economically unfeasible".</storyitem>
<storyitem>Environmental groups organize rally in Aethoria.</storyitem>
<storyitem>Rally takes place in Central Square.</storyitem>
<storyitem>Thousands attend the celebratory gathering.</storyitem>
<storyitem>Zephyrian Dollar strengthens against Lumina's currency.</storyitem>
<storyitem>Energy Minister Lyra Solstice outlines implementation plan.</storyitem>
<storyitem>First phase focuses on solar power expansion.</storyitem>
<storyitem>Local businesses express mixed reactions.</storyitem>
<storyitem>Renewable energy sector stocks surge on Zephyrian Exchange.</storyitem>
</outline>
</result>

IMPORTANT:
- The news event must be entirely realistic, even though it is fictional. Do not include any science fiction or fantasy elements. The story should read like a plausible current event that could appear in a mainstream news publication.
- Do not use any galactic events. The fictional world should be similar to our world but not about galaxies or outer space.
- Each story item must only discuss one fact or subevent. Ensure that each story item is specific, concise, and focused on a single piece of information.
- Begin your response with <result> and end it with </result>. Do not include any text outside of these tags.

Remember to generate exactly one outline with at least the number of distinct story items specified in NUM_STORYITEMS, or a minimum of 5 if not specified. Ensure that the outline is coherent, follows a logical sequence, and offers a unique perspective on the given event summary while maintaining consistency with the provided background information.

Each of the provided summaries in the HISTORY is prepended with a date. Use these dates to inform the timeline of your story and ensure that the date you create for the news article is consistent with this timeline.
"""

INSTRUCTIONS_VBAD = """
You are an AI assistant tasked with generating an outline for a fictional news article based on given inputs. Your goal is to create a realistic, entirely fictional news story that does not overlap with real-world entities or known fictional entities, while maintaining consistency with provided background information.

You will be provided with the following inputs:

<known_entities>
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
</known_entities>

<history>
{{HISTORY_XML}}
</history>

<genre>{{GENRE}}</genre>
<summary>{{EVENT_SUMMARY}}</summary>
<keywords>{{KEYWORDS}}</keywords>
<num_storyitems>{{NUM_STORYITEMS}}</num_storyitems>

Follow these guidelines to generate the news article outline:

1. Create an entirely fictional story based on the given genre, event summary, and history of previous events. The story must be realistic but should not reference any existing real-world or known fictional entities.

2. Invent new entities (names, places, organizations, currencies) as needed, ensuring they don't exist in the real world or in existing works of fiction. When creating names, use unique combinations unlikely to match real entities.

3. Construct the outline using short, concise, factual, and objective statements. Each statement should discuss only one fact or sub-event, structured sequentially in a logical temporal order when applicable.

4. Ensure all statements form a coherent outline with a clear beginning, middle, and end, building upon previous ones to create a complete narrative.

5. Output each statement within a <story_item> tag.

6. Generate exactly one outline with the number of distinct story items specified in NUM_STORYITEMS. If NUM_STORYITEMS is not provided or is less than 5, generate at least 5 distinct story items.

7. If keywords are provided, do not include them verbatim in your outline. Instead, think about associations with these keywords and how they connect with the provided summary of the event. Use these associations to guide you in creating a unique event outline. They can serve as inspiration for characters, settings, locations, subevents, etc.

8. Ensure logical progression, with each statement following chronologically when applicable. Include a mix of main events, reactions, consequences, and contextual information.

9. Make storyitems as atomic as possible, communicating only a single piece of relevant information per item. Do not merge multiple pieces of information into one storyitem.

10. Ensure the story sounds realistic without explicitly stating it's fictional.

11. Maintain consistency with the provided HISTORY. The outline must logically follow and build upon the chronological events described in the HISTORY.

12. Incorporate some or all of the entities provided in your outline. Ensure that any mention of these entities is consistent with the information given. You may introduce additional fictional entities as needed, but they must not conflict with the existing ones.

13. When referencing locations, organizations, or other entities from the provided inputs, maintain consistency in their descriptions and roles within the story.

14. Generate a complete date for the news article, including the year. The date should be formatted as "Month Day, Year" (e.g., "March 12, 2024" or "June 3, 2025"). This date should be consistent with the timeline established in the HISTORY.

15. Note that fields within the provided entities can discuss content in the following form: "{[Mention]|[ID]}". This simply means that the text should be read as if only [Mention] was written. The [Id] represents the entity ID of the mentioned entity.

Your output should be formatted as follows:

<result>
<outline>
<story_item>First story item</story_item>
<story_item>Second story item</story_item>
<story_item>Third story item</story_item>
...
</outline>
</result>

Here's an example of how your output should look:
</result>

IMPORTANT:
- The news event must be entirely realistic, even though it is fictional. Do not include any science fiction or fantasy elements. The story should read like a plausible current event that could appear in a mainstream news publication.
- Do not use any galactic events. The fictional world should be similar to our world but not about galaxies or outer space.
- Each story item must only discuss one fact or subevent. Ensure that each story item is specific, concise, and focused on a single piece of information.
- Begin your response with <result> and end it with </result>. Do not include any text outside of these tags.

Remember to generate exactly one outline with at least the number of distinct story items specified in NUM_STORYITEMS, or a minimum of 5 if not specified. Ensure that the outline is coherent, follows a logical sequence, and offers a unique perspective on the given event summary while maintaining consistency with the provided background information.

Each of the provided summaries in the HISTORY is prepended with a date. Use these dates to inform the timeline of your story and ensure that the date you create for the news article is consistent with this timeline.
"""