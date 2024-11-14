## Project Structure
- LLM queries and their results will be stored in sqlite databases within the [cache](cache) directory to avoid sending identical queries via the API to the LLM (if they share the same parameters such as seed or max length).
- The outputs during the generation of the events, questions and answers are stored in thr [outputs](outputs) directory. Each distinct storyline has one directory.
- The actual datasets derived from these outputs are stored in the [generated-datasets](generated-datasets) directory.

## Install
Run:
```bash
conda env create -f environment.yml
```
## How to generate seed data from scratch:
First, we need to generate different event types for all the different genres:
```bash
PYTHONPATH=src python generate_stories_seeds.py seed-events
```
This will produce seed event types in the [outputs/seed-event-types](outputs/seed-event-types) directory.

Second, generate concrete seed sentences for very specific events:
```bash
PYTHONPATH=src python generate_stories_seeds.py seed-summaries
```
This will produce seed event types in the [outputs/seed-summaries](outputs/seed-summaries) directory.


Third, collect all the seed summaries into the right format, that is required to generate storylines:
```bash
PYTHONPATH=src python generate_stories_seeds.py extract-all 
```
This btch files in the [outputs/seed-batches](outputs/seed-batches) directory.


## The Quick guide to only generate more data and care about nothing else

### Step 1: Get the seed data.
To generate storylines, the LLM requires seed information about the genre, the seed summary for the first event (and some other information for consistency and identification). The input looks like:
```json
{
  "summary": "Luxury fashion brands are increasingly incorporating recycled ocean plastics into their haute couture collections, blending sustainability with high-end design.",
  "genre": "Lifestyle",
  "event_type": {
    "category": "Celebrity Fashion Trends",
    "event_type_id": "lifestyle:0"
  },
  "event_type_id": "lifestyle:0",
  "story_seed_id": "lifestyle:0:1",
  "init_random_seed": 735843
}
```
We have enough of these seed entries stored in the [outputs/seed-batches/](outputs/seed-batches) directory. Make sure they are included.

### Step 2: Generate the storyline with the questions and news articles
1. Select one of the files within [outputs/seed-batches/](outputs/seed-batches). Each file contains many seed entries. these seed entries will be used to sequentially generate data.
    - I started in parallel with the batches [batch-01.jsonl](outputs/seed-batches/batch-01.jsonl) and [batch-02.jsonl](outputs/seed-batches/batch-02.jsonl) (they can be continued)
2. Generate the data by running `PYTHONPATH=src python generate_full_from_batches.py <batch_name>`. Replace `<batch_name>` with the chosen file name (e.g., `batch-01.jsonl`).
   - This will produce new data in the [outputs/storylines-final4/<name-of-the-story>](outputs/storylines-final4) directories.
   - In some cases the storyline generation breaks before it reaches the last (10th) event. These will be skipped.


### Step 3: Aggregate all into one final dataset
This consists of three steps:
1. **Pack** all the generated data into one .jsonl file that includes events, KBs, questions, news.
2. **Filter** all (answerable) questions that cannot be answered by CLaude based on optimal evidence. (*can be skipped but then we have more noise*)
3. **Assemble** different questions and evidence documents under various settings. This, I can improve. I think we can be smarter about how we want to assemble the evidence with the news.

#### Pack
To create a single `dataset.jsonl` file run:
```bash
PYTHONPATH=src python export_final_dataset.py pack <name>
```
This will produce a `dataset.jsonl` file based on all complete storylines (with all questions, and evidence). It will be stored within the [generated-datasets/<name-you-selected>](generated-datasets) directory.


#### Filter
To create a single `filtered-dataset.jsonl` file run:
```bash
PYTHONPATH=src python export_final_dataset.py filter <name>
```
It will remove all answers questions that cannot be answered by Claude based on optimal evidence from the outline.

#### Assemble
To create actual samples that combine questions with evidence documents, run:
```bash
PYTHONPATH=src python export_final_dataset.py create-samples <name> [<num_questions_per_type>]
```
It will produce various .jsonl files with question-evidence pairs under different conditions. If you do not specify `<num_questions_per_type>`, all questions will be used. If you specify `<num_questions_per_type>`, for each question type and each event, only this many questions will be sampled.


## The quick guide to run the experiments and care about nothing else
Make sure that you have .jsonl files that contain instances for inference. For example, for the generated dataset with the name `1410`, there should be various jsonl files within `generated-datasets/1410/<subset-name>/*`

Example: `generated-datasets/1410/subset-30/insufficient-evidence_max-noise-0_articles.jsonl`

Run:
```bash
PYTHONPATH=src python run_timeless.py all claude-35 1410/subset-30
```

This will use Claude 3.5 to make inference over all .jsonl files within the `generated-datasets/1410/subset-30/` directory. The predictions and metrics will be stored in the [predictions](predictions) directory.
You can use these models:
- `claude-35`  for Claude 3.5
- `llama31-8b` for Llama 3.1 8B (meta.llama3-1-8b-instruct-v1:0)
- `llama31-70b` for Llama 3.1 70B (meta.llama3-1-70b-instruct-v1:0)

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the LICENSE NAME HERE License.

