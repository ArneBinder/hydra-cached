from __future__ import annotations

import copy
import logging
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any, Callable, Optional, Dict

from omegaconf import OmegaConf

logger = logging.getLogger(__name__)


KEY_INFO = "__info"


@dataclass(frozen=True)
class FuncInfo:
    """
    Object that can be attached to functions, e.g. to mark them as not deterministic
    (see decorator `not_deterministic`).
    """
    not_deterministic: bool = False

    @staticmethod
    def from_func(func: Callable) -> FuncInfo:
        return getattr(func, KEY_INFO) if hasattr(func, KEY_INFO) else FuncInfo()

    def to_func(self, func: Callable):
        if hasattr(func, KEY_INFO):
            info = getattr(func, KEY_INFO)
            assert isinstance(info, FuncInfo), \
                f'function {func} already has an attribute "{KEY_INFO}", but not with a {FuncInfo.__name__} object'
            logger.warning(f'function {func} already has an attribute "{KEY_INFO}" with value: {info}. This will be '
                           f'overwritten!')
        setattr(func, KEY_INFO, self)


@dataclass(frozen=True)
class InstantiatedNodeInfo:
    # This describes just the target callable of this node, not if any child / ancestor node is not deterministic!
    # In the later case, deterministic_config would be _not_ None.
    not_deterministic: bool = False
    cache_result: bool = True
    # This is only set, if this node depends (recursively) on any node that is not deterministic.
    deterministic_config: Optional[OmegaConf] = None
    time_target: Optional[timedelta] = None

    @staticmethod
    def combine(
        infos: Dict[Any, InstantiatedNodeInfo],
        parent_config: Optional[OmegaConf] = None,
        target_info: Optional[InstantiatedNodeInfo] = None,
        deterministic_config: Optional[OmegaConf] = None,
    ) -> InstantiatedNodeInfo:
        """
        logic how to combine multiple InstantiatedNodeInfo objects.

        :param infos: dict containing InstantiatedNodeInfo objects
        :param parent_config:
        :param target_info:
        :param deterministic_config:
        :return: the merged InstantiatedNodeInfo object
        """
        # This might set deterministic_config, if any child has one.
        if deterministic_config is None:
            assert parent_config is not None, \
                f'parent_config is required when combining InstantiatedNodeInfo object and not deterministic_config ' \
                f'is provided'
            for k, info in infos.items():
                if info.deterministic_config is not None:
                    if deterministic_config is None:
                        deterministic_config = copy.copy(parent_config)
                    deterministic_config[k] = info.deterministic_config

        _not_deterministic = False
        infos_list = list(infos.values())
        if target_info is not None:
            infos_list.append(target_info)
            _not_deterministic = target_info.not_deterministic
        _cache_result = all([info.cache_result for info in infos_list])
        return InstantiatedNodeInfo(cache_result=_cache_result, deterministic_config=deterministic_config,
                                    not_deterministic=_not_deterministic)

    @staticmethod
    def from_func_info(func_info: FuncInfo, not_deterministic: Optional[bool] = None, **kwargs) -> InstantiatedNodeInfo:
        if not_deterministic is None:
            not_deterministic = func_info.not_deterministic
        return InstantiatedNodeInfo(not_deterministic=not_deterministic, **kwargs)

    @staticmethod
    def from_func(func: Callable, **kwargs) -> InstantiatedNodeInfo:
        return InstantiatedNodeInfo.from_func_info(FuncInfo.from_func(func), **kwargs)


@dataclass(frozen=True)
class InstantiatedNode:
    """
    Wrapper class to hold the actual instantiated node and an InstantiatedNodeInfo object.
    """
    instance: Any
    info: InstantiatedNodeInfo = field(default_factory=InstantiatedNodeInfo)


def not_deterministic(func):
    """
    This is a decorator to mark functions as "not deterministic".

    :param func: the function to annotate
    :return: the annotated function
    """

    FuncInfo(not_deterministic=True).to_func(func=func)
    return func


