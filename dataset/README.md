# The NeoQA Dataset
> To run the experiments in this repository, make sure to add the decrypted `.jsonl` files in the appropriate directories.

## 📚 Overview
This documentation covers the core data structures used in **NeoQA**:
1. **Timelines** – Chronological sequences of fictional events centered around fictional named entities.
2. **News** – News articles about the fictional events.
3. **Questions** – Multiple Choice Questions about the fictional events.
4. **QA Instances** – The questions paired with news articles as evidence with a clear correct answer.

## 🕰️  Timelines
NeoQA is fully grounded in **fictional timelines** — structured sequences of events that form the narrative basis for all generated questions and answers.
Every timeline is *self-contained* and should not be combined with other timelines. No care was taken that the different timelines are compatible.

Below is the core structure of a timeline object:
````json
{
    "timeline_id": "local-news:12:8",
    "genre": {
        "category": "Local News",
        "genre_id": "local-news"
    },
    "event_type": {
        "category": "Public Safety Initiatives",
        "event_type_id": "local-news:12"
    },
    "initial_summary": "A community has successfully campaigned for the installation of a comprehensive surveillance system at their local mall, aiming to deter theft and enhance shopper safety.",
    "events": [...],
    "named_entity_snapshots": [...]
}
````

Each timeline includes:
- A unique identifier: `timeline_id`
- A `genre` (e.g., `Local News`)
- A specific `event_category` within that genre (e.g., `Public Safety Initiatives`)
- An `initial_summary`, which seeds the generation of the first event
- A sequence of `events` and `named_entity_snapshots`, which track named entities over time.

### 🧩 Events
Events occur in sequential order within each timeline. They may re-use named entities introduced in earlier events and/or introduce new ones.
Each event includes:
- A unique identifier (`event_id`)
- A `created_at` value indicating the event's position in the timeline
- An `initial_summary` — a short description that seeded the generation of the event
- A `date` representing when the fictional event occurred
- A list of `used_named_entities`, along with a flag (`new`) indicating if each entity is introduced in this event
- An `outline`, which breaks the event into individual narrative sentences:
  - Each sentence contains unique, detailed information
  - Each sentence has a unique `id` within the timeline

**Example Event:**
````json
        {
            "event_id": "local-news:12:8:E0",
            "created_at": 0,
            "initial_summary": "A community has successfully campaigned for the installation of a comprehensive surveillance system at their local mall, aiming to deter theft and enhance shopper safety.",
            "date": "2023-11-15",
            "used_named_entities": [
                {
                    "id": "PERSON-1",
                    "new": true
                },
                {
                    "id": "PERSON-2",
                    "new": true
                }, 
              ...
            ],
            "outline": [
                {
                    "sentence": "The community of {Silverbine Heights|LOCATION-1} successfully petitioned for the installation of a surveillance system at the {Birchwalk Commons|LOCATION-2} shopping mall.",
                    "id": "N0-S0",
                    "pos": 0
                },
                {
                    "sentence": "The petition gathered over 1,200 signatures from residents, highlighting widespread support for the initiative.",
                    "id": "N0-S1",
                    "pos": 1
                },
                ...
            ]
        }
````

### 🧬 Named Entities
Every fictional named entity in NeoQA is tracked through a **Knowledge Base (KB)**. For each event in a timeline, a **snapshot** of the KB is created, capturing the state of all named entities at that point in time.
This means that for a timeline with ten events, there will be ten corresponding snapshots — one for each point in the narrative.

Each **Named Entity Snapshot** contains:
- `created_at`: Position of the event in the timeline
- `for_event`: The `event_id` this snapshot corresponds to
- `date`: The fictional date of the event
- `named_entities`: A dictionary grouped by entity type (e.g., `person`, `organization`, `location`, etc.)

Within each entity type:
- Every named entity includes a unique `id` and a `name`
- Entities maintain a `history`, logging their involvement in events over time
- Different entity types may include **custom properties** relevant to their category (e.g., a person may have `profession`, while a location may have `population`)


**Example Named Entity Snapshot:**
````json
{
    "created_at": 0,
    "for_event": "local-news:12:8:E0",
    "date": "2023-11-15",
    "named_entities": {
      "person": [{
            "id": "PERSON-1",
            "name": "Sarah Kim",
            "entity_class": "person",
            "description": "An ambitious and entrepreneurial individual with a passion for fashion and community engagement.",
            "type": null,
            "created_at": 0,
            "last_updated": "2023-11-15",
            "history": [
                {
                    "created_at": 0,
                    "event_update": "Sarah Kim, owner of Kim's Boutique, expressed support for the new surveillance system at Birchwalk Commons, citing increased safety during the holiday shopping season.",
                    "date": "2023-11-15"
                }
            ],
            "date_of_birth": "1987-08-14",
            "gender": "Female",
            "profession": "Small business owner",
            "nationality": "Evendese",
            "education": "Bachelor's Degree in Business Administration",
            "height": "5'5\"",
            "weight": "135 lbs",
            "eye_color": "Brown",
            "hair_color": "Black",
            "marital_status": "Single",
            "political_affiliation": "Independent"
        },
        ...
        ],
      "organization": [...],
      "location": [...],
      "product": [...],
      "art": [...],
      "building": [...],
      "event": [...],
      "miscellaneous": [...],
    }
}
````
## 📰 News

Each event in a timeline is associated with multiple **news articles**, each written from a distinct **news profile**. These articles selectively report on specific aspects of the event, presenting only a **subset** of the event’s information.

**Key Characteristics:**
- A news article includes **only** the content from the sentences it explicitly references (`used_items`).
- It is assumed to contain **none** of the content from other sentences.
- In some cases, certain sentences fall into an `unsure_evidences` list—these are cases where inclusion/exclusion may conflict with external evaluations (via NLI predictions).
- News articles serve as the **evidence base** for answering generated questions.

**News Article Fields:**
- `timeline_id`: Identifies the timeline in which the article appears
- `article_id`: Unique identifier for the article
- `event_id`: The event the article is reporting on
- `headline`: The headline of the article
- `passages`: A list of paragraphs forming the article’s body
- `news_profile`: The style or perspective used to generate the article
- `used_items`: A list of sentence IDs from the event that are **included** in the article
- `unsure_evidences`: A list of sentence IDs where inclusion is uncertain
- `created_at`: Index of the event in the timeline

**Example News article:**
````json
{
    "timeline_id": "local-news:12:8",
    "article_id": "local-news_12_8-ev0-0",
    "event_id": "local-news:12:8:E0",
    "headline": "Silverbine Heights Celebrates New Surveillance System for Birchwalk Commons",
    "passages": [
        "The residents of {Silverbine Heights|LOCATION-1} have successfully petitioned for the installation of a new surveillance system at the neighborhood's {Birchwalk Commons|LOCATION-2} shopping mall. The petition, which gathered over 1,200 signatures from residents, highlighted widespread support for the initiative and underscored the community's commitment to addressing safety concerns. {Crestfield Property Holdings|ORGANIZATION-2}, the mall's management company, has agreed to finance and oversee the system's implementation, marking a collaborative step between local stakeholders.",
        "The campaign was coordinated by the {Silverbine Heights Residents Council|ORGANIZATION-1}, which cited rising instances of shoplifting and vandalism at the mall as key motivators for the initiative. Over the past six months, the council hosted three town hall meetings to engage residents and local business owners, providing a platform for dialogue and gathering input on the proposed measures. \"This is a big step towards making our neighborhood and public spaces safer for everyone,\" said {Marta Lenevos|PERSON-2}, chairperson of the council, reflecting on the community's achievement.",
        "The forthcoming implementation of the surveillance system is expected to address safety concerns at {Birchwalk Commons|LOCATION-2}, reassuring shoppers and business owners while deterring future incidents of crime and vandalism. The initiative reflects the community's dedication to improving public spaces and fostering a safer environment for all."
    ],
    "created_at": 0,
    "news_profile": "ConservativeNews",
    "date": "2023-11-15",
    "unsure_evidences": [
        "N5-S20"
    ],
    "used_items": [
        "N0-S0",
        "N0-S1",
        "N0-S2",
        "N0-S3",
        "N0-S4",
        "N0-S14"
    ]
}
````

## ❓ Questions

In NeoQA, all questions are presented in a **multiple-choice** format. The questions are designed to be answerable based on evidence from the timeline, with a particular focus on **multi-hop reasoning** and **time-span calculations**.

#### Question Types
NeoQA includes two primary types of answerable questions:
- **multi-hop**: Requires resolving named entities across multiple sentences or events to answer the question. The model must first identify the relevant entity before answering the question.
- **time-span**: The model must identify two points in time from the event timeline and compute the duration between them.

Additionally, NeoQA contains two types of **unanswerable** questions:
- **false premise**: The question contains parts that conflict with the provided evidence, making it impossible to answer correctly.

#### Question Design
- Questions are created based on **all available information up to the specified event**. For instance, a question referring to information from the first and third events is designed to have only one correct answer considering all data up to (and including) the third event. Questions are not meant to be answerable with future event data (e.g., from the fourth event).
- The **used_items** property of news articles is used to determine if the collected news articles contain sufficient evidence to answer a question.

Each question includes the following properties:

- `timeline_id`: Identifies the timeline in which the question is asked
- `question_id`: Unique identifier for each question
- `parent_question_id`: ID of the parent multi-hop question for false-premise or uncertain specificity questions
- `evidence_ids`: List of sentence IDs from which evidence is extracted to answer the question
- `question`: The text of the question
- `answer`: The correct answer (as a string)
- `category`: The type of question (e.g., `multi-hop`, `time-span`)
- `distractors`: A list of invalid answer options. Each distractor includes:
  - `answer`: The incorrect answer
  - `explanation`: Reason why the answer is incorrect but still plausible
  - `distractor-sentences`: List of sentence IDs that make the distractor plausible
  - `sufficient_article_ids`: A combination of news articles that provide enough evidence to answer the question
  - `all_sufficient_article_id_combinations`: All possible combinations of news articles that are minimally sufficient to answer the question
- `meta`: Additional information or model-generated data during the question generation process

**Example Question:**
````json
{
    "timeline_id": "local-news:12:8",
    "question_id": "2cc1b8c634720006f472573d52690230542632cb19669fcbaed2d7c06a5f7770",
    "parent_question_id": null,
    "evidence_ids": [
        "N1-S16",
        "N0-S18"
    ],
    "answer": "47 days",
    "created_at": 1,
    "category": "time-span",
    "distractors": [
        {
            "answer": "30 days",
            "explanation": "This is incorrect because it assumes the system was expected to be operational at the start of December instead of the end of November, leading to a shorter duration.",
            "distractor-sentences": [
                "N0-S18",
                "N1-S16"
            ]
        },
        {
            "answer": "60 days",
            "explanation": "This is incorrect because it assumes the system was expected to be operational at the start of November instead of the end of November, leading to an overestimation of the duration.",
            "distractor-sentences": [
                "N0-S18",
                "N1-S16"
            ]
        },
        ...
    ],
    "date": "2023-12-15",
    "sufficient_article_ids": [
        "local-news_12_8-ev0-1",
        "local-news_12_8-ev1-0"
    ],
    "all_sufficient_article_id_combinations": [
        [
            "local-news_12_8-ev0-1",
            "local-news_12_8-ev1-0"
        ],
        ...
    ],
    "question": "What is the total duration between the expected operational date of the Birchwalk Commons surveillance system and the completion of repairs and reinstallation of the cameras, as described in the selected sentences?",
    "answer_options": [
        "47 days",
        "30 days",
        "60 days",
        "45 days",
        "50 days",
        "40 days",
        "Unanswerable"
    ],
    "meta": ...
}
````

## 📚 QA Instances
In NeoQA, **QA instances** are generated by combining questions with preselected evidence documents. These instances are designed to evaluate how well a model can answer a question based on the available evidence.

Each **QA instance** extends a `question` and includes additional properties to capture the unique context of each combination of question and evidence. The properties are as follows:
- **`instance_id`**: A unique identifier for each instance. The same question can be used to create multiple instances, each with a different set of evidence.
- **`answerable`**: A label that categorizes whether the QA instance is answerable. If it is not answerable, the label specifies whether the lack of an answer is due to insufficient evidence or because the question is unanswerable.
- **`answer_options`**: The list of possible answer choices. When using the Hugging Face dataset, the options are pre-shuffled. For the downloaded dataset, the options will be shuffled during the loading process.
- **`gold_answer_idx`**: The correct (0-based) index of the answer in the `answer_options` list. This is preset in the Hugging Face dataset, and for the downloaded dataset, it will be determined after shuffling.
- **`use_evidence_documents`**: A list of evidence documents associated with this instance. This can either be the IDs of the news articles (for downloaded data) or the actual news article objects (for the Hugging Face dataset).

**Example QA Instance:**
````json
{
   ... properties from question,
  "instance_id": "4128beb659e98ed30d4bf888d5d7095cb66c5d985d46e0da7d9937ae65b315fd",
  "answerable": "answerable-insufficient",
  "use_evidence_documents": [
        "local-news_12_8-ev1-8"
    ],
   "answer_options": [
        "8 months",
        "6 months",
        "7 months",
        "9 months",
        "10 months",
        "5 months",
        "Unanswerable"
    ],
}
````