import os
from os.path import join, exists
from typing import List


from src.mglockne_story_line.llm.get_llm import get_llm
from src.mglockne_story_line.llm.modules.named_module_pipeline import NamedModulePipeline
from src.mglockne_story_line.llm.wrapper.base_llm_wrapper import BaseLLMWrapper
from src.mglockne_story_line.questions.generate_questions import generate_questions
from src.mglockne_story_line.questions.question_generator import QuestionGenerator
from src.mglockne_story_line.questions.question_types.time_span_questions.modules.multi_span_evidence_selector_module import \
    MultiEventTimeSpanSelectorModule
from src.mglockne_story_line.questions.question_types.time_span_questions.modules.time_span_distractor_module import \
    MultiEventTimeSpanDistractorGenerator
from src.mglockne_story_line.questions.question_types.time_span_questions.modules.time_span_question_refine_module import \
    MultiEventTimeSpanQuestionRefineModule
from src.mglockne_story_line.questions.question_types.time_span_questions.modules.time_span_question_write_module import \
    MultiEventTimeSpanQuestionModule
from src.mglockne_story_line.questions.question_types.time_span_questions.time_span_question_generator import \
    MultiEventTimeSpanQuestionGenerator
from src.mglockne_story_line.util.story_tools import get_all_storyline_directories



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
        question_revisers=[
            # ContradictoryFalsePremiseReviser(
            #     llm_strict, 'contradictory-false-premise', 'v1', 'contradictory'
            # ),
            # UncertainFalsePremiseReviser(
            #     llm_strict, 'uncertain-false-premise', 'v1', 'uncertain-specificity'
            # )
        ],
    )


    generate_questions(
        generator=question_generator,
        storyline_directories=storyline_directories,
        storyline_file_name='EXPORT_it-10.json',
        values={
            'NUM_DISTRACTORS': num_distractors  # How many distractors are generated per question
        }
    )




def main():
    storyline_root_dir: str = 'outputs/storylines-final2'
    storyline_directories: List[str] = sorted(list(get_all_storyline_directories(storyline_root_dir)))

    # Use this to generate questions for all storylines
    storyline_directories = [
        d for d in storyline_directories
        if exists(join(d, 'EXPORT_it-10.json')) and exists(join('/'.join(d.split('/')[:-1]), 'news/news-articles.json'))
    ]
    # for d in os.listdir('outputs/storylines-final2'):
    #     if ex
    #generate_time_span_questions(storyline_directories)
    for d in storyline_directories:
        generate_time_span_questions([d])


    pass


if __name__ == "__main__":
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    os.environ["AWS_PROFILE"] = "llmexp"
    main()