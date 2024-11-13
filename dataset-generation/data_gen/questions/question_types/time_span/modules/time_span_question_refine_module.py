from typing import Dict, Optional, List

from data_gen.llm.critiques.base_critique import BaseCritique
from data_gen.llm.critiques.output_format_critique import OutputFormatCritique
from data_gen.llm.modules.parsable_base_module import ParsableBaseModule
from data_gen.llm.prompting.modules.nested_parsable_output_prompt import BasicNestedXMLParser
from data_gen.llm.prompting.parsable_prompt import ParsablePrompt
from data_gen.llm.wrapper.base_llm_wrapper import BaseLLMWrapper
from data_gen.questions.question_generator import QuestionGenerator
from data_gen.questions.question_types.time_span.modules.time_span_question_write_module import TimeSpanQuestionCritique
from data_gen.questions.question_types.time_span.time_span_question_generator import MultiEventTimeSpanQuestionGenerator

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


class MultiEventTimeSpanQuestionRefineModule(ParsableBaseModule):
    def _create_formatting_critique(self, parsers: List[BasicNestedXMLParser]) -> BaseCritique:
        return OutputFormatCritique('format-entity-update', parsers, EXPECTED_OUTPUT_FORMAT)

    def _postprocess_values(self, values: Dict) -> Optional[Dict]:
        qa: Dict = values['current_qa_pair']
        additional_sentence_ids: str = qa.get('additional_sentence_ids', '') or ''
        values[QuestionGenerator.VAL_PAIRS] = [{
                MultiEventTimeSpanQuestionGenerator.VAL_QUESTION: qa['question'],
                MultiEventTimeSpanQuestionGenerator.VAL_ANSWER: qa['answer'],
                'ADDITIONAL_SENTENCE_IDS': [_id.strip() for _id in additional_sentence_ids.split(',') if len(_id.strip()) > 4],
                'ADDITIONAL_SENTENCE_IDS_EXPLANATION': qa.get('additional_sentence_explanation', ''),
                'scratchpad': values['scratchpad'],
                'scratchpad2': values['scratchpad2'],
                'current_qa_pair1': values['current_qa_pair1']
            }
        ]
        values[MultiEventTimeSpanQuestionGenerator.VAL_HOPS] = len(values['EVIDENCE_CURRENT_SELECTIONS'])
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
            TimeSpanQuestionCritique()
        ]

    def _get_parsers(self) -> List[BasicNestedXMLParser]:
        return [
            BasicNestedXMLParser('current_qa_pair', './/qa', is_object=True, allow_empty_list=False, result_node='results', to_single=True, require_fields=[
                'question', 'answer'
            ]),
            BasicNestedXMLParser('scratchpad2', './/scratchpad', is_object=False, shallow_text_extraction=True, result_node='scratchpad')

        ]

    def get_file_name(self, prompt: ParsablePrompt, values: Dict):
        node_idx: int = values['CREATED_AT']
        return f'N{node_idx:02d}-{self.name}_{self.instruction_name}.json'


def get_instructions(version: str) -> str:

    if version == 'v1':
        out: str = INSTRUCTIONS_V1
    if version == 'v2':
        out: str = INSTRUCTIONS_V2
    else:
        raise ValueError(version)
    return out.strip()


INSTRUCTIONS_V2 = """
Check the response from above following these steps:
1. Carefully examine the response and compare it to the task instructions.
2. Check if the response meets all criteria outlined in the task instructions.
3. If you find any problems or discrepancies, describe them in detail using the <scratchpad> tags.
4. If corrections are needed, make them and explain your changes within the <scratchpad> tags.
5. Provide the complete and corrected response, even if you didn't change anything.

Use the following output format for your response:

<scratchpad>
[Outline your reasoning here, including any problems found and explanations for corrections made]
</scratchpad>

<results>
<qa>
<question>[Your refined question about the time span]</question>
<answer>[The precise and concise answer to the question]</answer>
<additional_sentence_ids>[List of additional sentence IDs required to answer the question (including those selected in the previous response), if applicable]</additional_sentence_ids>
<additional_sentence_explanation>[Explain the unique information of each additional sentence that is required to answer the question and justify why it is needed, if applicable]</additional_sentence_explanation>
</qa>
</results>

Remember to provide a complete and accurate response, addressing all aspects of the task instructions. If no changes are needed, simply reproduce the original response in the correct format.

Important:
- Make minimal changes.
- Do not remove assumptions just because they are not explicitly stated.
"""

INSTRUCTIONS_V1 = """
Analyze and verify the question, answer, and selected sentences by following these steps:

1. Analyze the selected sentences:
   a. List the unique information from each sentence that is needed to infer the answer.
   b. Check if it's possible to replace any selected sentence with a different one from the complete outline. If so, consider refining the question to ensure each sentence is necessary.
   c. Ensure the question doesn't already mention the unique information that needs to be extracted from the sentences.

2. Verify information sufficiency:
   a. Check if the question requires any additional information beyond the selected sentences and event dates.
   b. If additional information is needed, either rephrase the question to remove the need or include the necessary information in the selected sentences.
   c. If you include a new sentence, provide an explanation for its inclusion.

3. Verify the assumptions:
   a. Remember that questions can add additional information that is not explicitly stated in the text but important to ensure that the answer duration can be computed with certainty, via assumptions.
   b. Verify that the assumptions made in the question are reasonable.
   c. Verify that the assumptions made in the question are required to derive the answer to the question.
   d. Verify that the assumptions do not provide the identical information as the selected sentences that is required to answer the question. It is important that one can only answer the question if one has access to ALL selected sentences.
   e. Adjust the assumptions in the question if needed and explain your decision.
   DO NOT remove assumptions just because they are not explicitly stated in the selected sentences (or other context). The purpose of framing questions with assumptions is that the question is specific enough to compute the duration even if the information in the selected sentences is not specific enough.

4. Ensure specificity:
   a. Double-check that the question is very specific to avoid ambiguities.
   b. Carefully analyze the other outline so far. Check if the question can be interpreted in other ways based on the other information available.
   c. Make sure that there is no other way to interpret the question, other than relying on the selected sentences.

5. Double-check the reasoning:
   a. Ensure that the answer is correctly inferred from the given information.
   b. Verify that the logic used to derive the answer is sound and based solely on the provided sentences.

After completing these steps, output your results using the following format:

<scratchpad>
[Outline your reasoning here]
</scratchpad>

<results>
<qa>
<question>[Your refined question about the time span]</question>
<answer>[The precise and concise answer to the question]</answer>
<additional_sentence_ids>[List of additional sentence IDs required to answer the question (including those selected in the previous response), if applicable]</additional_sentence_ids>
<additional_sentence_explanation>[Explain the unique information of each additional sentence that is required to answer the question and justify why it is needed, if applicable]</additional_sentence_explanation>
</qa>
</results>

Important reminders:
- Ensure that the question can ONLY be answered when ALL of the selected sentences are present, and that ALL of the selected sentences are needed to answer the question.
- Make sure that no other information from the <complete_outline> is sufficient to infer the correct answer.
- If you need to include additional sentences, clearly explain why they are necessary and what unique information they provide.
- In your question clearly indicate if some point in time happens in the future as such (for example when including the planned end date of an ongoing or planned event).
- In your question, DO NOT include the required temporal information. The temporal information must be inferred from the content of the selected sentences.
- State your assumptions that are required to answer the question clearly in the question.
- Make sure that the question cannot be answered without considering unique content from ALL selected evidence sentences (from <selected_sentences> and <additional_sentence_ids>)
- Ensure that you DO NOT explicitly refer to absolute dates or relative time spans (from the selected sentences) in the question. It is important that answering the question requires extracting this information from these sentences.
- Make sure your refined answer (if necessary) is in line with the previous instructions!
"""
