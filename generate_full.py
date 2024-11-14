import os
from collections import defaultdict
from os import listdir
from os.path import join, exists
from typing import Dict, List


from generate_news_articles import create_articles
from generate_questions_bridge_entity import generate_multi_hop_bridge_questions
from generate_questions_simple import generate_simple_questions
from generate_questions_timespan import generate_time_span_questions
from generate_story_lines import generate_storylines
from src.mglockne_story_line.news.modules.write_news_article_module import EXPECTED_OUTPUT_FORMAT
from src.mglockne_story_line.util.file_util import read_json, read_jsonl
from generate_story_lines import generate_storylines_for
from src.mglockne_story_line.util.story_tools import get_outline_directory_from_story_path


def gen_articles():
    seed_summary_dir: str = 'outputs/seed-summaries'
    summaries: List[Dict] = [
        read_json(join(seed_summary_dir, file)) for file in sorted(
            os.listdir(seed_summary_dir)) if file.endswith('.json')
    ]
    event_type_ids = [0,1,2]
    summary_ids = [0,1,2]
    for summary_id in summary_ids:
        for event_type_id in event_type_ids:
            for i, genre_summaries in  enumerate(summaries):
                skip = False
                if i < 5 and event_type_id == 0 and summary_id == 0:

                    seed_summary = genre_summaries['events'][event_type_id]['summaries'][summary_id]
                    print(seed_summary)
                    file = seed_summary["story_seed_id"].replace(':', '_')
                    storyline_dir = get_outline_directory_from_story_path(f'outputs/storylines-cont/{file}__cs')
                    try:
                        for directory in [storyline_dir]:
                            directory = '/'.join(directory.split('/')[:3])
                            create_articles(directory)
                    except Exception as err:
                        print(err)


def gen_full():
    seed_summary_dir: str = 'outputs/seed-summaries'
    summaries: List[Dict] = [
        read_json(join(seed_summary_dir, file)) for file in sorted(
            os.listdir(seed_summary_dir)) if file.endswith('.json')
    ]
    event_type_ids = [0,1,2]
    summary_ids = [0,1,2]
    for summary_id in summary_ids:
        for event_type_id in event_type_ids:
            for i, genre_summaries in  enumerate(summaries):
                skip = False
                if i < 5 and event_type_id == 0 and summary_id == 0:
                    skip = True
                if not skip:
                    seed_summary = genre_summaries['events'][event_type_id]['summaries'][summary_id]
                    print(seed_summary)
                    storyline_directory = generate_storylines_for(seed_summary)

                # try:
                #     generate_time_span_questions([storyline_directory])
                # except Exception as err:
                #     print(err)
                #
                # try:
                #     generate_multi_hop_bridge_questions([storyline_directory])
                # except Exception as err:
                #     print(err)
                #
                # try:
                #     for directory in [storyline_directory]:
                #         directory = '/'.join(directory.split('/')[:3])
                #         create_articles(directory)
                # except Exception as err:
                #     print(err)


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


def main():

    summaries = read_jsonl('outputs/seed-summaries/exported/events1.jsonl')
    summaries = sorted(summaries, key=lambda x: x['genre'])
    for summary in summaries:
        try:
            storyline_directory: str= get_full_outline(summary)
            if storyline_directory is None:
                storyline_directory = generate_storylines_for(summary)

            directory = '/'.join(storyline_directory.split('/')[:3])
            if not exists(join(directory, f'questions/single-2hop-bridge-series.json')):
                generate_multi_hop_bridge_questions([storyline_directory])

            if not exists(join(directory, f'news/news-articles.json')):
                create_articles(directory, selected_news_profiles=[
                    'SensationalNews', 'ObjectiveNews'
                ])
                exit()
        except Exception as err:
            print(err)
    #gen_full()










if __name__ == "__main__":
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    os.environ["AWS_PROFILE"] = "llmexp"
    main()