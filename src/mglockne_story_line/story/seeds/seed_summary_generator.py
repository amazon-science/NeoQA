from os.path import join
from typing import List, Dict, Optional

from src.mglockne_story_line.llm.modules.callable_module import  FilePathModule
from src.mglockne_story_line.llm.modules.impl.file_output_caller import FileOutputCaller
from src.mglockne_story_line.llm.prompting.parsable_prompt import ParsablePrompt
from src.mglockne_story_line.llm.prompting.modules.shallow_xml_output_prompts import ShallowXMLListOutputPrompt
from src.mglockne_story_line.llm.wrapper.base_llm_wrapper import BaseLLMWrapper

def get_instructions(name: str) -> str:
    if name == 'v8':
        instructions = NEWS_SUMMARY_INSTRUCTIONS_V8
    else:
        raise ValueError(name)
    return instructions.strip()


class SeedSummaryGenerator(FileOutputCaller, FilePathModule):

    def __init__(self, llm: BaseLLMWrapper, output_directory: str, instruction_name: str):
        super().__init__(llm, self)
        self.instruction_name: str = instruction_name
        self.instructions: str = get_instructions(instruction_name)
        self.directory: str = join(output_directory, instruction_name)

    def generate_summaries(
            self,
            news_genre: str,
            optional_keywords: List[str],
            num_summaries: int,
            event_type: str,
            params: Optional[Dict] = None, print_results: bool = True):
        params = params or dict()
        prompt = ShallowXMLListOutputPrompt(self.instructions, ['summary'], self.instruction_name)
        out: Dict = self.query(
            prompt,
            {
                "NUMBER_OF_SUMMARIES": num_summaries, "GENRE": news_genre,
                "KEYWORDS": ', '.join(optional_keywords), "EVENT_TYPE": event_type
            } | {
                k.upper(): params[k] for k in params
            },
            self.directory,
            params=params
        )
        out = prompt.parse(out['response'])

        if print_results:
            print(f'News Genre: {news_genre}\n Event: "{event_type}"')
            print(f'Optional Keywords: "{", ".join(optional_keywords)}"')
            for summary in out:
                print(f' - {summary["summary"]}')

        return out

    def get_file_name(self, prompt: ParsablePrompt, values: Dict):
        genre: str = values["GENRE"].replace(' ', '-').lower()
        event_type: str =  values["EVENT_TYPE"].replace(' ', '-').lower()[:20]
        keywords: str =  values["KEYWORDS"].replace(' ', '-').replace(',', '').lower()
        return f'{genre}__{event_type}__{keywords}__{self.instruction_name}.json'




NEWS_SUMMARY_INSTRUCTIONS_V8 = """
You are an AI assistant tasked with generating fictional one-sentence summaries of newsworthy events. Your goal is to create realistic-sounding, diverse, and objective summaries that could plausibly appear in news media, while ensuring they are entirely fictional and not based on real events.

You will be given the following inputs:

1. Genre: <genre>{{GENRE}}</genre>
2. Event Type: <event_type>{{EVENT_TYPE}}</event_type>
3. Keywords (optional): <keywords>{{KEYWORDS}}</keywords>
4. Number of Summaries to Generate: <number>{{NUMBER_OF_SUMMARIES}}</number>

To create appropriate fictional news summaries, follow these guidelines:

1. Ensure all summaries are fictional and not based on real events or real people.
2. Make the summaries sound realistic and plausible for the given genre and event type.
3. Use the provided keywords as inspiration for the background, setting, location, actors, or subevents of your summaries.
4. Avoid using specific names of real people, organizations, or places.
5. Create summaries that are unbiased and objective in tone.
6. Vary the structure and content of the summaries to maintain diversity.
7. Include relevant details that make the summary specific and factual.
8. Focus on providing clear, concise information rather than creating intrigue or sensation.
9. Balance the summaries so that some describe events that are not very newsworthy and are rather informative, while others are of interest to wider audiences.

Before generating the summaries, think about various associations you have with the keywords and how they could relate to the genre and event type. Write these associations and potential connections in <associations> tags. Use these associations to inform your summary creation.

Format your output as follows:
1. First, provide your associations and potential connections in <associations> tags.
2. Then, place each one-sentence summary within <summary> tags.

Here are some examples of good summaries:
<summary>A local community garden initiative has successfully transformed an abandoned lot into a thriving green space, providing fresh produce for neighborhood residents.</summary>
<summary>Scientists have discovered a new species of deep-sea creature that exhibits unique bioluminescent properties, potentially offering insights into marine ecosystems.</summary>
<summary>A multinational technology company has announced plans to invest in renewable energy infrastructure, aiming to power all its operations with clean energy within five years.</summary>
<summary>Recent archaeological findings in a remote desert region have uncovered evidence of an ancient civilization's advanced irrigation systems.</summary>

Important reminders:
- Produce concise, factual, objective single-sentence statements.
- Do not refer to any (existing or fictional) named entity explicitly.
- Ensure all summaries sound realistic.
- Maintain an objective and unbiased tone without introducing any "excitement" in the wording.
- Make sure that each summary is substantially affected by (parts of) the keywords or your associations - if the keywords exist.
- Focus on the content of the summary of the fictional events, not on the tone.
- Balance the newsworthiness of the summaries, including both informative and widely interesting events.

Begin by writing your associations in <associations> tags, then generate the summaries, ensuring you create exactly the number of summaries specified in the input.
"""
