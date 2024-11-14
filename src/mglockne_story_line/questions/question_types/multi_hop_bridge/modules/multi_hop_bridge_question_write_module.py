from typing import Dict, Optional, List, Set

from src.mglockne_story_line.llm.critiques.critique_result import CritiqueResult
from src.mglockne_story_line.llm.critiques.base_critique import BaseCritique
from src.mglockne_story_line.llm.critiques.modules.output_format_critique import OutputFormatCritique
from src.mglockne_story_line.llm.modules.parsable_base_module import ParsableBaseModule
from src.mglockne_story_line.llm.prompting.modules.nested_parsable_output_prompt import BasicNestedXMLParser
from src.mglockne_story_line.llm.prompting.parsable_prompt import ParsablePrompt
from src.mglockne_story_line.llm.wrapper.base_llm_wrapper import BaseLLMWrapper
from src.mglockne_story_line.questions.question_types.multi_hop_bridge.multi_hop_bridge_question_generator import \
    MultiEventMultiHopBridgeEntityQuestionGenerator


EXPECTED_OUTPUT_FORMAT: str = """
<scratchpad>
[Your thinking can go here.]
</scratchpad>
<results>
<qa>
<question>[Your generated question]</question>
<answer>[The answer based on the evidence sentences]</answer>
<additional_sentence_ids>[List of additional sentence IDs required to answer the question, if applicable]</additional_sentence_ids>
<additional_sentence_explanation>[Explain the unique information of each additional sentence that is required to answer the question and justify why it is needed, if applicable]</additional_sentence_explanation>
</qa>
</results>

"""


class MultiHopQuestionCritique(BaseCritique):
    """
    Make sure that a name is not too long (which would likely be due to en error in parsing)
    """
    def process(self, values: Dict) -> CritiqueResult:

        errors: List[Dict] = []
        error_message: str = f"Make sure that all additional sentences from the <additional_sentence_ids> are from the selected events. The following sentences are NOT from the selected events:\n"
        selected_events: List[Dict] = values['SELECTED_EVENTS']
        all_item_ids: Set[str] = {
            item['id']
            for event in selected_events
            for item in event['outline']
        }

        for qa in values['current_qa_pairs']:
            if 'additional_sentence_ids' in qa and qa['additional_sentence_ids'] is not None:
                newly_selected_ids: Set[str] = {
                    item_id.strip() for item_id in qa['additional_sentence_ids'].split(',')
                    if len(item_id.strip()) > 0
                }

                incorrect_ids: List[str] = sorted(list(newly_selected_ids - all_item_ids))
                if len(incorrect_ids) > 0:
                    errors.append({
                        'incorrect_item_ids': incorrect_ids
                    })
                    error_message += f'\t- {incorrect_ids}\n'

        if len(errors) == 0:
            return CritiqueResult.correct(self.name)
        else:
            return CritiqueResult(self.name, False, errors, error_message)

    def __init__(self, field='current_qa_pair'):
        super().__init__('multi-hop-question-critique')
        self.field: str = field


class MultiEventMultiHopQuestionWriteModule(ParsableBaseModule):

    def _postprocess_values(self, values: Dict) -> Optional[Dict]:

        values[MultiEventMultiHopBridgeEntityQuestionGenerator.VAL_PAIRS] = []
        for qa in values['current_qa_pairs']:
            additional_sentence_ids_str: str = qa.get('additional_sentence_ids', '') or ''
            additional_sentence_ids_str = additional_sentence_ids_str.strip()
            additional_sentence_ids: List[str] = [
                item_id.strip() for item_id in additional_sentence_ids_str.split(',')
                if len(item_id.strip()) > 0
            ]
            additional_sentence_explanation: str = qa.get('additional_sentence_explanation', '') or ''
            additional_sentence_explanation = additional_sentence_explanation.strip()
            values[MultiEventMultiHopBridgeEntityQuestionGenerator.VAL_PAIRS].append({
                MultiEventMultiHopBridgeEntityQuestionGenerator.VAL_QUESTION: qa['question'],
                MultiEventMultiHopBridgeEntityQuestionGenerator.VAL_ANSWER: qa['answer'],
                'additional_sentence_ids': additional_sentence_ids,
                'additional_sentence_explanation': additional_sentence_explanation
            })
        #     if 'additional_sentence_explanation' in qa:
        #         assert False, 'implement me'
        # values[MultiEventMultiHopBridgeEntityQuestionGenerator.VAL_PAIRS] = [{
        #         MultiEventMultiHopBridgeEntityQuestionGenerator.VAL_QUESTION: qa['question'],
        #         MultiEventMultiHopBridgeEntityQuestionGenerator.VAL_ANSWER: qa['answer']
        #     } for qa in values['current_qa_pairs']
        # ][:values['NUM_QUESTIONS']]
        values[MultiEventMultiHopBridgeEntityQuestionGenerator.VAL_HOPS] = -1  # legacy code -- should be removed
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

    def _get_parsers(self) -> List[BasicNestedXMLParser]:
        return [
            BasicNestedXMLParser('current_qa_pairs', './/qa', is_object=True, allow_empty_list=False, result_node='results')
        ]

    def _create_critiques(self) -> List[BaseCritique]:
        return [MultiHopQuestionCritique('current_qa_pairs')]

    def _create_formatting_critique(self, parsers: List[BasicNestedXMLParser]) -> BaseCritique:
        return OutputFormatCritique('current_qa_pairs', parsers, EXPECTED_OUTPUT_FORMAT)

    def get_file_name(self, prompt: ParsablePrompt, values: Dict):
        node_idx: int = values['CREATED_AT']
        return f'N{node_idx:02d}-{self.name}_{self.instruction_name}.json'


def get_instructions(version: str) -> str:

    if version == 'v1':
        out: str = INSTRUCTIONS_V1
    elif version == 'v2':
        out: str = INSTRUCTIONS_V2
    elif version == 'v3':
        out: str = INSTRUCTIONS_V3
    elif version == 'v4':
        out: str = INSTRUCTIONS_V4


    else:
        raise ValueError(version)
    return out.strip()


INSTRUCTIONS_V4 = """
You are an AI assistant tasked with analyzing two sentences about fictional events involving fictional named entities and generating multi-hop questions using a bridge entity. Your goal is to identify specific details within these sentences and create {{NUM_QUESTIONS}} question-answer pairs that require reasoning over both sentences.

First, familiarize yourself with the complete storyline outline of the fictional events:

<storyline_outline>
{{STORYLINE_OUTLINE_TO_DATE}}
</storyline_outline>

Now, focus on the two selected sentences based on which you must generate multi-hop questions:

<selected_sentences>
{{SELECTED_SENTENCES}}
</selected_sentences>

The bridge entity in these sentences is:

<bridge_entity>{{BRIDGE_ENTITY_NAME}}</bridge_entity>

To generate multi-hop questions that require reasoning over both sentences, follow these steps:

1. Identify information about the bridge entity in both sentences that is unique to these two sentences and cannot be found based on any other information from the provided storyline outline. This information should be as specific as possible, to avoid any ambiguities or overlap with other information from other sentences.

2. To generate a question-answer pair, ask for specific information about the bridge entity from one sentence while describing the bridge entity with information from the other sentence. Make sure that the correct answer is concise and factual. The answer should focus on very specific details that can be described in few words. 
   - Make sure that the question is answerable.
   - Make sure to ask for short and concise information
   - Make sure that the way you paraphrase the bridge named entity clearly identifies the bridge entity using the unique information from the selected sentence (and not more)
   - Ensure that you do not introduce additional ambiguity when paraphrasing: 
        a. If the evidence says that the bridge entity announces the creation of something, it does not mean that the bridge entity created it. Be careful in your word choice to avoid ambiguities.
        b. Do include specific information (such as the named entity's profession or role) from the <storyline_outline> if they are not explicitly clear in from the selected sentences.

3. Make sure that the information from the selected sentences is sufficient to answer the question with certainty. Your question must not rely on other information that is only communicated in different sentences. If it is important to include additional information that is not included in the selected sentences, add the additional sentence IDs that are needed to the output. 
   - For each of the new sentences, explain the unique information from the sentence that is required to answer the question 
   - For each of the new sentences, ensure that the unique information from the new sentences is required to answer the question with certainty. Refine the question idea if necessary.

4. Do not mention the bridge named entity explicitly in your questions. Paraphrase the bridge named entity using the unique information from one of the selected sentences.

5. Ensure that the question can ONLY be answered when having access to the information from BOTH sentences. Make sure that all selected sentences must be considered to answer the question. Avoid using the bridge entity itself as the answer.

6. Ensure that the information that is required from each sentence is unique within this sentence: It can neither be inferred nor extracted from any other sentence within the provided storyline outline. If the question can be answered based on the other information from the storyline outline, increase the specificity of the required details and ensure they are unique to the selected sentences.

7. Verify that your question does not assume any relations that are not clear from the selected sentences. 
   - You can only assume that the bridge entity is identical across all sentences. Other information may not refer to the identical entity. For example, a group of people in one sentence may not be identical to a group of people in another sentence.
   - Do not assume causality between the selected sentences.
   If in doubt, rely on the bridge entity.
   
8. Compare each specific detail in the question with the selected sentences. Make sure that each detail can with certainty be inferred from the selected sentences. If not, omit or generalize the specific details that cannot be inferred from the selected sentences.
   - Only focus on the selected sentences!
   - Correct information that is only known from the <storyline_outline> but not from the <selected_sentences> must NOT be used in the question.
  - DO NOT assume the profession of an entity when paraphrasing it, unless it is fully clear from the selected sentences! DO NOT write "artist" if the <selected_sentences> do not introduce this person as "artist".

Use the following scratchpad format to outline your reasoning:

<scratchpad>
Sentence information: 
[List all specific information from each sentence, that can be used to create a question]

Idea: 
[Brainstorm a good question idea that can be answered with the selected sentences using the unique information you have identified. Ask for specific information from one of the sentences. Make sure that the correct answer is short and concise.]

Additional sentences:
[Check if the selected sentences are sufficient to write a self-contained question based on the defined criteria. If you believe you need additional sentence(s), for each additional sentence justify your decision by stating the sentence id, the unique information from this sentence and why it is essential. If no additional sentence is needed, explain why the current selection is self-contained.]

Verification:
[Draft your question and verify points 4,5,6,7,8]

</scratchpad>

It is crucial that you adhere to the following criteria:
- Answering the question is only possible based on the unique information that can be found in the selected sentences.
- Answering the question requires combining the unique information from ALL selected sentences.
- The question is specific enough to allow only for one valid answer. There are no other interpretations based on the storyline outline which would allow for a different valid answer.
- The answer must be complete. 

Important reminders:
- The sentences describe part of a fictional event. Your questions must address the fictional event.
- Generate {{NUM_QUESTIONS}} multi-hop questions.
- Verify the generated questions based on the defined criteria and correct them if necessary.
- Make sure to be specific in the question when paraphrasing the bridge entity to avoid ambiguities. It must be clear to identify the bridge entity based on the details provided in the question.
- DO NOT ask for "specific" information verbatim. Instead, provide specific details in the question that can be answered with concrete values.
- While you must ask for very specific information, make sure the answer itself is a short and concise phrase!

Format your output as follows:

<scratchpad>
[Your thinking can go here.]
</scratchpad>
<results>
<qa>
<question>[Your generated question]</question>
<answer>[The answer based on the evidence sentences]</answer>
<additional_sentence_ids>[List of additional sentence IDs required to answer the question, if applicable]</additional_sentence_ids>
<additional_sentence_explanation>[Explain the unique information of each additional sentence that is required to answer the question and justify why it is needed, if applicable]</additional_sentence_explanation>
</qa>
</results>

Now, begin the task of generating question-answer pairs based on the provided sentences. Include all question-answer pairs within a single <results> tag.
"""


INSTRUCTIONS_V3 = """
You are an AI assistant tasked with analyzing two sentences about fictional events involving fictional named entities and generating multi-hop questions using a bridge entity. Your goal is to identify specific details within these sentences and create {{NUM_QUESTIONS}} question-answer pairs that require reasoning over both sentences.

First, familiarize yourself with the complete storyline outline of the fictional events:

<storyline_outline>
{{STORYLINE_OUTLINE_TO_DATE}}
</storyline_outline>

Now, focus on the two selected sentences based on which you must generate multi-hop questions:

<selected_sentences>
{{SELECTED_SENTENCES}}
</selected_sentences>

The bridge entity in these sentences is:

<bridge_entity>{{BRIDGE_ENTITY_NAME}}</bridge_entity>

To generate multi-hop questions that require reasoning over both sentences, follow these steps:

1. Identify information about the bridge entity in both sentences that is unique to these two sentences and cannot be found based on any other information from the provided storyline outline. This information should be as specific as possible, to avoid any ambiguities or overlap with other information from other sentences.

2. To generate a question-answer pair, ask for specific information about the bridge entity from one sentence while describing the bridge entity with information from the other sentence. Make sure that the correct answer is concise and factual. The answer should focus on very specific details that can be described in few words. 

3. Do not mention the bridge entity explicitly in your questions.

4. Ensure that the question can ONLY be answered when having access to the information from BOTH sentences. Make sure that all selected sentences must be considered to answer the question. Avoid using the bridge entity itself as the answer.

5. Ensure that the information that is required from each sentence is unique within this sentence: It can neither be inferred nor extracted from any other sentence within the provided storyline outline. If the question can be answered based on the other information from the storyline outline, increase the specificity of the required details and ensure they are unique to the selected sentences.

6. Try to add some additional complexities that make the question more challenging while keeping the question about specific factual details. Make sure that the question remains specific and valid, and that the required information to answer the question is unique to the selected sentences. While adding complexities, make sure that the answer remains short, concise and focused on specific details.

It is crucial that you adhere to the following criteria:
- Answering the question is only possible based on the unique information that can be found in the selected sentences.
- Answering the question requires combining the unique information from ALL selected sentences.
- The question is specific enough to allow only for one valid answer. There are no other interpretations based on the storyline outline which would allow for a different valid answer.
- The answer must be complete. 

Important reminders:
- The sentences describe part of a fictional event. Your questions must address the fictional event.
- Generate {{NUM_QUESTIONS}} multi-hop questions.
- Verify the generated questions based on the defined criteria and correct them if necessary.
- Make sure to be specific in the question when paraphrasing the bridge entity to avoid ambiguities. It must be clear to identify the bridge entity based on the details provided in the question.
- Avoid referring to any of the fictional named entities by name in the question if possible.
- DO NOT ask for "specific" information verbatim. Instead, provide specific details in the question that can be answered with concrete values.

Format your output as follows:

<scratchpad>
[Your thinking can go here.]
</scratchpad>
<results>
<qa>
<question>[Your generated question]</question>
<answer>[The answer based on the evidence sentences]</answer>
</qa>
</results>

Now, begin the task of generating question-answer pairs based on the provided sentences. Include all question-answer pairs within a single <results> tag.
"""


INSTRUCTIONS_V2 = """
You are an AI assistant tasked with analyzing two sentences about fictional events involving fictional named entities and generating multi-hop questions using a bridge entity. Your goal is to identify specific details within these sentences and create {{NUM_QUESTIONS}} question-answer pairs that require reasoning over both sentences.

First, review the known knowledge base entries about the fictional named entities:

<known-named-entities>
{{KNOWN_PREV_NAMED_ENTITIES}}
</known-named-entities>

Next, familiarize yourself with the complete other sentences about the fictional events:

<events>
{{STORYLINE_OUTLINE_TO_DATE}}
</events>

Now, focus on the two selected sentences based on which you must generate multi-hop questions:

<selected_sentences>
{{SELECTED_SENTENCES}}
</selected_sentences>

The bridge entity in these sentences is:

<bridge_entity>{{BRIDGE_ENTITY_NAME}}</bridge_entity>

To generate multi-hop questions that require reasoning over both sentences, follow these steps:

1. Identify information about the bridge entity in both sentences that is distinct from information in the knowledge base entries and other information from the fictional events.
2. Ask for specific information about the bridge entity from one sentence while describing the bridge entity with information from the other sentence. The question should be answerable with only a word or short phrase.
3. Do not mention the bridge entity explicitly in your questions.
4. Ensure that the question can ONLY be answered when having access to the information from BOTH sentences.
5. Add complexity to the reasoning by replacing specific details with more general information, such that lexical similarity is not sufficient.

It is crucial that you adhere to the following criteria:
- None of the other sentences from the fictional events can replace one of the provided sentences to answer the question.
- None of the other sentences from the fictional events changes the validity of the question-answer pair.
- None of the other sentences from the fictional events introduces a different valid answer.
- The correct answer to your questions can only be found based on the two provided sentences. Having access to the additional context should not make the task easier or provide alternative answers.

Important reminders:
- The sentences describe part of a fictional event. Your questions must address the fictional event.
- Generate {{NUM_QUESTIONS}} multi-hop questions.
- Verify the generated questions based on the defined criteria and correct them if necessary.
- Make sure to be specific in the question when paraphrasing the bridge entity to avoid ambiguities. It must be clear to identify the bridge entity based on the details provided in the question.
- Avoid referring to any of the fictional named entities by name in the question if possible.
- DO NOT ask for "specific" information verbatim. Instead, provide specific details in the question that can be answered with concrete values.

Format your output as follows:

<scratchpad>
[Your thinking can go here.]
</scratchpad>
<results>
<qa>
<question>[Your generated question]</question>
<answer>[The answer based on the evidence sentences]</answer>
</qa>
</results>

Now, begin the task of generating question-answer pairs based on the provided sentences. Include all question-answer pairs within a single <results> tag. Aim to generate at least 3 diverse question-answer pairs.
"""



INSTRUCTIONS_V1 = """
You are an AI assistant tasked with analyzing two sentences about fictional events involving fictional named entities and generating multi-hop questions using a bridge entity. Your goal is to identify specific details within these sentences and create {{NUM_QUESTIONS}} question-answer pairs that require reasoning over both sentences.

First, review the known knowledge base entries about the fictional named entities:

<known-named-entities>
{{KNOWN_PREV_NAMED_ENTITIES}}
</known-named-entities>

Next, familiarize yourself with the complete other sentences about the fictional events:

<events>
{{STORYLINE_OUTLINE_TO_DATE}}
</events>

Now, focus on the two selected sentences based on which you must generate multi-hop questions:

<selected_sentences>
{{SELECTED_SENTENCES}}
</selected_sentences>

The bridge entity in these sentences is:

<bridge_entity>{{BRIDGE_ENTITY_NAME}}</bridge_entity>

To generate multi-hop questions that require reasoning over both sentences, follow these steps:

1. Identify information about the bridge entity in both sentences that is distinct from information in the knowledge base entries and other information from the fictional events.
2. Ask for specific information about the bridge entity from one sentence while describing the bridge entity with information from the other sentence. The question should be answerable with only a word or short phrase.
3. Do not mention the bridge entity explicitly in your questions.
4. Ensure that the question can ONLY be answered when having access to the information from BOTH sentences.
5. Add complexity to the reasoning by replacing specific details with more general information, such that lexical similarity is not sufficient.

It is crucial that you adhere to the following criteria:
- None of the other sentences from the fictional events can replace one of the provided sentences to answer the question.
- None of the other sentences from the fictional events changes the validity of the question-answer pair.
- None of the other sentences from the fictional events introduces a different valid answer.
- The correct answer to your questions can only be found based on the two provided sentences. Having access to the additional context should not make the task easier or provide alternative answers.

Important reminders:
- The sentences describe part of a fictional event. Your questions must address the fictional event.
- Generate {{NUM_QUESTIONS}} multi-hop questions.
- Verify the generated questions based on the defined criteria and correct them if necessary.
- Make sure to be specific in the question when paraphrasing the bridge entity to avoid ambiguities. It must be clear to identify the bridge entity based on the details provided in the question.
- Avoid referring to any of the fictional named entities by name in the question if possible.
- DO NOT ask for "specific" information verbatim. Instead, provide specific details in the question that can be answered with concrete values.

Format your output as follows:

<scratchpad>
[Your thinking can go here.]
</scratchpad>
<results>
<qa>
<question>[Your generated question]</question>
<answer>[The answer based on the evidence sentences]</answer>
</qa>
</results>

Now, begin the task of generating question-answer pairs based on the provided sentences. Include all question-answer pairs within a single <results> tag. Aim to generate at least 3 diverse question-answer pairs.
"""

