"""
generate_stories_seeds.py

Usage:
  generate_stories_seeds.py seed-events
  generate_stories_seeds.py seed-summaries
  generate_stories_seeds.py extract-all
"""
import os
import random
import re
from collections import defaultdict
from os import listdir, makedirs
from os.path import join
from typing import Dict, List, Set

from docopt import docopt


from data_gen.llm.get_llm import get_llm
from data_gen.timelines.seeds.seed_event_category_generator import EventCategorySeedGenerator
from data_gen.timelines.seeds.seed_summary_generator import SeedSummaryGenerator
from data_gen.util.file_util import read_jsonl, store_json, read_json, store_jsonl

OUTPUT_DIR: str = 'outputs'


def seed_events(genres: List[str], num_events_per_category: int, model_name: str) -> None:
    version: str = 'v1'
    generator: EventCategorySeedGenerator = EventCategorySeedGenerator(
        get_llm(model_name, temperature=0.0, max_tokens=4000),
        join(OUTPUT_DIR, 'seeds-event-types/event-types'),
        version
    )
    all_events: Dict = dict()
    for genre in genres:
        events: Dict = generator.call(genre, num_events_per_category)
        for i, event in enumerate(events):
            event_type_id: str = genre.replace(' ', '-').lower() + f':{i}'
            event['event_type_id'] = event_type_id
        all_events[genre] = events
    store_json(all_events, join(OUTPUT_DIR, f'seeds-event-types/event-types/all-events-{version}.json'), pretty=True)


def seed_summaries(model_name: str, keywords: List[str] = None, num_summaries: int = 10):
    keywords = keywords or []
    random.seed(1)
    directory: str = join(OUTPUT_DIR, 'seeds-event-types/event-types/')
    directory_out: str = join(OUTPUT_DIR, 'seed-summaries')
    version_summary = 'v8'
    version_event = 'v1'

    generator: SeedSummaryGenerator = SeedSummaryGenerator(
        get_llm(model_name, temperature=0.7, max_tokens=4000),
        directory_out,
        version_summary
    )

    genres: Dict = read_json(join(directory, f'all-events-{version_event}.json'))

    for genre in genres:
        event_types: Dict = genres[genre]
        summaries_genre: Dict = {
            'genre': genre,
            'events': []
        }
        for event_type in event_types:
            category = event_type['category']
            event_type_id: str = event_type['event_type_id']
            summaries = generator.generate_summaries(genre, keywords, num_summaries, category, {
                'genre': genre,
                'category': category,
            })

            for i, summary in enumerate(summaries):
                summary['genre'] = genre
                summary['event_type'] = event_type
                summary['event_type_id'] = event_type_id
                summary['story_seed_id'] = f'{event_type_id}:{i}'

                # We use this because story generation has some hard sampling. We want this to be seeded with different
                # seeds among different stories.
                summary['init_random_seed'] = random.randint(1, 1000000)

            summaries_genre['events'].append({
                'event': category,
                'summaries': summaries
            })
        store_json(summaries_genre, join(directory_out, f'all-{genre}-{version_summary}_{version_event}.json'))


def is_okay(_summary):
    text: str = _summary['summary'].lower()
    is_valid: bool = True
    blacklist = [
        r'\bwar\b', 'sex', 'religi', 'murder', 'violen', 'olympic', 'supreme court', 'revolutionary', 'holographic',
        r'\btech\b', 'international', '-wide', 'blockchain', 'discovery', 'cryptocurrency', 'created a new' 'cyber',
        r'\bai\b'
    ]

    # Added for v2
    blacklist += [
        'fantasy'

    ]
    for w in blacklist:
        if bool(re.search(w, text)):
            is_valid = False
    return is_valid


def extract_summaries_all(random_seed: int, existing: List[str] = None):
    directory: str = 'outputs/seed-summaries'
    prev_exported_dir = join(directory, 'exported')
    used_story_seed_ids: Set[str] = set()
    for file in existing or []:
        summaries: List[Dict] = read_jsonl(join(prev_exported_dir, file))
        for summary in summaries:
            used_story_seed_ids.add(summary['story_seed_id'])

    # Load all summaries
    files = [
        file for file in listdir(directory) if file.endswith('.json')
    ]
    genre_to_summaries = defaultdict(list)
    for file in files:
        summaries: Dict = read_json(join(directory, file))
        for event in summaries['events']:
            for summary in event['summaries']:
                if is_okay(summary) and summary['story_seed_id'] not in used_story_seed_ids:
                    genre_to_summaries[summary['genre']].append(summary)
    rnd = random.Random(random_seed)
    for key in genre_to_summaries:
        rnd.shuffle(genre_to_summaries[key])

    def count_items():
        return sum([
            len(genre_to_summaries[genre_key]) for genre_key in genre_to_summaries
        ])

    idx: int = 0
    out_dir = 'outputs/seed-batches'
    makedirs(out_dir, exist_ok=True)
    while count_items() > 0:
        current_summaries: List[Dict] = []
        for i in range(3):
            for k in genre_to_summaries:
                if len(genre_to_summaries[k]) > 0:
                    current_summaries.append(genre_to_summaries[k][0])
                    genre_to_summaries[k] = genre_to_summaries[k][1:]
        pass
        idx += 1
        store_jsonl(current_summaries, join(out_dir, f'batch-{idx:02}.jsonl'))


def main():
    """
    Main function to parse command-line arguments using docopt and execute commands.
    """
    args = docopt(__doc__, version="Storyline 1.0")
    random.seed(1)
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    os.environ["AWS_PROFILE"] = "llmexp"

    genres = [
        'Sports', 'Celebrities',
        'Politics', "International Affairs", 'Environment', 'Local News', 'Art', 'Food', 'Epidemics',
        'Business', 'Crimes', "Health", 'Lifestyle', 'Travel', 'Technology', 'Economics', 'Science', 'Education',
        'Social Issues', 'Legal'
    ]

    model_name = 'gpt4-turbo'

    if args['seed-events']:
        seed_events(genres, 20, model_name)
    elif args['seed-summaries']:
        seed_summaries(model_name, num_summaries=10)
    elif args['extract-all']:
        extract_summaries_all(12345)


if __name__ == "__main__":
    main()
