from os import makedirs
from os.path import join, dirname
from typing import Dict, List

from src.mglockne_story_line.questions.question_generator import QuestionGenerator
from src.mglockne_story_line.util.file_util import read_json, store_json


def generate_questions(
    generator: QuestionGenerator,
    storyline_directories: List[str],
    storyline_file_name: str = 'EXPORT_it-10.json',
    values: Dict = None
):
    for directory in storyline_directories:
        parent: str = dirname(directory)
        storyline: Dict = read_json(join(directory, storyline_file_name))
        current_question_directory: str = join(parent, 'questions')
        makedirs(current_question_directory, exist_ok=True)

        generated_qa_pairs = generator.generate(storyline, values)
        generated_qa_pairs['storyline'] = storyline
        generated_qa_pairs['storyline_file_path'] = join(directory, storyline_file_name)

        store_json(
            generated_qa_pairs,
            join(current_question_directory, f'{generator.get_file_name()}'), pretty=True
        )