from typing import Dict, Optional, List, Set

from data_gen.llm.critiques.base_critique import BaseCritique
from data_gen.llm.critiques.critique_result import CritiqueResult
from data_gen.llm.critiques.output_format_critique import OutputFormatCritique
from data_gen.llm.modules.parsable_base_module import ParsableBaseModule
from data_gen.llm.prompting.modules.nested_parsable_output_prompt import BasicNestedXMLParser
from data_gen.llm.prompting.parsable_prompt import ParsablePrompt
from data_gen.llm.wrapper.base_llm_wrapper import BaseLLMWrapper


class TimeSpanQuestionCritique(BaseCritique):
    """
    Make sure that a name is not too long (which would likely be due to en error in parsing)
    """
    def process(self, values: Dict) -> CritiqueResult:

        if 'additional_sentence_ids' not in values:
            return CritiqueResult.correct(self.name)

        selected_events: List[Dict] = values['SELECTED_EVENTS']
        all_item_ids: Set[str] = {
            item['id']
            for event in selected_events
            for item in event['outline']
        }

        values[self.field]['additional_sentence_ids'] = values[self.field]['additional_sentence_ids'].replace('[', '').replace(']', '').strip()

        newly_selected_ids: Set[str] = {
            item_id.strip() for item_id in values[self.field]['additional_sentence_ids'].split(',')
            if len(item_id.strip()) > 0
        }

        incorrect_ids: List[str] = sorted(list(newly_selected_ids - all_item_ids))
        if len(incorrect_ids) > 0:
            error_message: str = f"Make sure that all additional sentences from the <additional_sentence_ids> are from the selected events. The following sentences are NOT from the selected events: {incorrect_ids}."
            return CritiqueResult(self.name, False,
                                  [{'item_id': item_id} for item_id in incorrect_ids],
                                  error_message
                                  )
        else:
            return CritiqueResult.correct(self.name)

    def __init__(self, field='current_qa_pair'):
        super().__init__('time-span-question-critique')
        self.field: str = field


EXPECTED_OUTPUT_FORMAT = """
<scratchpad>[Outline your reasoning including the derived absolute points in time here.]</scratchpad>
<results>
<qa>
<question>[Your generated question about the time span]</question>
<answer>[The precise and concise answer to the question]</answer>
<additional_sentence_ids>[List of additional sentence IDs required to answer the question, if applicable]</additional_sentence_ids>
<additional_sentence_explanation>[Explain the unique information of each additional sentence that is required to answer the question and justify why it is needed, if applicable]</additional_sentence_explanation>
</qa>
</results>
"""


class MultiEventTimeSpanQuestionModule(ParsableBaseModule):
    def _create_formatting_critique(self, parsers: List[BasicNestedXMLParser]) -> BaseCritique:
        return OutputFormatCritique('format-entity-update', parsers, EXPECTED_OUTPUT_FORMAT)

    def _postprocess_values(self, values: Dict) -> Optional[Dict]:
        # qa: Dict = values['current_qa_pair']
        # values[QuestionGenerator.VAL_PAIRS] = [{
        #         MultiEventTimeSpanQuestionGenerator.VAL_QUESTION: qa['question'],
        #         MultiEventTimeSpanQuestionGenerator.VAL_ANSWER: qa['answer'],
        #         'ADDITIONAL_SENTENCE_IDS': [_id.strip() for _id in qa.get('additional_sentence_ids', '').split(',') if len(_id.strip()) > 4],
        #         'ADDITIONAL_SENTENCE_IDS_EXPLANATION': qa.get('additional_sentence_explanation', ''),
        #         'scratchpad': values['scratchpad']
        #     }
        # ]
        # values[MultiEventTimeSpanQuestionGenerator.VAL_HOPS] = len(values['EVIDENCE_CURRENT_SELECTIONS'])
        return super()._postprocess_values(values)

    def __init__(self, llm: BaseLLMWrapper, name: str, instruction_name: str):
        super().__init__(
            llm,
            name,
            instruction_name,
            get_instructions(instruction_name),
        )

    def _preprocess_values(self, values) -> Dict:
        return values

    def _create_critiques(self) -> List[BaseCritique]:
        return [
            TimeSpanQuestionCritique('current_qa_pair1')
        ]

    def _get_parsers(self) -> List[BasicNestedXMLParser]:
        return [
            BasicNestedXMLParser('current_qa_pair1', './/qa', is_object=True, allow_empty_list=False, result_node='results', to_single=True, require_fields=[
                'question', 'answer'
            ]),
            BasicNestedXMLParser('scratchpad', './/scratchpad', is_object=False, shallow_text_extraction=True, result_node='scratchpad')

        ]

    def get_file_name(self, prompt: ParsablePrompt, values: Dict):
        node_idx: int = values['CREATED_AT']
        return f'N{node_idx:02d}-{self.name}_{self.instruction_name}.json'


def get_instructions(version: str) -> str:

    if version == 'v2':
        out: str = INSTRUCTIONS_V2
    elif version == 'v3':
        out: str = INSTRUCTIONS_V3
    elif version == 'v4':
        out: str = INSTRUCTIONS_V4
    else:
        raise ValueError(version)
    return out.strip()


INSTRUCTIONS_V4 = """
You are an AI assistant tasked with generating a complex question-answer pair based on a fictional event outline. Your goal is to create a question that asks about an absolute time span (duration) that can be computed using specific selected sentences from the outline.

First, review the complete storyline outline:

<complete_outline>
{{STORYLINE_OUTLINE_TO_DATE}}
</complete_outline>

Now, focus on the selected sentences:

<selected_sentences>
{{SELECTED_SENTENCES}}
</selected_sentences>

To create a time-span question based on the selected sentences, follow these steps:

1. Identify the absolute date or time within each of the selected sentences if possible. If a sentence doesn't provide additional time information, use the event date as time information. Remember that the dates of individual sub-events within each event may differ from the event date. To compute the specific points in time, check if the selected sentences specify any of the following:
   - Relative time information (e.g., "six weeks ago", "in five days", "after two hours") based on which you can compute a specific point in time
   - Absolute time information (e.g., "10:00 am", "March 22nd")
   - You can always assume that the date listed for each event is known. The event date is always the latest possible date based on everything that has happened within the event. 
   - If the specific points in time cannot be asserted with certainty but only estimated based on some likelihood, specify assumptions under which you can derive absolute points in time
   - If the sentences describe durations, list the respective start and end dates/times together with the assumptions

2. Think about the different options of absolute points of time and which time span between them would be most challenging to compute, ensuring that all selected sentences are required to compute the duration.

3. Draft a specific question that asks for the time duration. This question can only be solved if one derives the absolute points in time from each of the selected sentences. The question must always ask about the duration between two points in time. Prefer time durations that differ from the absolute durations of the respective event (if multiple options of different possible ways to compute durations exist).

4. Formulate a precise and correct answer to the question, which must be an absolute duration. Only use the information from the selected sentences and make the question very specific to avoid ambiguities. In the scratchpad, include a derivation of the answer using the absolute dates you estimated before.

5. Ensure the validity of the questions:
   - Ensure that the question can ONLY be answered when ALL of the selected sentences are present.
   - Make sure that ALL of the selected sentences are needed to answer the question.
   - Make sure that no other information from the <complete_outline> is sufficient to answer the question and that no other sentence from the <complete_outline> can replace any of the selected sentence in answering the question.
   - Adjust the question accordingly to fulfill these criteria by making it more specific.

6. Avoid absolute dates or times in your question if possible:
   - If you needed to make an assumption about when something happened, try to explain it relative to other existing events or information from the <complete_outline>. Try to replace explicitly mentioned dates by anchoring them into some content of the <complete_outline> instead. If necessary, add the additional required sentence ID to your result and explain the unique information of this sentence that is necessary.
   - Make sure that temporal reasoning is still required in the revised question. Double-check if the temporal information is still essential to answer the question after resolving the absolute dates. Think about different options (like start and end dates) to make sure that one must apply temporal reasoning to answer the question.

7. If you must integrate additional information beyond what is specified within the selected sentences:
   - Identify the unique information you must add to the question within the provided <complete_outline> and select the sentence communicating this unique information
   - Explain what kind of unique information from this sentence is needed and why
   - List the sentence ID of the newly selected sentence in your result
   - Rewrite your question accordingly and ensure that all points listed in step 5 are valid when adding the newly selected sentence

Provide your reasoning in the following format:
<scratchpad>
(Repeat for all sentence IDs)
[Sentence ID]:
- [Describe the time information from this sentence]
- [Identify the event date]
Assumptions:
- [Make your assumptions explicit]
Absolute dates:
- [List all relevant absolute dates from this sentence. Justify how they relate to the event date or other date information.]


Additional sentences:
[Think about additional sentence IDs to add and explain your decision and what information from the sentence you require. List any new absolute dates based on this information.]

Question Idea:
[Outline how to create a challenging time-span question based on the absolute dates and selected information]
- [For each selected sentence, specifically elaborate the unique information from this sentence that is required to answer the question. Think about how to frame the question without explicitly stating this unique information.]

[Answer derivation]:
Compute the answer using the absolute dates from above.

<scratchpad>

Output your results in the following format:
<scratchpad>[Outline your reasoning including the derived absolute points in time here.]</scratchpad>
<results>
<qa>
<question>[Your generated question about the time span]</question>
<answer>[The precise and concise answer to the question]</answer>
<additional_sentence_ids>[List of additional sentence IDs required to answer the question, if applicable]</additional_sentence_ids>
<additional_sentence_explanation>[Explain the unique information of each additional sentence that is required to answer the question and justify why it is needed, if applicable]</additional_sentence_explanation>
</qa>
</results>

Remember to make your question as specific as possible, ensuring that it can only be answered using the information from the selected sentences (and any additional sentences you may need to include). If you need to make assumptions, state them clearly in the question. Always provide a precise and concise answer to the question you generate.

Important reminders:
- While each event provides a unique date, which can be helpful to identify the question, the provided date does not necessarily apply to all information listed in the event outline (or the selected sentences extracted from the event outline). The event date is always the latest possible date based on everything that has happened within the event. Think carefully about how the event date applies to the selected sentences before you start drafting your question. Some events may have happened in the past even though they are not described in the past tense. Use your common sense and the sequence of sentences within the event. If you are reasonably uncertain, make your assumption explicit and include it in your question.
- Ensure that the question can ONLY be answered when ALL of the selected sentences are present, and that ALL of the selected sentences are needed to answer the question.
- Make sure that no other information from the <complete_outline> is sufficient to infer the correct answer.
- If you need to include additional sentences, clearly explain why they are necessary and what unique information they provide.
- In your question clearly indicate if some point in time happens in the future as such (for example when including the planned end date of an ongoing or planned event).
- In your question, DO NOT include the required temporal information. The temporal information must be inferred from the content of the selected sentences.
- DO NOT create questions about time-spans that mix units that cannot be compared in a meaningful way (such as minutes and days, days and years).
- If you make assumptions, make sure they are plausible.
- If you rely on the event date, carefully assess if the whether the information likely occurred before or after the event date.
- State your assumptions that are required to answer the question clearly in the question.
- Make sure that the question cannot be answered without considering unique content from ALL selected evidence sentences (from <selected_sentences> and <additional_sentence_ids>)
- Explicitly compute and list all dates, including start and end dates, based on your assumptions before you draft your question.
- The answer should only consist of the correct time span and should not be a complete sentence.
- Ensure that you DO NOT explicitly refer to absolute dates or relative time spans (from the selected sentences) in the question. It is important that answering the question requires extracting this information from these sentences.
"""


INSTRUCTIONS_V3 = """
You are an AI assistant tasked with generating a complex question-answer pair based on a fictional event outline. Your goal is to create a question that asks about an absolute time span (duration) that can be computed using specific selected sentences from the outline.

First, review the complete storyline outline:

<complete_outline>
{{STORYLINE_OUTLINE_TO_DATE}}
</complete_outline>

Now, focus on the selected sentences:

<selected_sentences>
{{SELECTED_SENTENCES}}
</selected_sentences>

To create a time-span question based on the selected sentences, follow these steps:

1. Identify the absolute date or time within each of the selected sentences if possible. If a sentence doesn't provide additional time information, use the event date as time information. To compute the specific points in time, check if the selected sentences specify:
   - Relative time information (e.g., "six weeks ago", "in five days", "after two hours") based on which you can compute a specific point in time
   - Absolute time information (e.g., "10:00 am", "March 22nd")
   - You can always assume that the date listed for each event is known
   - If the specific points in time cannot be asserted with certainty but only estimated based on some likelihood, specify assumptions under which you can derive absolute points in time
   - If the sentences describe durations, list the respective start and end dates/times together with the assumptions

2. Think about the different options of absolute points of time and which time span between them would be most challenging to compute, ensuring that all selected sentences are required to compute the duration.

3. Draft a specific question that asks for the time duration. This question can only be solved if one derives the absolute points in time from each of the selected sentences. The question must always ask about the duration between two points in time. Prefer time durations that differ from the absolute durations of the respective event (if multiple options of different possible ways to compute durations exist).

4. Formulate a precise and correct answer to the question, which must be an absolute duration. Only use the information from the selected sentences and make the question very specific to avoid ambiguities.

5. Ensure the validity of the questions:
   - Ensure that the question can ONLY be answered when ALL of the selected sentences are present
   - Make sure that ALL of the selected sentences are needed to answer the question
   - Make sure that no other information from the <complete_outline> is sufficient to infer the correct answer
   - Adjust the question accordingly to fulfill these criteria by making it more specific

6. Avoid absolute dates or times in your question if possible:
   - If you needed to make an assumption about when something happened, try to explain it relative to other existing events or information from the <complete_outline>. Try to replace explicitly mentioned dates by anchoring them into some content of the <complete_outline> instead. If necessary, add the additional required sentence ID to your result and explain the unique information of this sentence that is necessary.
   - Make sure that temporal reasoning is still required in the revised question. Double-check if the temporal information is still essential to answer the question after resolving the absolute dates. Think about different options (like start and end dates) to make sure that one must apply temporal reasoning to answer the question.

7. If you must integrate additional information beyond what is specified within the selected sentences:
   - Identify the unique information you must add to the question within the provided <complete_outline> and select the sentence communicating this unique information
   - Explain what kind of unique information from this sentence is needed and why
   - List the sentence ID of the newly selected sentence in your result
   - Rewrite your question accordingly and ensure that all points listed in step 5 are valid when adding the newly selected sentence

Output your results in the following format:
<scratchpad>[Outline your reasoning including the derived absolute points in time here.]</scratchpad>
<results>
<qa>
<question>[Your generated question about the time span]</question>
<answer>[The precise and concise answer to the question]</answer>
<additional_sentence_ids>[List of additional sentence IDs required to answer the question, if applicable]</additional_sentence_ids>
<additional_sentence_explanation>[Explain the unique information of each additional sentence that is required to answer the question and justify why it is needed, if applicable]</additional_sentence_explanation>
</qa>
</results>

Remember to make your question as specific as possible, ensuring that it can only be answered using the information from the selected sentences (and any additional sentences you may need to include). If you need to make assumptions, state them clearly in the question. Always provide a precise and concise answer to the question you generate.

Important reminders:
- While each event provides a unique date, which can be helpful to identify the question, the provided date does not necessarily apply to all information listed in the event outline (or the selected sentences extracted from the event outline). The event date is always the latest possible date based on everything that has happened within the event. Think carefully about how the event date applies to the selected sentences before you start drafting your question. If you are reasonably uncertain, make your assumption explicit and include it in your question.
- Ensure that the question can ONLY be answered when ALL of the selected sentences are present, and that ALL of the selected sentences are needed to answer the question.
- Make sure that no other information from the <complete_outline> is sufficient to infer the correct answer.
- If you need to include additional sentences, clearly explain why they are necessary and what unique information they provide.
- In your question clearly indicate if some point in time happens in the future as such (for example when including the planned end date of an ongoing or planned event).
- In your question, DO NOT include the required temporal information. The temporal information must be inferred from the content of the selected sentences.
"""


INSTRUCTIONS_V2 = """
You are an AI assistant tasked with generating a complex question-answer pair based on a fictional event outline. Your goal is to create a question that asks about a time span that can be computed using specific selected sentences from the outline.

First, carefully read the following complete outline of the fictional event:

<complete_outline>
{{STORYLINE_OUTLINE_TO_DATE}}
</complete_outline>

Now, focus on these selected sentences:

<selected_sentences>
{{SELECTED_SENTENCES}}
</selected_sentences>

These sentences were selected for the following reason:

<explanation>
{{SELECTION_EXPLANATION}}
</explanation>

To generate the question-answer pair, follow these steps:

1. Locate the selected sentences within the overall context of the fictional outline.
2. Analyze the information provided in the selected sentences, paying special attention to dates and events.
3. Identify the specific time span that can be computed based on the selected sentences.
4. Formulate a question that requires information from all selected sentences to be answered accurately.
5. Ensure that the question is as specific as possible to avoid ambiguities. Avoid asking directly for a unit (such as months, days, hours, etc.)
6. Verify that information from other sentences in the outline is not sufficient to replace any of the selected sentences when answering the question.
7. If you find that other sentences could potentially replace the selected ones, try to make the question more specific to align it with the exact novel information introduced in the selected sentences.
8. If it's impossible to avoid this problem, note the conflicting sentence IDs.
9. Compose a concise and precise answer to the question. The answer must be as short as possible.

Use the following format for your output:

<scratchpad>
[Use this space to think through the process, analyze the sentences, and formulate your question and answer.]
</scratchpad>

<results>
<qa>
<question>[Your generated question about the time span]</question>
<answer>[The precise and concise answer to the question]</answer>
<conflict-ids>[If applicable, list the IDs of sentences that could potentially replace the selected ones]</conflict-ids>
</qa>
</results>

In your scratchpad, you may:
- Break down the information from the selected sentences
- Identify key dates and events
- Brainstorm potential questions
- Analyze potential conflicts with other sentences in the outline
- Refine your question to ensure specificity

Remember:
- Be as specific as possible when drafting your question to avoid ambiguities.
- Make sure that both sentences are required to answer the question. DO NOT include the relevant time information from the sentences into the question. Make sure that the relevant time information from the selected sentences is only known when it is inferred from the selected sentences!
- Ensure that the time span can only be computed based on the information from all of the selected sentences.
- Double-check that information from other sentences is not sufficient to replace any of the selected sentences when answering the question.
- If you find it impossible to avoid conflicts with other sentences, make sure to list their IDs in the <conflict-ids> tag.

Your final question should be clear, unambiguous, and require information from all selected sentences to be answered accurately.
"""

# A bit less super-specific
INSTRUCTIONS_V1 = """
You are an AI assistant tasked with generating a complex question-answer pair based on a fictional event outline. Your goal is to create a question that asks about a time span that can be computed using specific selected sentences from the outline.

First, carefully read the following complete outline of the fictional event:

<complete_outline>
{{STORYLINE_OUTLINE_TO_DATE}}
</complete_outline>

Now, focus on these selected sentences:

<selected_sentences>
{{SELECTED_SENTENCES}}
</selected_sentences>

These sentences were selected for the following reason:

<explanation>
{{SELECTION_EXPLANATION}}
</explanation>

To generate the question-answer pair, follow these steps:

1. Locate the selected sentences within the overall context of the fictional outline.
2. Analyze the information provided in the selected sentences, paying special attention to dates and events.
3. Identify the specific time span that can be computed based on the selected sentences.
4. Formulate a question that requires information from all selected sentences to be answered accurately.
5. Ensure that the question is as specific as possible to avoid ambiguities. Avoid asking directly for a unit (such as months, days, hours, etc.)
6. Verify that information from other sentences in the outline is not sufficient to replace any of the selected sentences when answering the question.
7. If you find that other sentences could potentially replace the selected ones, try to make the question more specific to align it with the exact novel information introduced in the selected sentences.
8. If it's impossible to avoid this problem, note the conflicting sentence IDs.
9. Compose a concise and precise answer to the question. The answer must be as short as possible.

Use the following format for your output:

<scratchpad>
[Use this space to think through the process, analyze the sentences, and formulate your question and answer.]
</scratchpad>

<results>
<qa>
<question>[Your generated question about the time span]</question>
<answer>[The precise and concise answer to the question]</answer>
<conflict-ids>[If applicable, list the IDs of sentences that could potentially replace the selected ones]</conflict-ids>
</qa>
</results>

In your scratchpad, you may:
- Break down the information from the selected sentences
- Identify key dates and events
- Brainstorm potential questions
- Analyze potential conflicts with other sentences in the outline
- Refine your question to ensure specificity

Remember:
- Be as specific as possible when drafting your question to avoid ambiguities.
- Ensure that the time span can only be computed based on the information from all of the selected sentences.
- Double-check that information from other sentences is not sufficient to replace any of the selected sentences when answering the question.
- If you find it impossible to avoid conflicts with other sentences, make sure to list their IDs in the <conflict-ids> tag.

Your final question should be clear, unambiguous, and require information from all selected sentences to be answered accurately.
"""
