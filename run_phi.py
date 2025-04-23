"""
run_phi.py

Usage:
  run_phi.py tune <model_size> <template_name> <parser>
  run_phi.py main <model_size> <template_name> <parser>
  run_phi.py context <model_size> <template_name> <parser>

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
from experiments.llms.impl.phi import Phi
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


def get_phi(model_size: str) -> LLM:
    model_size = model_size.lower()
    if model_size == 'phi4-14b':
        weights_path = 'microsoft/phi-4'
    elif model_size == 'phi3-mini':
        weights_path = 'microsoft/phi-3-mini-128k-instruct'
    elif model_size == 'phi3-small':
        weights_path = 'microsoft/phi-3-small-128k-instruct'
    elif model_size == 'phi3-medium':
        weights_path = 'microsoft/phi-3-medium-128k-instruct'
    elif model_size == 'phi35-moe':
        weights_path = 'microsoft/Phi-3.5-MoE-instruct'
    else:
        raise ValueError(model_size)

    return Phi(weights_path)


def main(args):

    llm: LLM = get_phi(args['<model_size>'])
    template_name: str = args['<template_name>']
    parser_name: str = args['<parser>']
    #  <template_name> <parser>
    if args['tune']:
        eval_prompt_selection(llm, template_name, parser_name)
    elif args['main']:
        main_benchmark(llm, template_name, parser_name)
    elif args['context']:
        context_length_ablation(llm, template_name, parser_name)


if __name__ == "__main__":
    args = docopt(__doc__, version="run_phi.py 1.0")
    main(args)

