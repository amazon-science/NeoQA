from os import listdir
from os.path import join
from typing import Dict, List

from data_gen.llm.get_llm import get_llm
from data_gen.llm.modules.history_parsable_module_list import HistoryParsableModuleList
from data_gen.llm.modules.module_pipeline import ModulePipeline
from data_gen.llm.wrapper.base_llm_wrapper import BaseLLMWrapper
from data_gen.timelines.event_sequence.event_sequence2 import EventSequence2
from data_gen.timelines.event_sequence.modules.fictive_entities.adjust_outline_with_entity_names import \
    ResolveFoundNamedEntityConflictsInOutlineModule
from data_gen.timelines.event_sequence.modules.fictive_entities.entity_fill_fields import PopulateNewNamedEntitiesModule
from data_gen.timelines.event_sequence.modules.fictive_entities.entity_find_names import IdentifyNewNamedEntitiesModule
from data_gen.timelines.event_sequence.modules.fictive_entities.entity_fix_names import ChangeNamedEntityNamesModule
from data_gen.timelines.event_sequence.modules.fictive_entities.entity_update2 import UpdateNamedEntityEntriesModule
from data_gen.timelines.event_sequence.modules.fictive_entities.find_new_entities_and_assign_ids import \
    FindNewAndOldEntitiesWithIDs
from data_gen.timelines.event_sequence.modules.fictive_entities.idfy_outline import IdfyOutlineWithNamedEntitiesModule
from data_gen.timelines.event_sequence.modules.improver.add_specifics import AddSpecificDetailsToOutlineModule
from data_gen.timelines.event_sequence.modules.improver.consistency_checker import CheckOutlineConsistencyModule
from data_gen.timelines.event_sequence.modules.recursive_outine_generator import OutlineGenerationModule
from data_gen.timelines.event_sequence.modules.story_alternative_continuations import AlternativeStoryContinuationModule
from data_gen.timelines.event_sequence.modules.story_continuation import StoryContinuationModule
from data_gen.util.file_util import read_json
from data_gen.util.story_tools import get_outline_directory_from_story_path

OUTPUT_DIR: str = 'outputs'

def get_seed_items(subset_key: str, start_at: int = 0):
    """
    This is just to avoid creating stories for ALL possible seed summaries. Adjust as necessary.
    """

    seed_summary_dir: str = 'outputs/seed-summaries'
    summaries: List[Dict] = [
        read_json(join(seed_summary_dir, file)) for file in sorted(listdir(seed_summary_dir)) if file.endswith('.json')
    ]

    if subset_key == 'set1':
        event_category_idx: int = 10  # Out of 40
        summary_seed_idx: int = 10  # Out of 20
        genre_cutoff: int = 6  # out of 20

        for genre_summaries in summaries[start_at:genre_cutoff]:
            event: Dict = genre_summaries['events'][event_category_idx]
            yield event['summaries'][summary_seed_idx]
    elif subset_key == 'set2':
        event_category_idx: int = 5  # Out of 40
        summary_seed_idx: int = 5  # Out of 20
        genre_cutoff: int = 21  # out of 20
        for genre_summaries in summaries[start_at:genre_cutoff]:
            event: Dict = genre_summaries['events'][event_category_idx]
            yield event['summaries'][summary_seed_idx]

    elif subset_key == 'set3':
        summaries = [
            read_json(join(seed_summary_dir, 'all-Social Issues-v8_v1.json'))['events'][25]['summaries'][3],  # Very dangerous one
            read_json(join(seed_summary_dir, 'all-Social Issues-v8_v1.json'))['events'][12]['summaries'][3],  # Randomly selected
            read_json(join(seed_summary_dir, 'all-Local News-v8_v1.json'))['events'][12]['summaries'][3],  # Very dangerous one
            read_json(join(seed_summary_dir, 'all-Celebrities-v8_v1.json'))['events'][12]['summaries'][3]  # Randomly selected
        ]
        yield from summaries
    elif subset_key == 'fix':
        summaries = [
            read_json(join(seed_summary_dir, 'all-Celebrities-v8_v1.json'))['events'][12]['summaries'][3]  # Randomly selected
        ]
        yield from summaries

    else:
        raise NotImplementedError(subset_key)


def make_pipeline_name(seed_item: Dict) -> str:
    seed_id: str = seed_item['story_seed_id']
    name: str = seed_id.replace(':', '_')
    return name


def get_pipeline_toned_down_2(
    llm_strict: BaseLLMWrapper,
    llm_write: BaseLLMWrapper,
    num_continuations: int = 4,
    num_story_items: int = 10,
    add_specifics: int = 2,
) -> ModulePipeline:

    components: List = [
        OutlineGenerationModule(llm_write, 'A_outline-generate', 'v5', num_story_items),
        AddSpecificDetailsToOutlineModule(llm_strict, 'B_outline-add-specifics', 'v7', add_specifics),
        CheckOutlineConsistencyModule(llm_strict, 'C_outline-consistency', 'v1'),
        HistoryParsableModuleList(
            [
                IdentifyNewNamedEntitiesModule(llm_strict, 'D_entities-find', 'v8'),
                ChangeNamedEntityNamesModule(llm_write, 'E_entities-fix', 'v1'),
                ResolveFoundNamedEntityConflictsInOutlineModule(llm_strict, 'F_outline-fixnames', 'v4'),
                FindNewAndOldEntitiesWithIDs(llm_strict, 'G_entities-idfy', 'v3'),
                IdfyOutlineWithNamedEntitiesModule(llm_strict, 'H_outline-idfy', 'full1'),
                PopulateNewNamedEntitiesModule(llm_write, 'I_entities-fill-entries', 'v3'),
                UpdateNamedEntityEntriesModule(llm_strict, 'J_entities-update-history', 'v1'),
            ],
            'entities',
            # We reset thew history on these steps.
            reset_history_at=[3, 4, 5, 6, 7]  # Entity Updater has no history
        ),
        StoryContinuationModule(llm_write, 'K_continue', 'v3-diverse', num_continuations),
        AlternativeStoryContinuationModule(llm_write, 'L_continue_alt', 'v3', 3)
    ]

    return ModulePipeline(components)


def get_event_sequence_toned_down2(
        llm_strict: BaseLLMWrapper,
        llm_creative: BaseLLMWrapper,
        seed_item: Dict,
        outline_directory: str
) -> EventSequence2:
    pipeline_name: str = make_pipeline_name(seed_item)
    pipeline: ModulePipeline = get_pipeline_toned_down_2(llm_strict, llm_creative)

    output_dir: str = join(OUTPUT_DIR, outline_directory)

    event_sequence = EventSequence2(
        pipeline_name, output_dir, pipeline, pipeline, seed_item['genre'], seed_item['summary'], seed_item['story_seed_id'], seed_item['init_random_seed']
    )
    return event_sequence


def generate_storylines_for(seed_item: Dict,  directory: str,  llm_name: str, max_num_events: int = 10, version=2):
    llm_strict: BaseLLMWrapper = get_llm(llm_name, 0.0, 10000)
    llm_creative: BaseLLMWrapper = get_llm(llm_name, 1.0, 10000)

    llm_creative.reset_query_count()
    llm_strict.reset_query_count()

    if version == 1:
        assert False, 'outdated'
        # event_seq: EventSequence2  = get_event_sequence(
        #     llm_strict, llm_creative,
        #     seed_item
        # )
    elif version == 2:
        event_seq: EventSequence2 = get_event_sequence_toned_down2(
            llm_strict, llm_creative,
            seed_item, outline_directory=directory
        )
    else:
        raise NotImplementedError

    query_counts = []
    event_seq.start({
        'KEY_OUTLINE_REFINE_STEP': 0,
    })

    query_counts.append(llm_strict.count_queries + llm_creative.count_queries)
    for i in range(1, max_num_events):
        event_seq.continue_news()
        query_counts.append(llm_strict.count_queries + llm_creative.count_queries)

        event_seq.export(f'it-{i + 1}', {
            'query_counts': query_counts
        } | seed_item)
    out_dir = get_outline_directory_from_story_path(event_seq.output_directory)
    return out_dir
