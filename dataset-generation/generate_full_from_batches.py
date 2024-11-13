"""
Usage:
  generate_full_from_batches.py <batch_name>

Options:
  -h --help     Show this screen.
  --version     Show version.
"""
import os
from os import listdir
from os.path import exists, join, dirname
from docopt import docopt
from generate_news_articles import create_articles
from generate_questions_bridge_entity import generate_multi_hop_bridge_questions
from generate_questions_timespan import generate_time_span_questions
from generate_story_lines import generate_storylines_for
from data_gen.util.file_util import read_jsonl
from data_gen.util.sanitize import fix_named_entity_names


def get_full_outline(summary, base_directory: str):
    file = summary['story_seed_id'].replace(' ', '-').replace(':', '_')
    directory = f'{base_directory}/{file}'
    if not exists(directory):
        return None
    children = [
        d for d in listdir(directory) if d not in ['news', 'questions']
    ]
    if len(children) == 0:
        return None
    else:
        exported_path: str = join(directory, f'{children[0]}/EXPORT_it-10.json')
        if exists(join(directory, f'{children[0]}/EXPORT_it-10.json')):
            return join(directory, f'{children[0]}')
        else:
            return None


def multi_hop_questions_exist(storyline_parent_dir: str) -> bool:
    return exists(join(storyline_parent_dir, f'questions/multiv2-bridge-series.json'))


def timespan_questions_exist(storyline_parent_dir: str) -> bool:
    return exists(join(storyline_parent_dir, f'questions/timespan-questions_v2complete.json'))


def news_exist(storyline_parent_dir: str) -> bool:
    return exists(join(storyline_parent_dir, f'news/news-articles.json'))


def run(batch_name: str, llm_name: str):

    summaries = read_jsonl(f'outputs/seed-batches/{batch_name}')
    for i, summary in enumerate(summaries):
        try:
            storyline_directory: str = get_full_outline(summary, 'outputs/storylines-final4')
            if storyline_directory is None:
                storyline_directory = generate_storylines_for(summary, 'storylines-final4', llm_name)

            storyline_path: str = join(storyline_directory, 'EXPORT_it-10.json')
            fix_named_entity_names(storyline_path, llm_name)

            storyline_base_dir: str = dirname(storyline_path)
            storyline_parent_dir: str = dirname(storyline_directory)
            if not timespan_questions_exist(storyline_parent_dir):
                generate_time_span_questions([storyline_base_dir], llm_name, max_num_evidence_selections=2)
            if not multi_hop_questions_exist(storyline_parent_dir):
                generate_multi_hop_bridge_questions([storyline_base_dir], llm_name, sample_num_entities=True, max_entities_per_selection=2)
            if not news_exist(storyline_parent_dir):
                create_articles(storyline_parent_dir, llm_name)
        except Exception as err:
            raise err


def main(args):

    batch_name: str = args['<batch_name>']
    run(batch_name, 'gpt4-o')


if __name__ == '__main__':
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    os.environ["AWS_PROFILE"] = "llmexp"
    arguments = docopt(__doc__, version='1.0')
    main(arguments)
