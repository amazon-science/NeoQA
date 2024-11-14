from typing import List, Dict, Optional, Set

from src.mglockne_story_line.llm.critiques.base_critique import BaseCritique
from src.mglockne_story_line.llm.critiques.critique_result import CritiqueResult
from src.mglockne_story_line.llm.critiques.modules.output_format_critique import OutputFormatCritique
from src.mglockne_story_line.llm.modules.parsable_base_module import ParsableBaseModule
from src.mglockne_story_line.llm.prompting.modules.nested_parsable_output_prompt import BasicNestedXMLParser
from src.mglockne_story_line.llm.prompting.parsable_prompt import ParsablePrompt
from src.mglockne_story_line.llm.wrapper.base_llm_wrapper import BaseLLMWrapper
from src.mglockne_story_line.questions.question_generator import QuestionGenerator

EXPECTED_OUTPUT_FORMAT: str = """
<result>
<scratchpad>
[Your reasoning and sentence numbering here]
</scratchpad>

<selection>
<ids>[ID of the first selected sentence (comma separated)]</ids>
<explanation>[Explanation]</explanation>
</selection>
[... repeat for the number of spans requested ...]
</result>
""".strip()



class DiverseEventsCritique(BaseCritique):
    def __init__(self, name: str, num_hops: int = 2):
        super().__init__(name)
        self.num_hops: int = num_hops

    def to_error_string(self, item: Dict):
        raise NotImplementedError

    def process(self, values: Dict) -> CritiqueResult:
        need_distinct_events: int = min([self.num_hops, len(values['SELECTED_EVENTS'])])
        errors: List[Dict] = []
        conflict_message: str = f"The selected sentence IDs must cover {need_distinct_events} distinct events. However, the current selection covers fewer events:\n"
        for selection in values['selected_sentence_ids']:
            event_ids: Set[str] = {sent_id.split('-')[0].strip() for sent_id in selection['ids'].split(',')}
            if len(event_ids) < need_distinct_events:
                errors.append({
                    'selection': selection,
                    'has_events': len(event_ids),
                    'need_events': need_distinct_events
                })
                conflict_message += f'\t- {selection["ids"]}\n'
        self.add_errors_to_result(values, errors)
        return CritiqueResult(
            self.name,
            len(errors) == 0,
            errors,
            conflict_message
        )


class SameNamedEntityCritique(BaseCritique):
    def __init__(self, name: str):
        super().__init__(name)

    def to_error_string(self, item: Dict):
        raise NotImplementedError

    def process(self, values: Dict) -> CritiqueResult:

        errors: List[Dict] = []
        conflict_message: str = f'Only select sentence IDs from this list: {values["POSSIBLE_SENTENCE_IDS"]}. The following selections include other sentences:\n'
        for selection in values['selected_sentence_ids']:
            sent_ids: List[str] = [sent_id.strip() for sent_id  in selection['ids'].split(',')]

            is_valid: bool = True
            for event_id in sent_ids:
                if event_id not in values['POSSIBLE_SENTENCE_IDS_LIST']:
                    is_valid = False

            if not is_valid:
                conflict_message += f'\t- {selection}\n'
                errors.append({
                    'sent_ids': sent_ids,
                    'allowed': values['POSSIBLE_SENTENCE_IDS_LIST']
                })

        self.add_errors_to_result(values, errors)
        return CritiqueResult(
            self.name,
            len(errors) == 0,
            errors,
            conflict_message
        )


class MultiEventBridgeEntitySentenceSelectionModule(ParsableBaseModule):

    def _postprocess_values(self, values: Dict) -> Optional[Dict]:
        # Assert nums
        selections: List[Dict] = []
        for selection in values['selected_sentence_ids']:
            selected_sentences: List[str] = [
                sent_id.strip() for sent_id in selection['ids'].split(',') if len(sent_id.strip()) > 0
            ]
            assert len(set(selected_sentences)) == self.num_sentences, selected_sentences
            selections.append({
                'sentence_ids': selected_sentences,
                'explanation': selection.get('explanation', '')
            })

        values[QuestionGenerator.VAL_SELECTIONS] = selections[:self.max_num_selections]
        return values

    def __init__(self, llm: BaseLLMWrapper, name: str, instruction_name: str, max_num_selections: int, num_sentences: int = 2):
        super().__init__(
            llm,
            name,
            instruction_name,
            get_instructions(instruction_name),
        )
        self.max_num_selections: int = max_num_selections
        self.num_sentences: int  = num_sentences

    def _create_critiques(self) -> List[BaseCritique]:
        return [
            DiverseEventsCritique('ensure-distinct-events'),
            SameNamedEntityCritique('ensure-sentence-subset')
        ]

    def _create_formatting_critique(self, parsers: List[BasicNestedXMLParser]) -> Optional[BaseCritique]:
        return OutputFormatCritique('format-select-specifics', parsers, EXPECTED_OUTPUT_FORMAT)

    def _preprocess_values(self, values) -> Dict:

        possible_sentence_ids: List[str] = []
        entity_id: str = values['BRIDGE_ENTITY_ID']
        for event in values['SELECTED_EVENTS']:
            possible_sentence_ids.extend(event['entity_id_to_outline_ids'][entity_id])
        assert len(possible_sentence_ids) >= 2

        sentence_id_str: str = ', '.join(possible_sentence_ids)
        values = values | {
            'MAX_NUMBER_SELECTIONS': self.max_num_selections,
            'POSSIBLE_SENTENCE_IDS': sentence_id_str,
            'POSSIBLE_SENTENCE_IDS_LIST': possible_sentence_ids,
        }
        return values

    def _get_parsers(self) -> List[BasicNestedXMLParser]:
        return [
            BasicNestedXMLParser('selected_sentence_ids', './/selection', is_object=True, allow_empty_list=False, result_node='result')
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
You are an AI assistant tasked with analyzing fictional event descriptions and identifying sentences that can be used to generate multi-hop questions with a bridge entity. Your goal is to find up to {{MAX_NUMBER_SELECTIONS}} tuples, each comprising 2 sentences, that can be used to create challenging and interesting multi-hop questions with a bridge entity.

Here are the key inputs for this task:

1. Fictional events to analyze:
<events>
{{OUTLINES}}
</events>

2. The bridge entity name for this task:
<bridge_entity>
{{BRIDGE_ENTITY_NAME}}
</bridge_entity>

3. Known named entities:
<known-named-entities>
{{KNOWN_PREV_NAMED_ENTITIES}}
</known-named-entities>

4. List of sentence IDs that include the bridge entity:
<possible_sentence_ids>
{{POSSIBLE_SENTENCE_IDS}}
</possible_sentence_ids>

When selecting sentences, follow these guidelines:
1. If two events are provided, ensure that each tuple covers both events (i.e., one sentence ID stems from the first event, and the other sentence ID stems from the second event).
2. If only one event is provided, the selected sentence IDs can stem from the same event.
3. Look for diverse combinations of sentences across the selected events.
4. Only consider sentence IDs from the provided list of possible sentence IDs.
5. Ensure that ALL selected sentence IDs include the bridge named entity.
6. Make sure that the specific information needed to identify the bridge entity cannot be known from any other sentence, nor from the knowledge base entries from the known named entities.
7. Verify that the information from the known named entities is not sufficient to replace the detailed information found in the selected sentences.

Before providing your final answer, use a <scratchpad> section to analyze the events and think through potential sentence combinations. This will help you identify the most suitable pairs for multi-hop questions. In your scratchpad, consider the following:
1. Identify sentences that contain specific information about the bridge entity.
2. Look for connections between sentences that could form the basis of a multi-hop question.
3. Evaluate whether the selected sentences provide unique information not available in other sentences or known named entities.
4. Consider how the sentences could be used to create a challenging and interesting question.

For each suitable combination of sentences you find, output your selection using this format:

<selection>
<ids>[IDs of the selected sentences (comma separated)]</ids>
<explanation>[Explanation of why these sentences are suitable for generating a multi-hop question with the given bridge entity]</explanation>
</selection>

Try to find as many interesting combinations of sentences as possible, but do not exceed {{MAX_NUMBER_SELECTIONS}} selections.

If you cannot find any meaningful combination of sentences based on which good multi-hop questions with this bridge entity can be generated, return an empty list.

Wrap all your results, including the scratchpad and selections, in a <result> root node. Your final output should look like this:

<result>
<scratchpad>
[Your analysis and thought process]
</scratchpad>

[Your selections, if any]

</result>

Remember, the goal is to identify sentence pairs that can be used to create challenging and interesting multi-hop questions with the given bridge entity. Focus on finding unique and specific information that requires reasoning over both sentences to answer a potential question.
"""