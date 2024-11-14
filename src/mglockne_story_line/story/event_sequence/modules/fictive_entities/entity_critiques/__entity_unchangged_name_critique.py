# from typing import Dict, List
#
# from src.mglockne_story_line.llm.critiques.base_critique import BaseCritique, CritiqueResult
# from src.mglockne_story_line.util.entity_util import get_entity_categories
#
#
# class EntryFieldFormatHeuristics(BaseCritique):
#     def __init__(self):
#         super().__init__('fill-entity-unchanged-name-critique')
#
#     def process(self, values: Dict) -> CritiqueResult:
#
#         id_to_name: Dict[str, str] = {
#             ent['id']: ent['name'].strip()
#             for entity_type in get_entity_categories()
#             for ent in values[f'used_new-{entity_type}']
#         }
#
#         changed_names: List[Dict] = []
#         for entity_type in get_entity_categories():
#             for ent in values[f'fictional_new_{entity_type}s']:
#                 if ent['name'] != id_to_name[ent['id']]:
#                     changed_names.append({
#                         'id': ent['id'],
#                         'used_name': ent['name'],
#                         'correct_name': id_to_name[ent['id']]
#                     })
#         if len(changed_names) > 0:
#             message: str = f'DO NOT change the names of the provided entities. You changed the names of the following entities. Please use the original names instead!\n'
#             for changed_name in changed_names:
#                 message += f' - [ID="{changed_name["id"]}"] The "name" must be "{changed_name["correct_name"]}" but was "{changed_name["used_name"]}".'
#
#
#             return CritiqueResult(self.name, False, changed_names, message)
#         else:
#             return CritiqueResult.correct(self.name)
