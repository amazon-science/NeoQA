from os.path import join
from typing import Dict

from src.mglockne_story_line.llm.modules.callable_module import CallableModule, FilePathModule
from src.mglockne_story_line.llm.modules.impl.file_output_caller import FileOutputCaller
from src.mglockne_story_line.llm.prompting.parsable_prompt import ParsablePrompt
from src.mglockne_story_line.llm.prompting.modules.shallow_xml_output_prompts import ShallowXMLListOutputPrompt
from src.mglockne_story_line.llm.wrapper.base_llm_wrapper import BaseLLMWrapper


class EventCategorySeedGenerator(FileOutputCaller, FilePathModule):

    def __init__(self, llm: BaseLLMWrapper, output_directory: str, instruction_name: str):
        super().__init__(llm, self)
        self.instructions: str = get_instructions(instruction_name)
        self.instruction_name: str = instruction_name
        self.directory: str = join(output_directory, instruction_name)

    def call(self, news_genre: str, num_event_categories: int, print_results: bool = True):
        prompt: ShallowXMLListOutputPrompt = ShallowXMLListOutputPrompt(self.instructions, ['category'], self.instruction_name)
        out: Dict = self.query(
            prompt,
            {"NUM_CATEGORIES": num_event_categories, "NEWS_GENRE": news_genre}, self.directory
        )
        out = prompt.parse(out['response'])

        if print_results:
            print(f'News Genre: {news_genre} ({num_event_categories} categories)')
            for cat in out:
                print(f' - {cat["category"]}')

        return out

    def get_file_name(self, prompt: ParsablePrompt, values: Dict):
        genre: str = values["NEWS_GENRE"].replace(' ', '-')
        num: int = values["NUM_CATEGORIES"]
        return f'{genre}__num-{num}__{self.instruction_name}.json'


def get_instructions(name: str) -> str:
    if name == 'v1':
        instructions: str =  NEWS_EVENT_TYPE_INSTRUCTIONS_V1
    else:
        raise ValueError(name)
    return instructions.strip()


NEWS_EVENT_TYPE_INSTRUCTIONS_V1: str = """
You are an AI assistant tasked with generating a list of newsworthy event categories for a specific news genre. Your goal is to create a diverse and comprehensive list that covers various aspects of the given genre.

The news genre you will be working with is:
<genre>
{{NEWS_GENRE}}
</genre>

You are to generate the following number of categories:
<number>
{{NUM_CATEGORIES}}
</number>

Please follow these instructions carefully:

1. Generate exactly {{NUM_CATEGORIES}} distinct categories of newsworthy events within the {{NEWS_GENRE}} genre.

2. Each category should be specific and topical, focusing on particular types of events, occurrences, or subjects within the genre.

3. Ensure that the categories are diverse and cover different aspects of the {{NEWS_GENRE}} field.

4. Consider various stakeholders, events, developments, and issues that could be relevant to this news genre.

5. Avoid overlapping or redundant categories.

6. Present each category within its own XML tag, using the format <category></category>.

7. Number each category for easy reference.

Here's an example of how your output should be formatted (using "Technology" as an example genre):

1. <category>Product Launches</category>

2. <category>Cybersecurity Breaches</category>

3. <category>Artificial Intelligence Advancements</category>

Remember to tailor your categories specifically to the {{NEWS_GENRE}} genre and generate exactly {{NUM_CATEGORIES}} categories. Begin your list now.
"""

