import glob
import logging
import pickle as pkl
from datetime import timedelta
from os import makedirs, path
from typing import Callable, Optional, List, Type, Union
from typing import Iterable

import joblib
from hydra._internal.instantiate._instantiate2 import _convert_target_to_string
from omegaconf import OmegaConf, DictConfig

from hydra_cached.execution.caching.interface import TV
from hydra_cached.execution.caching.memory import InMemoryCache
from hydra_cached.execution.hydra_utils import InstantiatedNode

logger = logging.getLogger(__name__)


class DumpableInMemoryCache(InMemoryCache[DictConfig, TV]):
    """
    Similar to InMemoryCache, but has a `dump` and `load` method. If a directory is provided
    on initialization, this will directly load the content into the cache.
    """

    def __init__(self, directory: str = None, **kwargs):
        super().__init__(**kwargs)
        self.directory = directory
        if self.directory is not None:
            self.load()

    def load(
        self,
        directory: str = None,
        constraints: Optional[Iterable[Callable[[DictConfig, TV], Optional[str]]]] = None
    ):
        if directory is None:
            directory = self.directory
        file_names = glob.glob(path.join(directory, f'*.pkl'))
        if self.verbose:
            logger.info(f'load {len(file_names)} files from cache directory: {directory}')
        for fn in file_names:
            with open(fn, 'rb') as f:
                v = pkl.load(f)
            config_fn = path.splitext(fn)[0] + '.yaml'
            k = OmegaConf.load(config_fn)
            if constraints is not None:
                skip = False
                for c in constraints:
                    constraint_error_message = c(k, v)
                    if constraint_error_message is not None:
                        if self.verbose:
                            logger.warning(constraint_error_message)
                        skip = True
                if skip:
                    continue
            self[k] = v

        logger.info(f'loaded {len(self.store)} entries into the cache')

    def dump(
        self,
        directory: str = None,
        constraints: Optional[Iterable[Callable[[DictConfig, TV], Optional[str]]]] = None,
        overwrite: bool = False,
    ):
        if directory is None:
            directory = self.directory
        if self.verbose:
            logger.info(f'dump cache to directory ({len(self.store)} entries): "{directory}"')
        if path.exists(directory):
            logger.warning(f'cache dir "{directory}" already exists!')
        n_dumped = 0
        makedirs(directory, exist_ok=True)
        for k, v in self.store.items():
            if constraints is not None:
                skip = False
                for c in constraints:
                    constraint_error_message = c(k, v)
                    if constraint_error_message is not None:
                        if self.verbose:
                            logger.warning(constraint_error_message)
                        skip = True
                if skip:
                    continue
            k_dump = OmegaConf.to_yaml(k) #, sort_keys=True)
            h = joblib.hash(k_dump)
            fn_config = path.join(directory, f'{h}.yaml')
            # To keep initial file creation timestamps, do not overwrite existing files.
            if path.exists(fn_config) and not overwrite:
                if self.verbose:
                    logger.info(f'do not dump cache entry because it already exists: {h} (set overwrite=True to '
                                f'enforce overwrite)')
                continue
            with open(fn_config, "w") as f:
                f.write(k_dump)
            fn_data = path.join(directory, f'{h}.pkl')
            with open(fn_data, "wb") as f:
                pkl.dump(v, f)
            n_dumped += 1

        logger.info(f'dumped {n_dumped} out of {len(self.store)} entries to directory: "{directory}"')


def not_deterministic_constraint(k, v: InstantiatedNode):
    if v.info.not_deterministic:
        return f'don\'t dump/load entry since it is not deterministic: {k}'


def exclude_types_constraint(k, v: InstantiatedNode, exclude_types: List[Type]):
    if type(v.instance) in exclude_types:
        return f'don\'t dump/load entry since its type={type(v.instance)} is in exclude_types={exclude_types}: {k}'


def exclude_targets_constraint(k, v: InstantiatedNode, exclude_targets: List[Union[Callable, Type, str]]):
    exclude_targets_strings = [_convert_target_to_string(target) for target in exclude_targets]
    if k.get("_target_", None) in exclude_targets_strings:
        return f'don\'t dump/load entry since it was created with an excluded target {exclude_targets_strings}: {k}'


def exclude_target_time_none_or_lesser_then(k, v: InstantiatedNode, min_time: timedelta):
    if v.info.time_target is None or v.info.time_target <= min_time:
        return f'don\'t dump/load entry since its target_time {v.info.time_target} is lesser then {min_time}: {k}'
