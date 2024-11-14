import os
from collections import defaultdict
from os import listdir
from os.path import join, exists
from typing import Dict, List

from mglockne_story_line.util.file_util import read_jsonl, read_json


def get_full_outline(summary):
    file = summary['story_seed_id'].replace(' ', '-').replace(':', '_')
    directory = f'outputs/storylines-final2/{file}'
    if not exists(directory):
        return None
    children = [
        d for d in listdir(directory) if d not in ['news', 'questions']
    ]
    if len(children) == 0:
        return None
    else:
        if exists(join(directory, f'{children[0]}/EXPORT_it-10.json')):
            return join(directory, f'{children[0]}')
        else:
            return None



def process_summary(summary: Dict):
    storyline_directory: str = get_full_outline(summary)
    news_status = 0
    timespan_status: str = None
    multihop_status = None
    multihop_num = 0
    has_storyline = storyline_directory is not None
    if has_storyline:
        directory = '/'.join(storyline_directory.split('/')[:3])

        # Check news
        if exists(join(directory, f'news/news-articles.json')):
            articles = read_json(join(directory, f'news/news-articles.json'))
            have_newspaper = {
                article['news_profile']
                for key in articles['articles']
                for article in articles['articles'][key]
            }
            news_status = len(have_newspaper)

        # Timespan question
        timespan_path: str = join(directory, f'questions/timespan-questions_v2complete.json')
        if exists(timespan_path):
            timespan_questions = read_json(timespan_path)
            if 'use_decoded' in timespan_questions['questions'][0]['misc']:
                timespan_status = 'corrected'
            else:
                timespan_status = 'noisy'


        multi_hop_questions_path = join(directory, f'questions/multiv2-bridge-series.json')
        if exists(multi_hop_questions_path):
            multi_hop_questions = read_json(multi_hop_questions_path)
            multihop_num = len(multi_hop_questions['questions'])
            if 'use_decoded' in multi_hop_questions['questions'][0]['misc']:
                multihop_status = 'corrected'
            else:
                multihop_status = 'noisy'




    return {
        'news_status': news_status,
        'has_story': has_storyline,
        'timespan_status': timespan_status,
        'multihop_status': multihop_status,
        'multihop_num': multihop_num
    }





def main():
    seed_files = [
        'outputs/seed-summaries/exported/events1.jsonl',
        'outputs/seed-summaries/exported/events2.jsonl',
    ]

    seed_summaries = [{
        "genre": "Art",
        "summary": "A comprehensive survey of indigenous art from various cultures has been assembled, highlighting shared themes and artistic techniques across different regions and time periods.",
        "event_type": {
            "category": "Major Museum Exhibitions",
            "event_type_id": "art:custom0"
        },
        "event_type_id": "art:custom0",
        "story_seed_id": "art:custom0:9",
        "init_random_seed": 216306
    }] + [
        summary for file in seed_files for summary in read_jsonl(file)
    ]
    count = 0
    for summary in seed_summaries:
        status = process_summary(summary)
        # This should be finished with the correction-v1
        if status['has_story'] and status['multihop_status'] is not None and status['timespan_status'] is not None:
            print(summary['summary'])
            print(f'News: {status["news_status"]}')
            print('Timespan:', status['timespan_status'])
            print('Multi-Hop:', status['multihop_status'])
            print('Multi-Hop Nunm:', status['multihop_num'])
            print('--\n')

        # Check

        # Copy if final!

        # Starting all futures: in next directory

    print(count)
    pass


if __name__ == "__main__":
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    os.environ["AWS_PROFILE"] = "llmexp"
    main()