import json
from os import makedirs
from os.path import join, exists
from typing import List, Dict, Set

import torch
from datasets import Dataset
from torch.utils.data import DataLoader
from tqdm import tqdm
from transformers import Pipeline, AutoModelForCausalLM, AutoTokenizer

from experiments.data.neoqa_loader import NeoQALoader
from experiments.evaluate.evaluate import evaluate_file
from experiments.llms.llm import LLM
from experiments.parsing.last_line_output_parser import LastLineOutputParser
from experiments.parsing.multiple_choice_json_output_parser import MultipleChoiceJsonOutputParser
from experiments.parsing.ouput_parser import OutputParser
from experiments.prompter.mcq_prompt_generator import MultipleChoicePromptGenerator
from experiments.prompter.prompt_generator import PromptGenerator
from experiments.util.file_util import store_jsonl, store_json, read_jsonl, append_jsonl


def collate_fn(batch, device, tokenizer):
    prompts = [instance['prompt'] for instance in batch]
    messages_batch = [[{"role": "user", "content": prompt}] for prompt in prompts]

    # Apply chat template to the whole batch at once
    input_tensors = tokenizer.apply_chat_template(
        messages_batch,
        add_generation_prompt=True,
        return_tensors="pt",
        padding=True  # Important: Add padding for batching
    )

    # Move input tensors to the device
    input_tensors = input_tensors.to(device)
    original_batch = [{k:v for k,v in instance.items()} for instance in batch]
    for instance in original_batch:
        instance['news_articles'] = [article['article_id'] for article in instance['news_articles']]

    return input_tensors, original_batch


def run_and_eval_multiple_choice_with_batches(
        model: AutoModelForCausalLM, tokenizer: AutoTokenizer, batch_size: int, model_name: str,
        template_name: str, parser_name: str, data_variant: str, data_split: str, random_seed: int
):
    parser: OutputParser
    if parser_name == 'last-line':
        parser = LastLineOutputParser(7)
    elif parser_name == 'json':
        parser = MultipleChoiceJsonOutputParser(7)
    else:
        raise NotImplementedError(parser_name)

    loader: NeoQALoader = NeoQALoader(data_variant)
    prompt_generator: PromptGenerator = MultipleChoicePromptGenerator(template_name)

    dataset: Dataset = loader.get(data_split, random_seed=random_seed)
    dataset_with_prompts: Dataset = dataset.map(prompt_generator.get_prompt, load_from_cache_file=False)

    model_dir: str = model_name.replace('/', '--')
    out_directory: str = f'./results/{model_dir}/{data_variant}/{template_name.replace(".txt", "")}'
    makedirs(out_directory, exist_ok=True)

    # Fail early! Start with largest context
    dataset_with_prompts = dataset_with_prompts.sort('prompt_len', reverse=True)
    dataloader = DataLoader(
        dataset_with_prompts,
        batch_size=batch_size,
        collate_fn=lambda batch: collate_fn(batch, model.device, tokenizer)
    )

    all_results = []
    for batch, instances in tqdm(dataloader):
        with torch.no_grad():  # Important for inference
            outputs = model.generate(
                batch,
                max_new_tokens=3000,
                do_sample=False,
                temperature=None,
                top_p=None,
                pad_token_id=tokenizer.eos_token_id, eos_token_id=tokenizer.eos_token_id
            )
            start_indices = batch.shape[1]  # Correctly compute start indices
            for i in range(outputs.shape[0]):  # Iterate through the batch dimension
                response = tokenizer.decode(outputs[i][start_indices:], skip_special_tokens=True)
                predicted_answer: int = parser.select_answer(response, instances[i]['options'])['answered']
                instances[i]['response'] = response
                instances[i]['predicted_answer'] = predicted_answer
                all_results.append(instances[i])

    out_path: str = join(out_directory, f'{data_split}.seed-{random_seed}.predictions.jsonl')
    store_jsonl(all_results, out_path)

    metrics = evaluate_file(out_path)
    store_json(metrics, join(out_directory, f'{data_split}.seed-{random_seed}.metrics.json'), pretty=True)
    print('ADTScore:', json.dumps(metrics['adt_score'], indent=2))
    return metrics


def run_and_eval_multiple_choice(
        llm: LLM, template_name: str, parser_name: str, data_variant: str, data_split: str, random_seed: int
):

    parser: OutputParser
    if parser_name == 'last-line':
        parser = LastLineOutputParser(7)
    elif parser_name == 'json':
        parser = MultipleChoiceJsonOutputParser(7)
    else:
        raise NotImplementedError(parser_name)

    loader: NeoQALoader = NeoQALoader(data_variant)
    prompt_generator: PromptGenerator = MultipleChoicePromptGenerator(template_name)

    dataset: Dataset = loader.get(data_split, random_seed=random_seed)
    dataset_with_prompts: Dataset = dataset.map(prompt_generator.get_prompt, load_from_cache_file=False)

    # Fail early! Start with largest context
    dataset_with_prompts = dataset_with_prompts.sort('prompt_len', reverse=True)

    model_dir: str = llm.get_name().replace('/', '--')
    out_directory: str = f'./results/{model_dir}/{data_variant}/{template_name.replace(".txt", "")}'
    makedirs(out_directory, exist_ok=True)

    out_path: str = join(out_directory, f'{data_split}.seed-{random_seed}.predictions.jsonl')

    if exists(out_path):
        already_predicted: Set[str] = {
            pred['instance_id'] for pred in read_jsonl(out_path)
        }
    else:
        already_predicted = set()

    for instance in tqdm(dataset_with_prompts):
        if instance['instance_id'] not in already_predicted:
            response: str = llm.generate(instance)
            predicted_answer: int = parser.select_answer(response, instance['options'])['answered']
            instance['response'] = response
            instance['predicted_answer'] = predicted_answer

            # So that we do not store all the news articles.
            instance['news_articles'] = [article['article_id'] for article in instance['news_articles']]
            append_jsonl(instance, out_path)

    metrics = evaluate_file(out_path)
    store_json(metrics, join(out_directory, f'{data_split}.seed-{random_seed}.metrics.json'), pretty=True)
    print('ADTScore:', json.dumps(metrics['adt_score'], indent=2))
    return metrics
