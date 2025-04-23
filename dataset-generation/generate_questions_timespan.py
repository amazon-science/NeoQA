
from typing import List

from data_gen.llm.get_llm import get_llm
from data_gen.llm.modules.named_module_pipeline import NamedModulePipeline
from data_gen.llm.wrapper.base_llm_wrapper import BaseLLMWrapper
from data_gen.questions.generate_questions import generate_questions
from data_gen.questions.question_generator import QuestionGenerator
from data_gen.questions.question_types.time_span.modules.multi_span_evidence_selector_module import \
    MultiEventTimeSpanSelectorModule
from data_gen.questions.question_types.time_span.modules.time_span_distractor_module import \
    MultiEventTimeSpanDistractorGenerator
from data_gen.questions.question_types.time_span.modules.time_span_question_refine_module import \
    MultiEventTimeSpanQuestionRefineModule
from data_gen.questions.question_types.time_span.modules.time_span_question_write_module import \
    MultiEventTimeSpanQuestionModule
from data_gen.questions.question_types.time_span.time_span_question_generator import MultiEventTimeSpanQuestionGenerator


def generate_time_span_questions(
    storyline_directories: List[str],
    llm_name: str,
    max_num_evidence_selections: int = 3,  # otherwise we generate way too much
    num_distractors: int = 5
):

    llm_strict: BaseLLMWrapper = get_llm(llm_name, temperature=0.0, max_tokens=5000)

    question_generator: QuestionGenerator = MultiEventTimeSpanQuestionGenerator(
        'timespan-questions_v2complete',
        evidence_selection_module=NamedModulePipeline(
            [
                MultiEventTimeSpanSelectorModule(llm_strict, 'select-sentences', 'v2', max_num_evidence_selections=max_num_evidence_selections)
            ], 'select-timespan'
        ),
        question_answer_generation_module=NamedModulePipeline(
            [
                MultiEventTimeSpanQuestionModule(llm_strict, 'write-question', 'v4'),
                MultiEventTimeSpanQuestionRefineModule(llm_strict, 'refine-question', 'v2'),
            ], 'multi-event-timespan-questions', True
        ),
        validate_modules=[],
        question_refine_module=NamedModulePipeline(
            [
                MultiEventTimeSpanDistractorGenerator(llm_strict, 'make-distractors', 'v1')
            ], 'multi-event-distractors-timespan'
        ),
        question_revisers=[],
    )

    generate_questions(
        generator=question_generator,
        storyline_directories=storyline_directories,
        storyline_file_name='EXPORT_it-10.json',
        values={
            'NUM_DISTRACTORS': num_distractors  # How many distractors are generated per question
        }
    )
