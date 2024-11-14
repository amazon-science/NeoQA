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
from typing import Dict, List, Optional

from docopt import docopt

from export_final_dataset import get_complete_storyline_if_exists, get_complete_questions_if_exist, \
    get_complete_news_articles_if_exist
from generate_news_articles import create_articles
from generate_questions_bridge_entity import generate_multi_hop_bridge_questions
from generate_questions_timespan import generate_time_span_questions
from generate_story_lines import generate_storylines_for



from src.mglockne_story_line.util.file_util import read_jsonl
from src.mglockne_story_line.util.sanitize import fix_named_entity_names


def get_all_storylines_without_questions_or_articles(directory: str) -> List[str]:
    outputs: List[str] = []
    for story_directory in sorted(listdir(directory)):
        storyline: Optional[Dict] = get_complete_storyline_if_exists(join(directory, story_directory))
        questions: Optional[Dict] = get_complete_questions_if_exist(join(directory, story_directory))
        # This could be improved to filter for the cleaned evidence documents.
        news_articles: Optional[Dict] = get_complete_news_articles_if_exist(join(directory, story_directory))

        needs_processing: bool = questions is None or news_articles is None

        if storyline is not None and needs_processing:
            outputs.append(join(directory, story_directory))
    return outputs



def get_complete_storyline_path_if_exists(storyline_directory: str) -> Optional[str]:
    if not exists(storyline_directory):
        return None
    children = [
        d for d in listdir(storyline_directory) if d not in ['news', 'questions']
    ]
    if len(children) == 0:
        return None
    else:
        if exists(join(storyline_directory, f'{children[0]}/EXPORT_it-10.json')):
            return join(storyline_directory, f'{children[0]}/EXPORT_it-10.json')
        else:
            return None


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
    #summaries = read_jsonl(f'outputs/seed-summaries/exported/{batch_name}')
    for summary in summaries:
        try:
            storyline_directory: str= get_full_outline(summary, 'outputs/storylines-final4')
            if storyline_directory is None:
                storyline_directory = generate_storylines_for(summary, 'storylines-final4', llm_name)

            storyline_path: str = join(storyline_directory, 'EXPORT_it-10.json')
            fix_named_entity_names(storyline_path, llm_name)

            storyline_base_dir: str = dirname(storyline_path)
            storyline_parent_dir: str = dirname(storyline_directory)
            if not timespan_questions_exist(storyline_parent_dir):
                generate_time_span_questions([storyline_base_dir], llm_name)
            if not multi_hop_questions_exist(storyline_parent_dir):
                generate_multi_hop_bridge_questions([storyline_base_dir], llm_name)
            if not news_exist(storyline_parent_dir):
                directory = '/'.join(storyline_directory.split('/')[:3])
                create_articles(directory, llm_name)

        except Exception as err:
            print(err)




def main(args):

    batch_name: str = args['<batch_name>']
    #run(batch_name, 'claude-35')
    run(batch_name, 'gpt4-turbo')

if __name__ == '__main__':
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    os.environ["AWS_PROFILE"] = "llmexp"
    arguments = docopt(__doc__, version='1.0')
    main(arguments)
