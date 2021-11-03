import logging
from typing import Dict

from hydra_cached.execution.caching.interface import Cache, TK, TV

logger = logging.getLogger(__name__)


class InMemoryCache(Cache[TK, TV]):

    def __init__(self, verbose: bool = False):
        self.store: Dict[TK, TV] = {}
        self.verbose: bool = verbose

    def __contains__(self, key: TK) -> bool:
        res = key in self.store
        if self.verbose:
            logger.info(f'lookup cache ({"HIT" if key in self.store else "MISS"}): {key}')
        return res

    def __getitem__(self, key: TK) -> TV:
        return self.store[key]

    def __setitem__(self, key: TK, value: TV):
        if self.verbose:
            logger.info(f'add to cache: {key}')
        self.store[key] = value
