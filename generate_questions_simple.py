import os
from os import listdir
from os.path import join
from typing import List, Dict

from src.mglockne_story_line.llm.modules.named_module_pipeline import NamedModulePipeline
from src.mglockne_story_line.llm.wrapper.base_llm_wrapper import BaseLLMWrapper
from src.mglockne_story_line.llm.wrapper.models.claude_wrapper import ClaudeWrapper
from src.mglockne_story_line.questions.generate_questions import generate_questions
from src.mglockne_story_line.questions.question_generator import QuestionGenerator
from src.mglockne_story_line.questions.question_types.basic_questions.modules.simple_question_distractor_module import \
    SimpleQuestionDistractorModule
from src.mglockne_story_line.questions.question_types.basic_questions.modules.simple_question_sentence_selection_module import \
    SimpleQuestionSentenceSelectionModule
from src.mglockne_story_line.questions.question_types.basic_questions.modules.simple_question_write_module import \
    SimpleQuestionWriteModule
from src.mglockne_story_line.questions.question_types.basic_questions.single_event_single_hop_question_generator import \
    SingleEventQuestionGenerator
from src.mglockne_story_line.util.story_tools import get_outline_directory_from_story_path, \
    get_all_storyline_directories


def generate_simple_questions(
        storyline_directories: List[str],
        num_sentences_selected_per_event: int = 5,
        num_question_per_evidence: int = 1
):
    llm_strict: BaseLLMWrapper = ClaudeWrapper(temperature=0.0, max_tokens=8000, model_version='3.5')

    question_generator: QuestionGenerator = SingleEventQuestionGenerator(
        f'simple-questions-v1-select_{num_sentences_selected_per_event}-{num_question_per_evidence}',
        evidence_selection_module=NamedModulePipeline(
            [
                SimpleQuestionSentenceSelectionModule(
                    llm_strict, 'select', 'v1'
                )
            ], 'select-specifics'
        ),
        question_answer_generation_module=NamedModulePipeline(
            [
                SimpleQuestionWriteModule(llm_strict, 'create-question', 'v3'),
            ], 'single-event-single-hop-questions'
        ),
        validate_modules=[],
        question_refine_module=NamedModulePipeline(
            [
                SimpleQuestionDistractorModule(llm_strict, 'create-distractors', 'v1')
            ], 'single-event-distractors'
        )
    )


    generate_questions(
        generator=question_generator,
        storyline_directories=storyline_directories,
        storyline_file_name='EXPORT_it-10.json',
        values={
            'NUM_ITEMS': num_sentences_selected_per_event,  # How many sentences are selected
            'NUM_QUESTIONS': num_question_per_evidence  # How many questions are generated per evidence
        }
    )



def main():
    storyline_root_dir: str = 'outputs/storylines-cont'
    storyline_directories: List[str] = list(get_all_storyline_directories(storyline_root_dir))
    generate_simple_questions(storyline_directories)


if __name__ == "__main__":
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    os.environ["AWS_PROFILE"] = "llmexp"
    main()