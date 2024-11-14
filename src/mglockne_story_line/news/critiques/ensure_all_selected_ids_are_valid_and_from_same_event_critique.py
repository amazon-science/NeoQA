from typing import Dict, Set, List

from src.mglockne_story_line.llm.critiques.base_critique import BaseCritique
from src.mglockne_story_line.llm.critiques.critique_result import CritiqueResult


class EnsureAllSelectedIdsAreValidAndFromSameEventCritique(BaseCritique):
    def process(self, values: Dict) -> CritiqueResult:
        event_ids: Set[str] = {item['id'] for item in values['EVENT']['outline']}
        all_err_ids: List[str] = []
        for subset in values['subsets']:
            ids = sorted(
                list(set([_id.strip() for _id in subset.split(',')])),
                key=lambda _id: int(_id.split('-S')[1])
            )
            err_ids: List[str] = sorted(list(set(ids) - event_ids))
            all_err_ids.extend(err_ids)

        all_err_ids = sorted(list(set(all_err_ids)))
        if len(all_err_ids) > 0:
            error_message: str = 'Some subsets include IDs that do not belong to the current event. Please ensure that each subset contains only items from the current event.\n'
            error_message += 'The following IDs are not associated with the current event: ' + ','.join(all_err_ids)
            return CritiqueResult(
                self.name, False, [{'id': _id} for _id in all_err_ids], error_message
            )
        else:
            return CritiqueResult.correct(self.name)

    def __init__(self):
        super().__init__('single-event-selected-ids')