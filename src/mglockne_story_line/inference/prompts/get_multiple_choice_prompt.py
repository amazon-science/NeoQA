import re
from collections import defaultdict
from turtledemo.sorting_animate import instructions1
from typing import Dict, List

from rich import inspect

from src.mglockne_story_line.util.story_tools import remove_ids_from


def get_multiple_choice_prompt(version: str, values: Dict, evidence_type: str = 'articles') :
    if version == 'default-1':
        instructions = INSTRUCTIONS_DEFAULT_1
    elif  version == 'default-2':
        instructions = INSTRUCTIONS_DEFAULT_2
    elif  version == 'default-3':
        instructions = INSTRUCTIONS_DEFAULT_3
    elif version == 'timespan-1':
        instructions = INSTRUCTIONS_TIMESPAN_1
    else:
        raise NotImplementedError

    def stringify_article(article):
        headline = remove_ids_from(article['content']['headline'])
        body = remove_ids_from(article['content']['body'])
        date = article['date']
        return f'<article><title>{headline}</title><date>{date}</date><content>{body}</content></article>'

    def stringify_outline_ids(outline_item):
        return f'<article><date>{outline_item["date"]}</date><content>{outline_item["content"]}</content></article>'



    if evidence_type == 'articles':
        news_articles = '\n\n'.join([stringify_article(a) for a in values['evidence']])
    elif evidence_type == 'sentences':
        # Was like this in 1410
        news_articles = '\n'.join([stringify_outline_ids(item) for item in values['evidence']])
    else:
        assert evidence_type == 'combined-sentences'
        written_articles = []
        articles = defaultdict(list)
        for evidence in values['evidence']:
            articles[evidence['event_id']].append(evidence)
        event_ids = sorted(list(articles.keys()))
        for event_id in event_ids:
            sentences = sorted(articles[event_id], key=lambda x: x['sentence_idx'])
            written_articles.append(
                f'<article><date>{sentences[0]["date"]}</date><content>{" ".join([s["content"] for s in sentences])}</content></article>'
            )

        news_articles = '\n'.join(written_articles)

    prompt_values = {
        'DATE': values['date'], #.strftime("%Y-%m-%d"),
        'QUESTION': remove_ids_from(values['question']),
        'ANSWERS': '\n'.join([
            f'[{num + 1}] {answer}' for num, answer in enumerate(values['answer_options'])
        ]),
        'NEWS_ARTICLES': news_articles
    }

    for key in prompt_values:
        repl = '{{' + key.upper() + '}}'
        if repl in instructions:
            instructions = instructions.replace(repl, prompt_values[key])

    pattern_instruction_placeholder: re.Pattern = re.compile(r'\{\{\w+\}\}')
    placeholder_exist = bool(re.search(pattern_instruction_placeholder, instructions))
    if placeholder_exist:
        raise ValueError(f'Placeholder still exist in prompt: "{instructions}"')

    return instructions

INSTRUCTIONS_TIMESPAN_1 = """
You are tasked with evaluating news articles to answer a question based on the information provided and a given date. Your goal is to determine if there's enough information to answer the question and select the correct answer option.

Here are the news articles you need to analyze:
<news_articles>
{{NEWS_ARTICLES}}
</news_articles>

The date on which the question is asked:
<date>
{{DATE}}
</date>

The question you need to answer:
<question>
{{QUESTION}}
</question>

The available answer options:
<answer_options>
{{ANSWERS}}
</answer_options>

Follow these steps to complete the task:

1. Carefully read and analyze all the provided news articles.
2. Compare the information in the articles with the question.
3. Check if the combined information from the articles confirms all the details required to answer the question.

4. Use a scratchpad to derive your answer:
   <scratchpad>
   - Identify all absolute start and end dates based on the content of the articles, the article dates, and any assumptions from the question.
   - Explicitly derive the answer based on these absolute dates if possible.
   - Show your step-by-step reasoning process.
   </scratchpad>

5. Select an answer:
   - Choose the correct answer if all necessary details are provided.
   - If the articles lack information or any important detail is missing, select the option for "Unknown."
   - If the question states assumptions, consider them as facts.

6. Provide your response in JSON format as follows:
   {
       "scratchpad": "Your reasoning from the scratchpad",
       "justification": "Brief explanation (1-2 sentences max)",
       "answer_choice": "A single number that corresponds to the chosen answer."
   }

Output the JSON directly without any additional text or markdown syntax.
"""

INSTRUCTIONS_DEFAULT_1 = """
You will receive news articles, a question, a date on which the question is asked, and answer options. Your task is to evaluate the articles, determine if they provide enough information to answer the question based on the date, and choose the correct answer.

**News Articles:**
<news_articles>
{{NEWS_ARTICLES}}
</news_articles>

**Date:**
{{DATE}}

**Question:**
{{QUESTION}}

**Answer Options:**
{{ANSWERS}}

**Instructions:**

1. **Analyze the Articles:**
   - Carefully read all the news articles.
   - Compare the information in the articles with the question.
   - Check if the combined information from the articles confirms all the details required to answer the question.

2. **Select an Answer:**
   - Choose the correct answer if all necessary details are provided.
   - If the articles lack information or any detail is missing, select "Unknown."

3. **Submit your Answer:**
   - Provide only the answer number.

**Answer number:**
"""



INSTRUCTIONS_DEFAULT_2 = """
You will receive news articles, a question, a date on which the question is asked, and answer options. Your task is to evaluate the articles, determine if they provide enough information to answer the question based on the date, and choose the correct answer.

**News Articles:**
<news_articles>{{NEWS_ARTICLES}}</news_articles>

**Date:**{{DATE}}**

Question:**{{QUESTION}}

**Answer Options:**
{{ANSWERS}}

**Instructions:**
1. **Analyze the Articles:**
- Carefully read all the news articles.
- Compare the information in the articles with the question.
- Check if the combined information from the articles confirms all the details required to answer the question.
2. **Select an Answer:**
- Choose the correct answer if all necessary details are provided.
- If the articles lack information or any important detail is missing, select the option for "Unknown."
3. **Submit your Answer:**
Provide your response in JSON format as follows:
{
    "justification": "Brief explanation (1-2 sentences max)",
    "answer_choice": "A single number that corresponds to the chosen answer."
}


Output JSON directly without any additional text or markdown syntax.
"""

INSTRUCTIONS_DEFAULT_3 = """
You will receive news articles, a question, a date on which the question is asked, and answer options. Your task is to evaluate the articles, determine if they provide enough information to answer the question based on the date, and choose the correct answer.

**News Articles:**
<news_articles>
{{NEWS_ARTICLES}}
</news_articles>

**Date:**
{{DATE}}

**Question:**
{{QUESTION}}

**Answer Options:**
{{ANSWERS}}

**Instructions:**
1. **Analyze the Articles:**
- Carefully read all the news articles.
- Compare the information in the articles with the question.
- Check if the combined information from the articles confirms all the details required to answer the question.
2. **Select an Answer:**
- Choose the correct answer if all necessary details are provided.
- If the articles lack information or any important detail is missing, select the option for "Unknown."
3. **Submit your Answer:**
Provide your response in JSON format as follows:
{
    "justification": "Brief explanation (1-2 sentences max)",
    "answer_choice": "A single number that corresponds to the chosen answer."
}


Output JSON directly without any additional text or markdown syntax.
"""