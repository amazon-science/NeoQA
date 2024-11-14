from typing import List, Dict, Optional

from src.mglockne_story_line.llm.critiques.base_critique import BaseCritique
from src.mglockne_story_line.story.seeds.critiques.crazy_topic_critique import CrazyTopicCritique
from src.mglockne_story_line.llm.critiques.modules.output_format_critique import OutputFormatCritique
from src.mglockne_story_line.llm.modules.parsable_base_module import ParsableBaseModule
from src.mglockne_story_line.llm.prompting.modules.nested_parsable_output_prompt import BasicNestedXMLParser
from src.mglockne_story_line.llm.prompting.parsable_prompt import ParsablePrompt
from src.mglockne_story_line.llm.verifiers.named_unified_output_verifier import NamedUnifiedOutputVerifier
from src.mglockne_story_line.llm.wrapper.base_llm_wrapper import BaseLLMWrapper
from src.mglockne_story_line.util.story_tools import renew_outline

EXPECTED_OUTPUT_FORMAT: str = """
<scratchpad>[Your thoughts go here.]</scratchpad>
<results>
<storyitems>
<storyitem>[Insert first storyitem here]</storyitem>
<storyitem>[Insert second storyitem here]</storyitem>
<storyitem>[Continue with additional storyitems as needed]</storyitem>
</storyitems>
</results>
""".strip()


class AddSpecificDetailsToOutlineModule(ParsableBaseModule):
    """
    This module extends the initial outline by adding very specific details by introducing new story items.
    """

    def _create_critiques(self) -> List[BaseCritique]:
        return [CrazyTopicCritique('story_item', 'list')]

    def _create_formatting_critique(self, parsers: List[BasicNestedXMLParser]) -> Optional[BaseCritique]:
        return OutputFormatCritique('format-add-specifics-outline', parsers, EXPECTED_OUTPUT_FORMAT)

    def __init__(self, llm: BaseLLMWrapper, name: str, instruction_name: str, max_num_specifics_per_sent: int):
        super().__init__(
            llm,
            name,
            instruction_name,
            get_instructions(instruction_name),
        )
        self.max_num_specifics_per_sent: int = max_num_specifics_per_sent

    def _preprocess_values(self, values) -> Dict:
        values['NUM_SPECIFIC_SENTS'] = self.max_num_specifics_per_sent
        values =  renew_outline(values)
        return values

    def _get_verifiers(self) -> List[NamedUnifiedOutputVerifier]:
        return []

    def _get_parsers(self) -> List[BasicNestedXMLParser]:
        return [
            BasicNestedXMLParser('story_item', './/storyitem', is_object=False, allow_empty_list=False, result_node='storyitems', remove_node='scratchpad'),
        ]

    def get_file_name(self, prompt: ParsablePrompt, values: Dict):
        headline = values['EVENT_SUMMARY_FOR_NAME'].lower().replace(' ', '-')
        node_idx = values['CREATED_AT']
        return f'N{node_idx:02d}-{self.name}-{headline}_{self.instruction_name}.json'


INSTRUCTIONS_V4 = """
You are an AI assistant tasked with analyzing a fictional event summary and its corresponding outline to enrich it with additional specific details. Follow these instructions carefully:

1. Read the provided fictional event summary:

<event_summary>
{{EVENT_SUMMARY}}
</event_summary>

2. Review the date and outline of the event:

Date: {{DATE}}
<outline>
{{OUTLINE}}
</outline>

3. Your task is to enrich this outline with additional details. The enhanced outline must discuss the same events as before and must not extend the events that happened. It must only provide supplementary details about these events.

4. Follow these rules for enrichment:
   a. Examine each sentence in the provided outline.
   b. For each sentence, identify information that is unspecific or can be elaborated with more detail.
   c. Consider the outline to be all information that is provided to a reporter about this fictional event and only include additional specific details that could also be known to the reporter at this point in time:
      - Some events may still be ongoing and some information may not be available at this point in time.
      - Do not include information that would likely not be known at this point in time.
      - Consider the perspective of what is currently known about this fictional event when adding details.
   d. When you find something unspecific, add a new sentence with supplementary specific details:
      - Place the new sentence directly after the original sentence in the outline.
      - Ensure the new sentence does not repeat content from the previous sentence.
      - Focus solely on providing supplementary specific details in the new sentence.
      - Make the new sentence self-contained and coherent on its own.

5. Additional guidelines:
   - Do not modify the existing sentences. Only add new sentences for supplementary details.
   - Ensure added sentences focus exclusively on new, specific information without repeating existing content.
   - Maintain consistency with the original outline in all additional specifics.
   - Do not introduce new subevents. Only provide more details about the events already mentioned.

6. Present your enriched outline in the following format:
   - Make sure that the sentences with the additional specific details are listed as separate <storyitem> and placed at the correct position within the outline.
   - Treat each new sentence you have created as a separate <storyitem>.
   - Each sentence provided to you in the <outline> forms one <storyitem> and must not be changed.
   - Each new sentence you have written that provides additional specific details forms one <storyitem> and must be listed separately.

Use this structure:
<results>
<storyitems>
<storyitem>[Insert first storyitem here]</storyitem>
<storyitem>[Insert second storyitem here]</storyitem>
<storyitem>[Continue with additional storyitems as needed]</storyitem>
</storyitems>
</results>

Maintain the chronological order and logical flow of the original outline while adding your supplementary details. Each <storyitem> should contain one sentence from the original outline.
"""



INSTRUCTIONS_V5 = """
You are an AI assistant tasked with analyzing a fictional event summary and its corresponding outline to enrich it with additional NEW specific details. Follow these instructions carefully:

1. Read the provided fictional event summary:

<event_summary>
{{EVENT_SUMMARY}}
</event_summary>

2. These are the fictional known entities:
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

3. Review the outline of previous events that have occurred in this fictional world:

<history>
{{HISTORY_XML}}
</history>

4. Review the date and outline of the event:

Date: {{DATE}}
<outline>
{{OUTLINE}}
</outline>

5. Your task is to enrich this outline with additional details. The enhanced outline must discuss the same events as before and must not extend the events that happened in the outline. It must only provide supplementary details about these events in the outline.

6. Follow these rules for enrichment:
   a. Examine each sentence in the provided outline.
   b. For each sentence, identify information that is unspecific or can be elaborated with more detail.
   c. Consider the outline to be all information that is provided to a reporter about this fictional event and only include additional specific details that could also be known to the reporter at this point in time:
      - Some events may still be ongoing and some information may not be available at this point in time.
      - Do not include information that would likely not be known at this point in time.
      - Consider the perspective of what is currently known about this fictional event when adding details.
   d. When you find something unspecific, add a new sentence with supplementary specific details:
      - Place the new sentence directly after the original sentence in the outline.
      - Ensure the new sentence does not repeat content from the previous sentence.
      - Focus solely on providing supplementary specific details in the new sentence.
      - Make the new sentence self-contained and coherent on its own.
   e. For each original sentence generate up to {{NUM_SPECIFIC_SENTS}} novel sentences that introduce supplementary details.

7. Additional guidelines:
   - Do not modify the existing sentences. Only add new sentences for supplementary details.
   - Ensure added sentences focus exclusively on new, specific information without repeating existing content.
   - Maintain consistency with the original outline in all additional specifics.
   - Do not introduce new subevents. Only provide more details about the events already mentioned.
   - Make sure the additional details provided are new and do not reiterate details known from the fictional history or the list of fictional known entities.
   - Make sure that the new details are not contradictory to  the history (<history>) and known entities (<known_entities>).

8. Present your enriched outline in the following format:
   - Make sure that the sentences with the additional specific details are listed as separate <storyitem> and placed at the correct position within the outline.
   - Treat each new sentence you have created as a separate <storyitem>.
   - Each sentence provided to you in the outline forms one <storyitem> and must not be changed.
   - Each new sentence you have written that provides additional specific details forms one <storyitem> and must be listed separately.

Use this structure:
<results>
<storyitems>
<storyitem>[Insert first storyitem here]</storyitem>
<storyitem>[Insert second storyitem here]</storyitem>
<storyitem>[Continue with additional storyitems as needed]</storyitem>
</storyitems>
</results>

Maintain the chronological order and logical flow of the original outline while adding your supplementary details. Each <storyitem> should contain one sentence from the original outline or one new sentence with additional specific details.
"""




INSTRUCTIONS_V6 = """
You are an AI assistant tasked with analyzing a fictional event summary and its corresponding outline to enrich it with additional NEW specific details. Follow these instructions carefully:

1. Read the provided fictional event summary of the genre {{GENRE}}:

<event_summary>
{{EVENT_SUMMARY}}
</event_summary>

2. These are the fictional known entities:
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

3. Review the outline of previous events that have occurred in this fictional world:

<history>
{{HISTORY_XML}}
</history>

4. Review the date and outline of the event:

Date: {{DATE}}
<outline>
{{OUTLINE}}
</outline>

5. Your task is to enrich this outline with additional details. The enhanced outline must discuss the same events as before and must not extend the events that happened in the outline. It must only provide supplementary details about these events in the outline.

6. Follow these rules for enrichment:
   a. Examine each sentence in the provided outline.
   b. For each sentence, identify information that is unspecific or can be elaborated with more detail.
   c. Consider the outline to be all information that is provided to a reporter about this fictional event and only include additional specific details that could also be known to the reporter at this point in time:
      - Some events may still be ongoing and some information may not be available at this point in time.
      - Do not include information that would likely not be known at this point in time.
      - Consider the perspective of what is currently known about this fictional event when adding details.
   d. When you find something unspecific, add a new sentence with supplementary specific details:
      - Place the new sentence directly after the original sentence in the outline.
      - Ensure the new sentence does not repeat content from the previous sentence.
      - Focus solely on providing supplementary specific details in the new sentence.
      - Make the new sentence self-contained and coherent on its own (do not refer to previously mentioned named entities by pronoun. Instead, directly refer to them via the name).
   e. For each original sentence generate up to {{NUM_SPECIFIC_SENTS}} novel sentences that introduce supplementary details.

7. Additional guidelines:
   - Do not modify the existing sentences. Only add new sentences for supplementary details.
   - Ensure added sentences focus exclusively on new, specific information without repeating existing content.
   - Maintain consistency with the original outline in all additional specifics.
   - Do not introduce new subevents. Only provide more details about the events already mentioned.
   - Make sure the additional details provided are new and do not reiterate details known from the fictional history or the list of fictional known entities.
   - Make sure that the new details are not contradictory to the history (<history>) and known entities (<known_entities>).

8. Present your enriched outline in the following format:
   - Make sure that the sentences with the additional specific details are listed as separate <storyitem> and placed at the correct position within the outline.
   - Treat each new sentence you have created as a separate <storyitem>.
   - Each sentence provided to you in the outline forms one <storyitem> and must not be changed.
   - Each new sentence you have written that provides additional specific details forms one <storyitem> and must be listed separately.

Important:
Before you start writing the new sentences with specific details, think about various dimensions that could be extended that align well with the genre, history, provided event summary and existing outline. Think about specific directions that could be of interest within the current genre ({{GENRE}}) and brainstorm how you could deepen the outline with new specific details on these interesting dimensions. Carefully decide when it is reasonable to provide technical details, when it make more sense to provide quotes, visions, etc., when to provide background information. Think about information that are of interest to a reader of a newspaper with the genre {{GENRE}}. Be in particular careful before introducing technological details and first examine if these details are appropriate for the genre or not.
Double-check that each detail is compatible with all the existing information you are provided with.

Use this structure:
<scratchpad>[Your thoughts go here.]</scratchpad>
<results>
<storyitems>
<storyitem>[Insert first storyitem here]</storyitem>
<storyitem>[Insert second storyitem here]</storyitem>
<storyitem>[Continue with additional storyitems as needed]</storyitem>
</storyitems>
</results>

Maintain the chronological order and logical flow of the original outline while adding your supplementary details. Each <storyitem> should contain one sentence from the original outline or one new sentence with additional specific details.
"""

INSTRUCTIONS_V7 = """
You are an AI assistant tasked with analyzing a fictional event summary and its corresponding outline to enrich it with additional NEW specific details. Follow these instructions carefully:

1. Read the provided fictional event summary of the genre {{GENRE}}:

<event_summary>
{{EVENT_SUMMARY}}
</event_summary>

2. These are the fictional known entities:
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

3. Review the outline of previous events that have occurred in this fictional world:

<history>
{{HISTORY_XML}}
</history>

4. Review the date and outline of the event:

Date: {{DATE}}
<outline>
{{OUTLINE}}
</outline>

5. Your task is to enrich this outline with additional details. The enhanced outline must discuss the same events as before and must not extend the events that happened in the outline. It must only provide supplementary details about these events in the outline.

6. Follow these rules for enrichment:
   a. Examine each sentence in the provided outline.
   b. For each sentence, identify information that is unspecific or can be elaborated with more detail.
   c. Consider the outline to be all information that is provided to a reporter about this fictional event and only include additional specific details that could also be known to the reporter at this point in time:
      - Some events may still be ongoing and some information may not be available at this point in time.
      - Do not include information that would likely not be known at this point in time.
      - Consider the perspective of what is currently known about this fictional event when adding details.
   d. When you find something unspecific, add a new sentence with supplementary specific details:
      - Place the new sentence directly after the original sentence in the outline.
      - Ensure the new sentence does not repeat content from the previous sentence.
      - Focus solely on providing supplementary specific details in the new sentence.
      - Make the new sentence self-contained and coherent on its own (do not refer to previously mentioned named entities by pronoun. Instead, directly refer to them via the name).
   e. For each original sentence generate up to {{NUM_SPECIFIC_SENTS}} novel sentences that introduce supplementary details.

7. Additional guidelines:
   - Do not modify the existing sentences. Only add new sentences for supplementary details.
   - Ensure added sentences focus exclusively on new, specific information without repeating existing content.
   - Maintain consistency with the original outline in all additional specifics.
   - Do not introduce new subevents. Only provide more details about the events already mentioned.
   - Make sure the additional details provided are new and do not reiterate details known from the fictional history or the list of fictional known entities.
   - Make sure that the new details are not contradictory to the history (<history>) and known entities (<known_entities>).
   - Do not exaggerate the outline. Avoid using words like "groundbreaking", "worldwide", "global". Keep the outline and the scope and influence of the event realistic.
   - Do not create outlines with global or national impact unless the genre specifically requires it. Instead, focus on smaller or local developments.
   - Do not focus on technological discoveries or topics like AI tools, virtual reality, augmented reality, 3D-modelling, quantum computing, etc. You may include such topics only if they are HIGHLY relevant to the genre {{GENRE}} AND the provided history of events.
   - Focus on realistic, meaningful outlines with specific details and events that align with typical, realistic scenarios of the genre {{GENRE}}.

8. Present your enriched outline in the following format:
   - Make sure that the sentences with the additional specific details are listed as separate <storyitem> and placed at the correct position within the outline.
   - Treat each new sentence you have created as a separate <storyitem>.
   - Each sentence provided to you in the outline forms one <storyitem> and must not be changed.
   - Each new sentence you have written that provides additional specific details forms one <storyitem> and must be listed separately.

Important:
Before you start writing the new sentences with specific details, think about various dimensions that could be extended that align well with the genre, history, provided event summary and existing outline. Think about specific directions that could be of interest within the current genre ({{GENRE}}) and brainstorm how you could deepen the outline with new specific details on these interesting dimensions. Carefully decide when it is reasonable to provide technical details, when it make more sense to provide quotes, visions, etc., when to provide background information. Think about information that are of interest to a reader of a newspaper with the genre {{GENRE}}. Be in particular careful before introducing technological details and first examine if these details are appropriate for the genre or not.
Double-check that each detail is compatible with all the existing information you are provided with.

Use this structure:
<scratchpad>[Your thoughts go here.]</scratchpad>
<results>
<storyitems>
<storyitem>[Insert first storyitem here]</storyitem>
<storyitem>[Insert second storyitem here]</storyitem>
<storyitem>[Continue with additional storyitems as needed]</storyitem>
</storyitems>
</results>

Maintain the chronological order and logical flow of the original outline while adding your supplementary details. Each <storyitem> should contain one sentence from the original outline or one new sentence with additional specific details.
"""



def get_instructions(version: str) -> str:

    if version == 'v4':
        out: str = INSTRUCTIONS_V4
    elif version == 'v5':
        out: str = INSTRUCTIONS_V5
    elif version == 'v6':
        out: str = INSTRUCTIONS_V6
    elif version == 'v7':
        out: str = INSTRUCTIONS_V7
    else:
        raise ValueError(version)
    return out.strip()
