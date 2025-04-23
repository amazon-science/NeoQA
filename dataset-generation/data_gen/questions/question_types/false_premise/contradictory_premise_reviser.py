from copy import deepcopy
from typing import Dict, List

from data_gen.llm.critiques.base_critique import BaseCritique
from data_gen.llm.critiques.output_format_critique import OutputFormatCritique
from data_gen.llm.modules.named_module_pipeline import NamedModulePipeline
from data_gen.llm.modules.parsable_base_module import ParsableBaseModule
from data_gen.llm.prompting.modules.nested_parsable_output_prompt import BasicNestedXMLParser
from data_gen.llm.prompting.parsable_prompt import ParsablePrompt
from data_gen.llm.wrapper.base_llm_wrapper import BaseLLMWrapper
from data_gen.questions.elements.qa_pair import QAPair
from data_gen.questions.question_reviser import QuestionReviser
from data_gen.util.ids import generate_id

EXPECTED_OUTPUT_FORMAT = """
<scratchpad>
[Your thinking process]
</scratchpad>
<results>
<qa>
<question>[Your generated false-premise question]</question>
<false-premise>[Explanation of the false premise introduced]</false-premise>
<contradictory-sentence-id>[The sentence ID that is contradictory to the changed information]</contradictory-sentence-id>
</qa>
</results>
"""


class ContradictoryFalsePremiseReviserModule(ParsableBaseModule):
    def _preprocess_values(self, values) -> Dict:
        values['QUESTION'] = values['QA_CURRENT_PAIR'].question
        values['ANSWER'] = values['QA_CURRENT_PAIR'].answer
        return super()._preprocess_values(values)

    def __init__(self, llm: BaseLLMWrapper, name: str, instruction_name: str, output_key: str):
        self.output_key: str = output_key
        super().__init__(
            llm,
            name,
            instruction_name,
            get_instructions(instruction_name),
        )

    def get_file_name(self, prompt: ParsablePrompt, values: Dict):
        node_idx: int = values['CREATED_AT']
        return f'N{node_idx:02d}-FALSE-PREMISE-{self.name}_{self.instruction_name}.json'

    def _get_parsers(self) -> List[BasicNestedXMLParser]:
        return [
            BasicNestedXMLParser(self.output_key, './/qa', is_object=True, allow_empty_list=False, result_node='results')
        ]

    def _create_formatting_critique(self, parsers: List[BasicNestedXMLParser]) -> BaseCritique:
        return OutputFormatCritique(self.output_key, parsers, EXPECTED_OUTPUT_FORMAT)


class ContradictoryFalsePremiseReviser(QuestionReviser):

    def __init__(self, llm: BaseLLMWrapper, output_key: str, instruction_name: str, false_premise_type: str):

        pipeline: NamedModulePipeline = NamedModulePipeline(
            name='generate-false-premise-question-contradictory',
            modules=[
                ContradictoryFalsePremiseReviserModule(
                    llm, f'generate-questions-{output_key}', instruction_name, output_key
                )
            ]
        )
        self.false_premise_type: str = false_premise_type
        super().__init__(output_key, pipeline)

    def get_qa_pairs(self, values: Dict, storyline: Dict, parent_qa_pair: QAPair) -> List[QAPair]:
        results: List[QAPair] = []
        for result in values[self.output_key]:
            question: str = result['question']
            false_premise_expl: str = result['false-premise']
            contradictory_sentence_id: str = result['contradictory-sentence-id'].strip()
            is_valid: bool = contradictory_sentence_id in values['EVIDENCE_CURRENT_SELECTIONS']
            results.append(QAPair(
                question=question,
                question_id=generate_id(result),
                answer=parent_qa_pair.answer,
                evidence_ids=values['EVIDENCE_CURRENT_SELECTIONS'],
                created_at=values['CREATED_AT'],
                num_hops=len(values['EVIDENCE_CURRENT_SELECTIONS']),
                is_valid=is_valid,
                category='false-premise-contradictory',
                validations=[],
                distractors=[deepcopy(distractor) for distractor in parent_qa_pair.distractors],
                false_premise_category=self.false_premise_type,
                false_premise_sentence_id=contradictory_sentence_id,
                misc={
                    'false-premise': false_premise_expl
                },
                event_information={
                    k: storyline[k] for k in ['event_type', 'event_type_id', 'story_seed_id']
                } | {
                    'parent_question': parent_qa_pair.question_id
                },
            ))
        return results


def get_instructions(version: str) -> str:

    if version == 'v1':
        out: str = INSTRUCTIONS_V1
    else:
        raise ValueError(version)
    return out.strip()


INSTRUCTIONS_V1 = """
You are an AI assistant tasked with generating false-premise questions based on fictional events. Your goal is to create questions that cannot be answered because they make incorrect assumptions about the events. Follow these instructions carefully:

You will be provided with the following information:
<question>
{{QUESTION}}
</question>

<selected_sentences>
{{SELECTED_SENTENCES}}
</selected_sentences>

<answer>
{{ANSWER}}
</answer>

<context>
{{STORYLINE_OUTLINE_TO_DATE}}
</context>

To generate false-premise questions:
1. Identify key information in one of the two selected sentences.
2. Create a question that contradicts this key information while keeping other details intact.
3. Ensure the false premise is mutually exclusive with the original information.
4. Make the questions challenging, with false premises that are easy to miss but mutually exclusive to the evidence sentences and context. For example:
   - If you change a name, change the lastname only
   - If you refer to a person or place, rather than changing the name, refer to a changed property of this entity (e.g., "in a 60-year-old building" instead of "in the 20-year-old office")
   - Replace with similar mutually exclusive cohyponyms (e.g., replace a cocker spaniel with a poodle)
   - In all of these cases, ensure that you do not accidentally create a valid question!
5. Keep the question as similar as possible to the original question, asking for the same information but changing small details that contradict the two sentences.
6. Only include ONE false premise for in each question.

Consider the additional context when creating false premises:
1. Avoid creating questions that can be validly answered using information from the context.
2. Ensure that the false premise remains inconsistent with both the selected sentences and the context.

Generate multiple false-premise questions if possible, each based on different key information from the selected sentences.
The changed information must be contradictory to one of the selected sentences only. 
Output the sentence that is contradictory (or mutually exclusive to) the generated false-premise question.

Format your output as follows:
<scratchpad>
[Your thinking process]
</scratchpad>
<results>
<qa>
<question>[Your generated false-premise question]</question>
<false-premise>[Explanation of the false premise introduced]</false-premise>
<contradictory-sentence-id>[The sentence ID that is contradictory to the changed information]</contradictory-sentence-id>
</qa>
</results>

Repeat the <qa> section for each false-premise question you generate.

Remember:
- Keep your responses concise and avoid verbose explanations.
- Ensure that the false premises are subtle but clear enough to invalidate the question.
- Generate multiple false-premise questions if possible, based on different key information from the selected sentences.
- Always consider the additional context to avoid creating questions that can be validly answered using that information.
"""
