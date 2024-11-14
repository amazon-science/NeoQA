from copy import deepcopy
from typing import Dict, List

from src.mglockne_story_line.llm.critiques.base_critique import BaseCritique
from src.mglockne_story_line.llm.critiques.modules.output_format_critique import OutputFormatCritique
from src.mglockne_story_line.llm.modules.named_module_pipeline import NamedModulePipeline
from src.mglockne_story_line.llm.modules.parsable_base_module import ParsableBaseModule
from src.mglockne_story_line.llm.prompting.modules.nested_parsable_output_prompt import BasicNestedXMLParser
from src.mglockne_story_line.llm.prompting.parsable_prompt import ParsablePrompt
from src.mglockne_story_line.llm.wrapper.base_llm_wrapper import BaseLLMWrapper
from src.mglockne_story_line.questions.elements.qa_pair import QAPair

from src.mglockne_story_line.questions.question_reviser import QuestionReviser
from src.mglockne_story_line.util.ids import generate_id

EXPECTED_OUTPUT_FORMAT = """
<scratchpad>
[Your thinking process, including analysis of the original question, identification of key details, and reasoning for the proposed change]
</scratchpad>
<results>
<qa>
<question>[Your generated question with the subtle change]</question>
<explanation>[Explanation of the changed specificity and how it meets the requirements]</explanation>
<information-sentence-id>[The sentence ID that introduces the information you made more specific]</information-sentence-id>
</qa>
</results>
"""

class UncertainFalsePremiseReviserModule(ParsableBaseModule):
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
        return f'N{node_idx:02d}-UNCERTAIN-PREMISE-{self.name}_{self.instruction_name}.json'


    def _get_parsers(self) -> List[BasicNestedXMLParser]:
        return [
            BasicNestedXMLParser(self.output_key, './/qa', is_object=True, allow_empty_list=False, result_node='results')
        ]

    def _create_formatting_critique(self, parsers: List[BasicNestedXMLParser]) -> BaseCritique:
        return OutputFormatCritique(self.output_key, parsers, EXPECTED_OUTPUT_FORMAT)


class UncertainFalsePremiseReviser(QuestionReviser):

    def __init__(self, llm: BaseLLMWrapper, output_key: str, instruction_name: str, false_premise_type: str):

        pipeline: NamedModulePipeline = NamedModulePipeline(
            name='generate-uncertain-premise-question',
            modules=[
                UncertainFalsePremiseReviserModule(
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
            uncertain_premise_expl: str = result['explanation']
            results.append(QAPair(
                question=question,
                question_id=generate_id(result),
                answer=parent_qa_pair.answer,
                evidence_ids=values['EVIDENCE_CURRENT_SELECTIONS'],
                created_at=values['CREATED_AT'],
                num_hops=len(values['EVIDENCE_CURRENT_SELECTIONS']),
                is_valid=True,
                category='false-premise-uncertain',
                validations=[],
                distractors=[deepcopy(distractor) for distractor in parent_qa_pair.distractors],
                false_premise_category=self.false_premise_type,
                false_premise_sentence_id=None,
                misc={
                    'false-premise': uncertain_premise_expl
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
You are an AI assistant tasked with generating false-premise questions based on fictional events. Your goal is to create questions that cannot be answered because they make possible but unknown assumptions about the events. Follow these instructions carefully:

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

To generate unknown-premise questions:
1. Identify key information in one of the two selected sentences.
2. Modify the question by making it more specific. 
   - The added details must be POSSIBLE based on the provided sentences and the provided list of all outlines. 
   - The added details must be UNVERIFIED based on the provided sentences and the provided list of all outlines. 
   - The added details must be substantial to require additional verification. Avoid details that are not only possible but also very likely.
3. Keep the question as similar as possible to the original question, asking for the same information but changing small details that contradict the two sentences.
4. Only include ONE specific unverified detail to the question.

Consider the additional context when creating the new question:
1. Make sure that the details you add cannot be confirmed by any of the sentences
2. Make sure that the details you add cannot be refuted by any of the sentences

Generate multiple such questions if possible, each based on different key information from the selected sentences.
Only output the questions for which you are certain that:
- The details you add cannot be confirmed by any of the sentences
- The details you add cannot be refuted by any of the sentences
- The details are substantial enough to require additional verification.

Here are some examples of ways to add specificity:
- Let a person have a more specific role: Instead of "a criminal of the ring," say "a ring leader" or "a lookout."
- Add a specific characteristic to an object: Instead of "a car," say "a red sports car" or "an old sedan."
- Use a hyponym where the 'is-a' relation holds: Instead of "a person," say "a woman" or "a child."
- Specify a location: Instead of "a park," say "a national park" or "Central Park."
- Specify a time: Instead of "at night," say "at 9 PM" or "during the full moon."
- Specify a number or quantity: Instead of "several books," say "three books" or "a dozen books."
- Specify a direction: Instead of "headed away," say "headed east" or "to the mountains."
- Specify a duration: Instead of "waited," say "waited for 15 minutes" or "waited for an hour."

Format your output as follows:
<scratchpad>
[Your thinking process]
</scratchpad>
<results>
<qa>
<question>[Your generated question]</question>
<explanation>[Explanation of the unknown information]</explanation>
</qa>
</results>

Repeat the <qa> section for each question you generate.

Remember:
- Keep your responses concise and avoid verbose explanations.
- Always consider the additional context to avoid creating questions that can be validly answered using that information.
"""
