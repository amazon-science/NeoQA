"""
run_qwen25.py

Usage:
  run_qwen25.py tune <model_size> <template_name> <parser>
  run_qwen25.py main <model_size> <template_name> <parser>
  run_qwen25.py context <model_size> <template_name> <parser>

Arguments:
  <model_size>      Size of the model
  <template_name>   The name of the template to use for tuning.
  <parser>          The parser to use during the tuning process.

Options:
  -h --help         Show this screen.
  --version         Show version.
"""

from docopt import docopt

from experiments.data.neoqa_loader import NeoQALoader

from experiments.llms.impl.qwen25 import Qwen25
from experiments.llms.llm import LLM
from experiments.running.run_and_eval import run_and_eval_multiple_choice


def eval_prompt_selection(llm: LLM, template_name: str, parser_name: str):
    run_and_eval_multiple_choice(
        llm=llm,
        template_name=template_name,
        parser_name=parser_name,
        data_variant=NeoQALoader.BENCHMARK_WITHOUT_NOISE,
        data_split='dev',
        random_seed=1
    )


def main_benchmark(llm: LLM, template_name: str, parser_name: str):
    run_and_eval_multiple_choice(
        llm=llm,
        template_name=template_name,
        parser_name=parser_name,
        data_variant=NeoQALoader.BENCHMARK,
        data_split='test',
        random_seed=1
    )


def context_length_ablation(llm: LLM, template_name: str, parser_name: str):
    run_and_eval_multiple_choice(
        llm=llm,
        template_name=template_name,
        parser_name=parser_name,
        data_variant=NeoQALoader.CONTEXT_ABL_80_20,
        data_split='test',
        random_seed=1
    )


def get_qwen25(model_size: str) -> LLM:
    model_size = model_size.lower()

    if model_size == '7b':
        weights_path = 'Qwen/Qwen2.5-7B-Instruct'
    elif model_size == '14b':
        weights_path = 'Qwen/Qwen2.5-14B-Instruct'
    elif model_size == '32b':
        weights_path = 'Qwen/Qwen2.5-32B-Instruct'
    else:
        raise ValueError

    return Qwen25(weights_path)


def main(args):

    llm: LLM = get_qwen25(args['<model_size>'])
    template_name: str = args['<template_name>']
    parser_name: str = args['<parser>']

    if args['tune']:
        eval_prompt_selection(llm, template_name, parser_name)
    elif args['main']:
        main_benchmark(llm, template_name, parser_name)
    elif args['context']:
        context_length_ablation(llm, template_name, parser_name)


if __name__ == "__main__":
    args = docopt(__doc__, version="run_qwen25.py 1.0")
    main(args)

