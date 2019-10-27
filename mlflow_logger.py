import yaml
import torch
from typing import *
from pathlib import Path
import wandb
from  mlflow.tracking import MlflowClient
from utils import *
client = MlflowClient()

class Experiment:
    def __init__(self, name):
        if client.get_experiment_by_name(name) is None:
            client.create_experiment(name)
        self._id = client.get_experiment_by_name(name).experiment_id
        self._run = None
        self._name = name
    def create_run(self, run_name=None):
        return ExperimentRun(self._id, name=self._name,
                             run_name=run_name)
    def get_run(self, run_name=None):
        if self._run is None:
            self._run = self.create_run(run_name=run_name)
        return self._run

class ExperimentRun:
    def __init__(self, experiment_id, name=None, run_name=None):
        self._id = client.create_run(experiment_id).info.run_id
        wandb.init(project=name, name=run_name,
                   allow_val_change=True)
        wandb.config.update({"allow_val_change": True})

    def __getattr__(self, x):
        def func(*args, **kwargs):
            return getattr(client, x)(self._id, *args, **kwargs)
        return func

    def set_tag(self, k, v):
        client.set_tag(self._id, k, v)
        wandb.config.update({k: v}, allow_val_change=True)

    def log_param(self, k, v):
        client.log_param(self._id, k, v)
        wandb.config.update({k: v}, allow_val_change=True)

    def log_metric(self, k, v):
        client.log_metric(self._id, k, v)
        wandb.log({k: v})

    def log_metric_step(self, k, v, step):
        wandb.log({k: v}, step=step)

def parse_results(log_dirs: List[str], prefixes: List[str]=None):
    results = {}
    if prefixes is None:
        prefixes = ["" for _ in log_dirs]
    assert len(prefixes) == len(log_dirs)
    for prefix, log_dir in zip(prefixes, log_dirs):
        results.update(load_results(log_dir, prefix))
    return results

def get_run(
    name: str,
    run_name: str,
    tag: dict={}
):
    experiment = Experiment(name)
    run = experiment.get_run(run_name=run_name)
    for k, v in tag.items():
        run.set_tag(k, v)
    return run

def record(
    name: str,
    configs: Union[List[str], str],
    train_args: str,
    results: Dict[str, Any],
    tag: dict={},
    run_name: str=None,
    metric_log: dict={},
):
    if isinstance(configs, str): configs = [configs]

    experiment = Experiment(name)
    run = experiment.get_run(run_name=run_name)
    # tag
    for k, v in tag.items():
        run.set_tag(k, v)

    for pfile in configs:
        params = load_config(pfile)
        print(f"Params: {params}")
        for k, v in params.items():
            run.log_param(k, v)

    args = torch.load(train_args)
    print(f"Train args: {args}")
    for k, v in vars(args).items():
        run.log_param(k, v)

    print(f"Results: {results}")
    for k, v in results.items():
        run.log_metric(k, float(v))

    for k, vals in enumerate(metric_log.items()):
        for i, v in enumerate(vals):
            run.log_metric_step(k, float(v), step=i)

if __name__ == "__main__":
    import fire
    fire.Fire(record)
