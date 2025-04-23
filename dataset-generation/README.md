# NeoQA Dataset Construction

> **Note:** This is experimental code that was used to produce the NeoQA dataset. The code provided is only supplementary to our publication.

## Overview

The process of generating the NeoQA dataset involves several steps. The general workflow is as follows:

1. **Generate Seed Data**: Seed data is created as the foundational building block for generating timelines, questions, and news articles.
2. **Generate Timelines, Questions, and News Articles**: Based on the seed data, timelines, questions, and news articles are generated.
3. **Aggregate the Data**: Finally, all the generated components (timelines, questions, news articles) are aggregated into a structured dataset.

---

## 🌱 Step 1: Generate Seed Data

This step outlines the process of generating seed data, which serves as the foundation for all subsequent stages.

### 1.1 Generate subevents 
First, generate a set of fine-grained subevents for each event category (e.g., politics, technology, sports). These subevents will later be assembled into full timelines.
````shell
 python generate_stories_seeds.py seed-events
````
### 1.2 Generate summary sentences
Next, for each subevent, generate generic single-sentence summaries of such an event.
````shell
 python generate_stories_seeds.py seed-summaries
````

### 1.3 Finalize
Finally, pack them into batches so that they can be sampled to generate complete timelines.
````shell
 python generate_stories_seeds.py extract-all
````


## ✏️ Step 2: Generate Timelines, Questions, and News

In this step, timelines, questions, and news articles are generated based on the seed data from **Step 1**.

To generate the data, run:
```bash
python generate_full_from_batches.py <batch_name>
```
Where ``<batch_name>`` refers to one of the files in the outputs/seed-batches/ directory.
Example: ``batch-01.jsonl``


## Step 3: 📦 Finalizing the Dataset

The final step involves aggregating all generated timelines, questions, and news articles into a structured dataset that can be used for training, evaluation, or further experimentation.
To finalize the dataset, run the following commands **in order**:

```bash
python export_final_dataset.py collect [<name>]
python export_final_dataset.py add-question-news-links <question_source_file> [<name>]
python export_final_dataset.py main [<name>]
python export_final_dataset.py context-ablation [<name>]
python export_final_dataset.py export [<name>]
````

 The ``<name>`` parameter is optional. If omitted, the current date will be used as the dataset name.

## Installation

To set up the project and its environment, run:

```bash
conda env create -f environment.yml
```
---
