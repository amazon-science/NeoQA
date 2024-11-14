import json
from typing import Dict, List

from src.mglockne_story_line.llm.wrapper.base_llm_wrapper import BaseLLMWrapper
from src.mglockne_story_line.util.story_tools import remove_ids_from


def create_event_summary(llm: BaseLLMWrapper, event: Dict, past_events: List[Dict]) -> str:

    past_event_texts = ''
    for ev in past_events:
        past_event_texts += ' '.join([
            remove_ids_from(item['sentence']) for item in ev['outline']
        ])
        past_event_texts += '\n\n'
    past_event_texts = past_event_texts.strip()

    text = ' '.join([
        remove_ids_from(item['sentence']) for item in event['outline']
    ])
    return llm.query(None, f"""
You are a skilled writer tasked with summarizing a new event in the context of an ongoing story. You will be provided with a background story and details of a new event. Your job is to write a concise summary of the new event that fits seamlessly into the existing narrative.

First, read the following background story:
<background>
{past_event_texts}
</background>

Now, here are the details of the new event:
<event>
{text}
</event>

To summarize this new event:
1. Carefully consider how the new event relates to the background story.
2. Identify the key points of the new event that are most relevant to the ongoing narrative.
3. Think about how this event might impact the characters or situation described in the background.
4. Craft a concise summary that integrates the new event into the existing story.

Your summary should:
- Be approximately 2-3 sentences long
- Clearly explain what happened in the new event
- Show how the new event connects to or advances the existing narrative

Only write the summary and nothing else.""".strip())['response']
