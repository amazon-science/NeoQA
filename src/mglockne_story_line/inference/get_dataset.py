from typing import Optional

from datasets import Dataset, load_dataset, Features, Value


def get_dataset_timeless(dataset_path: str, seed: int = 1, max_samples: Optional[int] = None) -> Dataset:

    ds: Dataset = load_dataset('json', data_files=dataset_path)['train']
    if max_samples is None:
        return ds
    else:
        shuffled_dataset = ds.shuffle(seed=seed)
        selected_dataset = shuffled_dataset.select(range(max_samples))
        return selected_dataset


