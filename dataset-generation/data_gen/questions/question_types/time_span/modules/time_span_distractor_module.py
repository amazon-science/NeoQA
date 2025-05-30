import re
from typing import Dict, List, Optional
from data_gen.llm.critiques.base_critique import BaseCritique
from data_gen.llm.critiques.critique_result import CritiqueResult
from data_gen.llm.critiques.output_format_critique import OutputFormatCritique
from data_gen.llm.modules.parsable_base_module import ParsableBaseModule
from data_gen.llm.prompting.modules.nested_parsable_output_prompt import BasicNestedXMLParser
from data_gen.llm.prompting.parsable_prompt import ParsablePrompt
from data_gen.llm.wrapper.base_llm_wrapper import BaseLLMWrapper
from data_gen.questions.question_generator import QuestionGenerator



EXPECTED_OUTPUT_FORMAT: str = """
<distractors>
<distractor>
<answer>[The incorrect answer]</answer>
<explanation>[A brief explanation why it is incorrect]</explanation>
<distractor-sentences>[Comma separated sentence IDs of the sentences that make the distractor sound plausible]</distractor-sentences>
</distractor>

[Repeat the above structure for each distractor]
</distractors>
""".strip()

class CorrectAnswerCritique(BaseCritique):
    def __init__(self):
        super().__init__('correct-answer-distractor')

    def to_error_string(self, item: Dict):
        raise NotImplementedError

    def process(self, values: Dict) -> CritiqueResult:
        correct_answer: str = values['CORRECT_TIMESPAN_ANSWER']
        conflict_message: str = f"The distractor contains the answer. Ensure it does not overlap with the correct answer:\n"
        errors: List[Dict] = []
        pattern = r'\b' + re.escape(correct_answer.lower()) + r'\b'
        for distractor in values['distractors']:

            #if correct_answer.lower().strip() in distractor['answer'].lower().strip():
            if re.search(pattern, distractor['answer'].lower().strip()):
                conflict_message += f'\t- {distractor["answer"]}\n'
                errors.append({
                    'correct': correct_answer,
                    'distractor': distractor
                })
        self.add_errors_to_result(values, errors)
        return CritiqueResult(
            self.name,
            len(errors) == 0,
            errors,
            conflict_message
        )


class MultiEventTimeSpanDistractorGenerator(ParsableBaseModule):

    def _create_formatting_critique(self, parsers: List[BasicNestedXMLParser]) -> Optional[BaseCritique]:
        return OutputFormatCritique('format-add-specifics-outline', parsers, EXPECTED_OUTPUT_FORMAT)

    def _postprocess_values(self, values: Dict) -> Optional[Dict]:
        values[QuestionGenerator.VAL_CURRENT_PAIR]['distractors'] = values['distractors']
        return super()._postprocess_values(values)

    def __init__(self, llm: BaseLLMWrapper, name: str, instruction_name: str):
        super().__init__(
            llm,
            name,
            instruction_name,
            get_instructions(instruction_name),
        )

    def _create_critiques(self) -> List[BaseCritique]:
        return [
            CorrectAnswerCritique()
        ]

    def _preprocess_values(self, values) -> Dict:
        # id_to_full_entity_sent: Dict[str, Dict] = get_outline_dict_with_full_entity_names(
        #     values['event']['outline'], values['event']['entities']['entities']
        # )
        # # Build context
        # context = '\n'.join([
        #     id_to_full_entity_sent[key]['decoded_sentence']
        #     for key in sort_outline_ids(id_to_full_entity_sent.keys())
        # ])
        # values['OUTLINE'] = context
        #
        # qa_pair: dict = values[QuestionGenerator.VAL_CURRENT_PAIR]
        # values['QUESTION'] = qa_pair[SingleEventQuestionGenerator.VAL_QUESTION]
        # values['ANSWER'] = qa_pair[SingleEventQuestionGenerator.VAL_ANSWER]
        values['CURRENT_TIMESPAN_QUESTION'] = values["QA_CURRENT_PAIR"]['TIMESPAN_QUESTION']
        values['CORRECT_TIMESPAN_ANSWER'] = values["QA_CURRENT_PAIR"]['TIMESPAN_ANSWER']
        return values

    def _get_parsers(self) -> List[BasicNestedXMLParser]:
        return [
            BasicNestedXMLParser('distractors', './/distractor', is_object=True, allow_empty_list=False, result_node='distractors')
        ]

    def get_file_name(self, prompt: ParsablePrompt, values: Dict):
        node_idx: int = values['CREATED_AT']
        return f'N{node_idx:02d}-{self.name}_{self.instruction_name}.json'


def get_instructions(version: str) -> str:

    if version == 'v1':
        out: str = INSTRUCTIONS_V1
    else:
        raise ValueError(version)
    return out.strip()


INSTRUCTIONS_V1 = """
You are an AI assistant tasked with creating challenging multiple-choice distractor options for a question based on a fictional event outline. Your goal is to create plausible but incorrect answer choices that will test the reader's understanding of the given information.

First, carefully read and analyze the following fictional event outline:

<outline>
{{STORYLINE_OUTLINE_TO_DATE}}
</outline>

Now, consider the following question:

<question>
{{CURRENT_TIMESPAN_QUESTION}}
</question>

The correct answer to this question is:

<correct_answer>
{{CORRECT_TIMESPAN_ANSWER}}
</correct_answer>

To correctly answer this question, these sentences from the outline are required:

<selected-sentences>
{{SELECTED_SENTENCES}}
</selected-sentences>

Your task is to create {{NUM_DISTRACTORS}} plausible but incorrect multiple-choice distractor options for this question. These distractors should be challenging and appear realistic, but must not be valid answers to the question.

Follow these guidelines when creating effective distractors:
1. Ensure each distractor is clearly incorrect when compared to the correct answer.
2. Use information from the fictional event outline to make distractors sound plausible.
3. If possible, incorporate specific values or details from the outline to increase believability.
4. Align distractors with non-answer text from the outline to make them more challenging.
5. Vary the type and structure of distractors to avoid patterns.
6. Ensure distractors are distinct from each other and the correct answer.
7. Make sure that the distractor is not by accident a valid answer based on different information from the outline.
8. Make sure all distractor options are plausible.

Present your {{NUM_DISTRACTORS}} distractor options in the following format:

<distractors>
<distractor>
<answer>[The incorrect answer]</answer>
<explanation>[A brief explanation why it is incorrect]</explanation>
<distractor-sentences>[Comma separated sentence IDs of the sentences that make the distractor sound plausible]</distractor-sentences>
</distractor>

[Repeat the above structure for each distractor]
</distractors>

After each distractor, provide a brief explanation of why it's incorrect but plausible, and list all sentence IDs (as a comma-separated list) from the outline that make the distractor sound plausible. Leave the list of sentence IDs empty if none other sentence from the outline increases the plausibility for this distractor. Both should be included within the respective distractor tags.

Remember, your goal is to create challenging distractors that will test the reader's understanding of the fictional event outline while ensuring they are definitively incorrect. Use your knowledge and creativity to craft distractors that are both believable and clearly distinguishable from the correct answer.

Before presenting your final distractors, use a <scratchpad> to brainstorm and refine your ideas. Consider different aspects of the outline that could be misinterpreted or confused, and how you can use these to create compelling distractors.

Once you have finalized your distractors, present them in the format specified above, ensuring that each one is unique, challenging, and clearly incorrect when compared to the correct answer.
"""
