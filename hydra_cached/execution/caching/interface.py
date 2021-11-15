import logging
from typing import TypeVar, Generic

logger = logging.getLogger(__name__)

TV = TypeVar("TV")
TK = TypeVar("TK")


class Cache(Generic[TK, TV]):
    """
    Cache interface that is required by `execution.hydra.instantiate`.
    """

    def __contains__(self, key: TK) -> bool:
        raise NotImplemented("implement!")

    def __getitem__(self, key: TK) -> TV:
        raise NotImplemented("implement!")

    def __setitem__(self, key: TK, value: TV):
        raise NotImplemented("implement!")

