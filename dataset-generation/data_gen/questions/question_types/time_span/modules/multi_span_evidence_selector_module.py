import re
from typing import List, Dict, Optional, Set

from data_gen.llm.critiques.base_critique import BaseCritique
from data_gen.llm.critiques.critique_result import CritiqueResult
from data_gen.llm.critiques.output_format_critique import OutputFormatCritique
from data_gen.llm.modules.parsable_base_module import ParsableBaseModule
from data_gen.llm.prompting.modules.nested_parsable_output_prompt import BasicNestedXMLParser
from data_gen.llm.prompting.parsable_prompt import ParsablePrompt
from data_gen.llm.wrapper.base_llm_wrapper import BaseLLMWrapper
from data_gen.questions.question_generator import QuestionGenerator

EXPECTED_OUTPUT_FORMAT: str = """
<result>
<scratchpad>
[Your reasoning and sentence numbering here]
</scratchpad>

<time-span>
<ids>[ID of the first selected sentence (comma separated)]</ids>
<explanation>[Explanation]</explanation>
</time-span>
[... repeat for the number of spans requested ...]
</result>

If you cannot identify a meaningful pair of sentences to derive specific points, try to find sentences where specific points can be derived under certain assumptions, or those that are very specific to a particular moment in time (such as the event date).
""".strip()


class DistinctSentencesCritique(BaseCritique):
    def __init__(self, name: str):
        super().__init__(name)

    def to_error_string(self, item: Dict):
        raise NotImplementedError

    def process(self, values: Dict) -> CritiqueResult:
        need_distinct_sentences: int = values['NUM_SENTENCES']

        errors: List[Dict] = []
        conflict_message: str = f"Each selection must include at least {need_distinct_sentences} unique sentence IDs. Please double-check the following selections:\n"
        for selection in values['selected_sentence_ids']:
            current_selection_ids: List[str] = [
                _id.strip() for _id in selection['ids'].split(",") if len(_id.strip()) > 0
            ]
            num_different_sentence_ids: int = len(set(current_selection_ids))
            print(len(set(selection['ids'])))
            if num_different_sentence_ids < need_distinct_sentences:
                errors.append({
                    'selection': selection,
                })
                conflict_message += f'\t- {selection["ids"]}\n'
        self.add_errors_to_result(values, errors)
        return CritiqueResult(
            self.name,
            len(errors) == 0,
            errors,
            conflict_message
        )


class EnsureCorrectSentenceIDCritique(BaseCritique):
    def __init__(self, name: str):
        super().__init__(name)

    def process(self, values: Dict) -> CritiqueResult:
        selections: List[Dict] = values['selected_sentence_ids']
        errors: List[Dict] = []
        for selection in selections:
            for sent_id in selection['ids'].split(','):
                sent_id = sent_id.strip()
                if len(sent_id) > 0:
                    if not re.match(r'^N[0-9]{1,2}-S[0-9]{1,2}$', sent_id):
                        errors.append({'id': sent_id})

        if len(errors) > 0:
            need_distinct_events: int = min([values['NUM_SENTENCES'], len(values['SELECTED_EVENTS'])])
            num_sents: int = values['NUM_SENTENCES']
            error_msg: str = f"Not all selected IDs correspond to valid sentence IDs. Ensure that each sentence pair contains {num_sents} valid sentence IDs from {need_distinct_events} distinct events. I identified the following issues, which were selected as sentence IDs:"
            for error in errors:
                error_msg += f'\n\t- "{error["id"]}"'

            return CritiqueResult(
                self.name, False, errors, error_msg
            )

        return CritiqueResult.correct(self.name)


class DiverseEventsCritique(BaseCritique):
    def __init__(self, name: str):
        super().__init__(name)

    def to_error_string(self, item: Dict):
        raise NotImplementedError

    def process(self, values: Dict) -> CritiqueResult:
        need_distinct_events: int = min([values['NUM_SENTENCES'], len(values['SELECTED_EVENTS'])])
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

        conflict_message += f'\nMake sure that each sentence pair covers {need_distinct_events} distinct events.'
        self.add_errors_to_result(values, errors)
        return CritiqueResult(
            self.name,
            len(errors) == 0,
            errors,
            conflict_message
        )


class MultiEventTimeSpanSelectorModule(ParsableBaseModule):

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

        values[QuestionGenerator.VAL_SELECTIONS] = selections
        return values

    def __init__(self, llm: BaseLLMWrapper, name: str, instruction_name: str, max_num_evidence_selections: int, num_sentences: int = 2):
        super().__init__(
            llm,
            name,
            instruction_name,
            get_instructions(instruction_name),
        )
        self.max_num_evidence_selections: int = max_num_evidence_selections
        self.num_sentences: int  = num_sentences

    def _create_critiques(self) -> List[BaseCritique]:
        return [
            DiverseEventsCritique('ensure-distinct-events'),
            DistinctSentencesCritique('ensure-distinct-sentences'),
            EnsureCorrectSentenceIDCritique('ensure-valid-sentence-id')
        ]

    def _create_formatting_critique(self, parsers: List[BasicNestedXMLParser]) -> Optional[BaseCritique]:
        return OutputFormatCritique('format-select-specifics', parsers, EXPECTED_OUTPUT_FORMAT)

    def _preprocess_values(self, values) -> Dict:
        values = values | {
            'NUM_SPANS': self.max_num_evidence_selections,
            'NUM_SENTENCES': self.num_sentences
        }
        return values

    def _get_parsers(self) -> List[BasicNestedXMLParser]:
        return [
            BasicNestedXMLParser('selected_sentence_ids', './/time-span', is_object=True, allow_empty_list=False, result_node='result', remove_node='scratchpad')
        ]

    def get_file_name(self, prompt: ParsablePrompt, values: Dict):
        node_idx: int = values['CREATED_AT']
        return f'N{node_idx:02d}-{self.name}_{self.instruction_name}.json'


def get_instructions(version: str) -> str:

    if version == 'v1':
        out: str = INSTRUCTIONS_V1
    elif version == 'v2':
        out: str = INSTRUCTIONS_V2
    else:
        raise ValueError(version)
    return out.strip()

INSTRUCTIONS_V2 = """
You are an AI assistant tasked with analyzing fictional event descriptions and identifying sentences that can be used to derive time spans. Your goal is to find up to {{NUM_SPANS}} tuples, each comprising {{NUM_SENTENCES}} sentences, that can be used to compute meaningful time spans.

Here are the outlines of the events you will be analyzing:

<events>
{{OUTLINES}}
</events>

To identify specific points in time from different sentences, consider the following:
1. Sentences mentioning relative time differences (e.g., "six weeks ago", "in five days", "after two hours"). Try to determine the specific date or time they refer to based on the context.
2. Sentences mentioning a specific date or time (e.g., "10:00 am", "March 22nd").
3. Sentences containing specific details unique to the current event.

Your task is to select tuples of NUM_SENTENCES sentences from which you can derive two specific points in time and compute a meaningful time span (duration). Follow these guidelines:
- The duration should be computed between comparable units.
- It must be possible to compute a specific time span between the two points in time.
- Prioritize sentences containing relative time differences for which you can compute a specific point in time.
- If possible, include sentences that mention a specific point in time explicitly.
- If neither of the above is possible, you may select sentences that rely only on the date of the events. However, it is preferred to collect sentences that introduce novel time information.

If multiple events are provided, the sentences must come from different events. If only one event is provided, the sentences can come from the same event.
Remember: It should be possible to compute a duration based on different specific points in time from the different selected sentence. DO NOT collect sentences based on which you can compare the ratio of different explicitly mentioned durations! Only select sentences based on which you can compute a meaningful absolute duration.

Use a <scratchpad> to plan your approach before outputting your final results. In your scratchpad, you can list potential sentence pairs, evaluate their suitability, and determine which ones to include in your final output.

For each tuple you identify, output the result in the following format:

<time-span>
<ids>[IDs of the selected sentences (comma separated)]</ids>
<explanation>[Explanation of how the time span can be computed from these sentences]</explanation>
</time-span>

Wrap all your results, including the scratchpad and time spans, in a <result> root node.

Example:
<result>
<scratchpad>
Potential pairs:
1. Sentences 2 and 5: Mention specific dates, can calculate exact duration.
2. Sentences 1 and 7: Relative time reference and specific time, need to infer exact start point.
3. Sentences 3 and 8: Both mention specific times on the same day, can calculate duration.

Decision: Include pairs 1 and 3 in the output.
</scratchpad>

<time-span>
<ids>2, 5</ids>
<explanation>Sentence 2 mentions the event starting on July 1st, while sentence 5 states it ended on July 15th. We can calculate a time span of 14 days between these two dates.</explanation>
</time-span>

<time-span>
<ids>3, 8</ids>
<explanation>Sentence 3 mentions a meeting at 9:00 AM, while sentence 8 refers to a conclusion at 4:30 PM on the same day. We can calculate a time span of 7 hours and 30 minutes between these two points.</explanation>
</time-span>
</result>

Remember to analyze the given event outlines carefully, identify suitable sentence pairs, and provide clear explanations for each time span you derive. If you cannot find the required number of valid time spans, include as many as you can identify from the given information.
"""


INSTRUCTIONS_V1 = """
You are an AI assistant tasked with analyzing fictional event descriptions and identifying sentences that can be used to derive time spans. Your goal is to find {{NUM_SPANS}} tuples, each comprising {{NUM_SENTENCES}} sentences, that can be used to compute meaningful time spans within the events' chronology.

Here are the outlines of the events:

<events>
{{OUTLINES}}
</events>

To complete this task, follow these steps:

1. Begin by using a <scratchpad> to analyze the events. Number each sentence in the event descriptions for easy reference. Consider sentences that describe:
   a) Absolute dates
   b) Relative time spans in relation to the date of the fictional events themselves (e.g., "Something happened three days ago")

In your <scratchpad>, explain your thought process for selecting sentences and creating time span tuples. Focus on identifying meaningful and diverse time spans that provide insight into the chronology of the events described.

2. After your analysis, generate {{NUM_SPANS}} tuples of {{NUM_SENTENCES}} sentences each that can be used to compute time spans. Follow these guidelines:
   a) Scatter the selected sentences within each tuple across all provided events.
   b) If more than one event is provided, the sentences within each tuple MUST come from different events.
   c) Choose sentences that offer a diverse range of time spans across the events' timeline.

3. For each time span tuple, provide a brief explanation describing why you chose those sentences and what time span can be derived from them.

4. Each sentence ID is structured as "[event-id]-[item-id]". Use this information to double-check that each tuple contains sentences from different events (with different event-ids).

5. Output each tuple in the following format:

<time-span>
<ids>[IDs of the selected sentences (comma separated)]</ids>
<explanation>[Explanation]</explanation>
</time-span>

6. Wrap all your results, including the scratchpad and time spans, in a <result> root node.

Remember:
- Time spans could concern months, days, hours, etc.
- Focus on time spans that are concrete enough to be computed to a reasonable degree. For example, comparing multiple years with a few days difference is not meaningful.
- Make sure to include your <scratchpad> analysis within the <result> tags, before the time-span tuples.
- Focus on meaningful time spans that provide insight into the chronology of the events described in the fictional events. 
- Within each tuple, the selected sentence IDs must stem from different events. 

Begin your analysis and provide your results within <result> tags.
"""
