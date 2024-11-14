from typing import Dict, Optional, List

from src.mglockne_story_line.llm.critiques.base_critique import BaseCritique
from src.mglockne_story_line.llm.critiques.modules.output_format_critique import OutputFormatCritique
from src.mglockne_story_line.llm.modules.parsable_base_module import ParsableBaseModule
from src.mglockne_story_line.llm.prompting.modules.nested_parsable_output_prompt import BasicNestedXMLParser
from src.mglockne_story_line.llm.prompting.parsable_prompt import ParsablePrompt
from src.mglockne_story_line.llm.wrapper.base_llm_wrapper import BaseLLMWrapper
from src.mglockne_story_line.questions.question_generator import QuestionGenerator
from src.mglockne_story_line.questions.question_types.basic_questions.single_event_single_hop_question_generator import \
    SingleEventQuestionGenerator
from src.mglockne_story_line.util.entity_util import get_outline_dict_with_full_entity_names
from src.mglockne_story_line.util.story_tools import sort_outline_ids


EXPECTED_OUTPUT_FORMAT: str = """
<scratchpad>
[Your thinking can go here.]
</scratchpad>
<results>
<qa>
<question>[Your generated question]</question>
<answer>[The answer based on the evidence sentence]</answer>
</qa>
</results>
"""

class SimpleQuestionWriteModule(ParsableBaseModule):

    def _create_formatting_critique(self, parsers: List[BasicNestedXMLParser]) -> Optional[BaseCritique]:
        return OutputFormatCritique('format-add-specifics-outline', parsers, EXPECTED_OUTPUT_FORMAT)

    def _postprocess_values(self, values: Dict) -> Optional[Dict]:
        values[QuestionGenerator.VAL_PAIRS] = [{
                SingleEventQuestionGenerator.VAL_QUESTION: qa['question'],
                SingleEventQuestionGenerator.VAL_ANSWER: qa['answer']
            } for qa in values['current_qa_pairs']
        ]
        values[SingleEventQuestionGenerator.VAL_HOPS] = 1
        return super()._postprocess_values(values)

    def __init__(self, llm: BaseLLMWrapper, name: str, instruction_name: str):
        super().__init__(
            llm,
            name,
            instruction_name,
            get_instructions(instruction_name),
        )

    def _preprocess_values(self, values) -> Dict:

        id_to_full_entity_sent: Dict[str, Dict] = get_outline_dict_with_full_entity_names(
            values['event']['outline'], values['event']['entities']['entities']
        )

        selected_item_id: str = values[QuestionGenerator.VAL_CURRENT_SELECTION]

        # Build sentence
        current_sentence: str = id_to_full_entity_sent[selected_item_id]['decoded_sentence']

        # Build context
        context = '\n'.join([
            id_to_full_entity_sent[key]['decoded_sentence']
            for key in sort_outline_ids(id_to_full_entity_sent.keys())
            if key != selected_item_id
        ])
        values['SENTENCE'] = current_sentence
        values['CONTEXT'] = context
        return values

    def _get_parsers(self) -> List[BasicNestedXMLParser]:
        return [
            BasicNestedXMLParser('current_qa_pairs', './/qa', is_object=True, allow_empty_list=False, result_node='results')
        ]

    def get_file_name(self, prompt: ParsablePrompt, values: Dict):
        node_idx: int = values['CREATED_AT']
        return f'N{node_idx:02d}-{self.name}_{self.instruction_name}.json'


def get_instructions(version: str) -> str:

    if version == 'v3':
        out: str = INSTRUCTIONS_V3
    else:
        raise ValueError(version)
    return out.strip()


# A bit less super-specific
INSTRUCTIONS_V3 = """
You are an AI assistant tasked with analyzing a single sentence about a fictional event with fictional entities. Your goal is to identify specific details within the sentence and generate specific question-answer pairs based on these details.

Here is the sentence you will be working with:
<sentence>
{{SENTENCE}}
</sentence>

You will also be provided with a context consisting of other sentences. You MUST make sure that:
- None of the sentences from this context is sufficient to answer the question
- The question asks about specific information that can ONLY be found in the selected sentence

Here is the other context:
<context>
{{CONTEXT}}
</context>

Follow these steps to complete the task:

1. Carefully read the sentence and identify specific details and information within it. This may include names, numbers, dates, locations, actions, or any other precise information.

2. For each identified specific detail, generate a question-answer pair:
   - The question should ask for the very specific detail.
   - The answer should be the very specific detail from the sentence.
   - The question should not be answerable when the evidence is not available. Avoid narrowing the question to one plausible answer only.

3. Ensure that each question is specific to avoid ambiguities while maintaining a natural tone:
   - The question should be worded in a way that there is only one possible correct answer, even with the additional context provided.
   - Include relevant details from the sentence in the question itself to make it as specific as possible. Contextualize as necessary.
   - Add details to the question to make it unambiguous but avoid making it unnatural.

4. Ensure that the questions cannot be answered based on any of the other sentences provided in the context. Discard all questions that can be answered based on this context.

5. Ensure that the questions can fully be answered via the selected sentence. Discard all questions that cannot fully be answered with this sentence.

6. Format your output as follows:
<scratchpad>
[Your thinking can go here.]
</scratchpad>
<results>
<qa>
<question>[Your generated question]</question>
<answer>[The answer based on the evidence sentence]</answer>
</qa>
</results>

7. Generate up to {{NUM_QUESTIONS}} question-answer pairs. Each pair should focus on a different detail.

Here are examples of good and bad question-answer pairs:

Good example:
<qa>
<question>What was the time that John Smith arrived at Central Park on July 4, 2023?</question>
<answer>2:15 PM</answer>
</qa>

Bad example:
<qa>
<question>When did John arrive at the park?</question>
<answer>2:15 PM on July 4, 2023</answer>
</qa>
(This is bad because the question is not specific enough and the answer includes more information than what was asked.)
Better Question: What was the time that John Smith arrived at Central Park on July 4, 2023?

Bad example:
<qa>
<question>What type of cyber attack technique involving database queries was used in the hacking methods described?</question>
<answer>SQL injection</answer>
</qa>
(This is bad because the question narrows the possible answer options too much. Even without evidence, SQL injection is the most plausible cyber attack involving database queries.)
Better Question: What type of cyber attack techniques was used in the hacking attack of [attack incident]?

Bad example:
<qa>
<question>How many cars were explicitly mentioned in the accident description?</question>
<answer>5</answer>
</qa>
(This is bad because the question is about the description and not the underlying event)
Better Question: How many cars were involved in the car accident on [some details about the accident]?

Bad example:
<qa>
<question>How many cars were involved in the accident near the caste Rockingham, which was built in 1457 by Thomas Cook?</question>
<answer>2</answer>
</qa>
(This is bad because the question is overly specific and includes too many specific details)
Better Question: How many cars were involved in the car accident near the castle Rockingham?

Important information:
- The sentence describes part of a fictional event. Your questions must address the fictional event.
- DO NOT phrase questions around the sentence as text, but rather about the content of the sentence that describes parts of the fictional event.
- Avoid terms like "precise" or "specific" in the question. You must make the question specific by providing specific and precise details.

Now, begin the task of generating question-answer pairs based on the provided sentence. Remember to make your questions as specific as possible and ensure that each answer directly corresponds to its question. 
Include all question-answer pairs within a single <results> tag.
"""



INSTRUCTIONS_V2 = """
You are an AI assistant tasked with analyzing a single sentence about a fictional event with fictional entities. Your goal is to identify specific details within the sentence and generate highly specific question-answer pairs based on these details.

Here is the sentence you will be working with:
<sentence>
{{SENTENCE}}
</sentence>

You will also be provided with a context consisting of other sentences. You MUST make sure that:
- None of the sentences from this context is sufficient to answer the question
- The question asks about specific information that can ONLY be found in the selected sentence

Here is the other context:
<context>
{{CONTEXT}}
</context>

Follow these steps to complete the task:

1. Carefully read the sentence and identify very specific details and information within it. This may include names, numbers, dates, locations, actions, or any other precise information.

2. For each identified specific detail, generate a question-answer pair:
   - The question should ask for the very specific detail.
   - The answer should be the very specific detail from the sentence.
   - The question should not be answerable when the evidence is not available. Avoid narrowing the question to one plausible answer only.

3. Ensure that each question is highly specific to avoid ambiguities:
   - The question should be worded in a way that there is only one possible correct answer, even if additional context were provided.
   - Include relevant details from the sentence in the question itself to make it as specific as possible. Contextualize as necessary.
   - Add as many details as possible to the question to make it unambiguous.

4. Ensure that the questions cannot be answered based on any of the other sentences provided in the context. Discard all questions that can be answered based on this context.

5. Ensure that the questions can fully be answered via the selected sentence. Discard all questions that cannot fully be answered with this sentence.

6. Format your output as follows:
<scratchpad>
[Your thinking can go here.]
</scratchpad>
<results>
<qa>
<question>[Your generated question]</question>
<answer>[The answer based on the evidence sentence]</answer>
</qa>
</results>

7. Generate as many question-answer pairs as there are specific details in the sentence. Each pair should focus on a different detail.

Here are examples of good and bad question-answer pairs:

Good example:
<qa>
<question>What was the time that John Smith arrived at Central Park on July 4, 2023?</question>
<answer>2:15 PM</answer>
</qa>

Bad example:
<qa>
<question>When did John arrive at the park?</question>
<answer>2:15 PM on July 4, 2023</answer>
</qa>
(This is bad because the question is not specific enough and the answer includes more information than what was asked.)
Better Question: What was the time that John Smith arrived at Central Park on July 4, 2023?

Bad example:
<qa>
<question>What type of cyber attack technique involving database queries was used in the hacking methods described?</question>
<answer>SQL injection</answer>
</qa>
(This is bad because the question narrows the possible answer options too much. Even without evidence, SQL injection is the most plausible cyber attack involving database queries.)
Better Question: What type of cyber attack techniques was used in the hacking attack of [attack incident]?

Bad example:
<qa>
<question>How many cars were explicitly mentioned in the accident description?</question>
<answer>5</answer>
</qa>
(This is bad because the question is about the description and not the underlying event)
Better Question: How many cars were involved in the car accident on [some details about the accident]?

Important information:
- The sentence describes part of a fictional event. Your questions must address the fictional event.
- DO NOT phrase questions around the sentence as text, but rather about the content of the sentence that describes parts of the fictional event.
- Avoid terms like "precise" or "specific" in the question. You must make the question specific by providing specific and precise details.

Now, begin the task of generating question-answer pairs based on the provided sentence. Remember to make your questions as specific as possible and ensure that each answer directly corresponds to its question. Include all question-answer pairs within a single <results> tag."""



INSTRUCTIONS_V1 = """
You are an AI assistant tasked with analyzing a single sentence about a fictional event with fictional entities. Your goal is to identify specific details within the sentence and generate highly specific question-answer pairs based on these details.

Here is the sentence you will be working with:
<sentence>
{{SENTENCE}}
</sentence>

You will also be provided with a context consisting of other sentences. You MUST make sure that:
- answering the question does not rely on any of this information
- none of the sentences from this context is sufficient to answer the question

Here is the other context:
<context>
{{CONTEXT}}
</context>

Follow these steps to complete the task:

1. Carefully read the sentence and identify very specific details and information within it. This may include names, numbers, dates, locations, actions, or any other precise information.

2. For each identified specific detail, generate a question-answer pair:
   - The question should ask for the very specific detail.
   - The answer should be the very specific detail from the sentence.

3. Ensure that each question is highly specific to avoid ambiguities:
   - The question should be worded in a way that there is only one possible correct answer, even if additional context were provided.
   - Use precise language and include relevant details from the sentence in the question itself to make it as specific as possible.
   - Add as many details as possible to the question to make it unambiguous.

4. Ensure that the questions cannot be answered with confidence based on any of the other sentences provided in the <context>. Discard all question that can be answered based on this context.

5. Ensure that the questions can fully be answered via the selected <sentence>. Discard all questions that cannot fully be answered with this sentence.

6. Format your output as follows:
<results>
<qa>
<question>[Your generated question]</question>
<answer>[The answer based on the evidence sentence]</answer>
</qa>
</results>

7. Generate as many question-answer pairs as there are specific details in the sentence. Each pair should focus on a different detail.

Here are examples of good and bad question-answer pairs:

Good example:
<qa>
<question>What was the time that John Smith arrived at Central Park on July 4, 2023?</question>
<answer>2:15 PM</answer>
</qa>

Bad example:
<qa>
<question>When did John arrive at the park?</question>
<answer>2:15 PM on July 4, 2023</answer>
</qa>
(This is bad because the question is not specific enough and the answer includes more information than what was asked.)

Important information:
- The sentence describes part of a fictional event. Your questions must address the fictional event.
- DO NOT phrase questions around the sentence as text, but rather about the content of the sentence that describes parts of the fictional event.
- Avoid terms like "precise" or "specific" in the question. You must make the question specific by providing specific and precise details.

Now, begin the task of generating question-answer pairs based on the provided sentence. Remember to make your questions as specific as possible and ensure that each answer directly corresponds to its question. Include all question-answer pairs within a single <results> tag.
"""
