from typing import Dict

from experiments.prompter.prompt_generator import PromptGenerator
from experiments.util.entity_util import remove_ids_from


def stringify_news_article(article: Dict, content=None) -> str:
    content: str = f'<title>{article["headline"]}</title>\n'
    content += f'<date>{article["date"]}<date>\n'
    content += '<text>' + ' '.join(article['passages']) + '</text>'
    return f'<article>\n{content}\n</article>'


class MultipleChoicePromptGenerator(PromptGenerator):
    def __init__(self, template_name: str, prompt_directory: str = './prompt_templates/mcq'):
        """
        Fills a prompt template with instances.
        :param template_name:           Name of the template.txt file (.txt is optional)
        :param prompt_directory:        Directory of the template files.
        """
        super().__init__(template_name, prompt_directory)

    def _prepare_prompt_values(self, instance: Dict) -> Dict:
        data = instance

        return {
            'DATE': data['date'],
            'QUESTION': data['question'],
            'ANSWERS': '\n'.join([
                f'[{i+1}] {data["options"][i]}' for i in range(len(data["options"]))
            ]),
            'NEWS_ARTICLES': '\n'.join(list(map(stringify_news_article, data['news_articles'])))
        }
