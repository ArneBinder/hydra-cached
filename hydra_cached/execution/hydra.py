from __future__ import annotations

import copy
import dataclasses
import logging
from datetime import datetime
from typing import Any, Union, Optional

import joblib
from hydra._internal.instantiate._instantiate2 import _prepare_input_dict, _Keys, _is_target, _resolve_target, \
    _call_target, _convert_target_to_string
from hydra.errors import InstantiationException
from hydra.types import ConvertMode, TargetConf
from omegaconf import OmegaConf, SCMode, DictConfig
from omegaconf._utils import is_structured_config

from hydra_cached.execution.caching import Cache, InMemoryCache
from hydra_cached.execution.hydra_utils import InstantiatedNodeInfo, InstantiatedNode

logger = logging.getLogger(__name__)

DONT_CACHE = "DISABLED"

convert_target_to_string = _convert_target_to_string


def instantiate(config: Any, *args: Any, cache: Optional[Union[Cache, str]] = None, **kwargs: Any) -> Any:
    f"""
    This method is very similar to `hydra.utils.instantiate`, but allows to use a cache to
    avoid recalculation of items that are defined several times within a config.
    
    Per default, it uses a simple in memory cache `InMemoryCache`. 
    
    Caching can be disabled by passing the string "{DONT_CACHE}" as cache.
    
    Functions used as _target_ (see hydra instantiate) can be annotated with the decorator 
    `@not_deterministic`. This sets a flag in the corresponding InstantiatedNodeInfo of the respective 
    config node and all node instantiations that depend on that (entries that are higher up in the config tree). 
    These info objects are passed to the cache and can be taken into account for cache persistence etc. when 
    implementing a cache that allows for that functionality.  
    
    :param config: An config object describing what to call and what params to use.
                   In addition to the parameters, the config must contain:
                   _target_ : target class or callable name (str)
                   And may contain:
                   _args_: List-like of positional arguments to pass to the target
                   _recursive_: Construct nested objects as well (bool).
                                True by default.
                                may be overridden via a _recursive_ key in
                                the kwargs
                   _convert_: Conversion strategy
                        none    : Passed objects are DictConfig and ListConfig, default
                        partial : Passed objects are converted to dict and list, with
                                  the exception of Structured Configs (and their fields).
                        all     : Passed objects are dicts, lists and primitives without
                                  a trace of OmegaConf containers
                   _args_: List-like of positional arguments
                   _cache_result_: If a cache is available, add to it the result of the 
                                   construction. The config is used as key.
                                   True by default.
    :param args: Optional positional parameters pass-through
    :param cache: A cache object that fallows the interface defined in Cache or the . Defaults to InMemoryCache.
    :param kwargs: Optional named parameters to override
                   parameters in the config object. Parameters not present
                   in the config objects are being passed as is to the target.
                   IMPORTANT: dataclasses instances in kwargs are interpreted as config
                              and cannot be used as passthrough
    :return: if _target_ is a class name: the instantiated object
             if _target_ is a callable: the return value of the call
    """

    # Return None if config is None
    if config is None:
        return None

    # TargetConf edge case
    if isinstance(config, TargetConf) and config._target_ == "???":
        # Specific check to give a good warning about failure to annotate _target_ as a string.
        raise InstantiationException(
            f"Missing value for {type(config).__name__}._target_. Check that it's properly annotated and overridden."
            f"\nA common problem is forgetting to annotate _target_ as a string : '_target_: str = ...'"
        )

    if isinstance(config, dict):
        config = _prepare_input_dict(config)

    kwargs = _prepare_input_dict(kwargs)

    # Structured Config always converted first to OmegaConf
    if is_structured_config(config) or isinstance(config, dict):
        config = OmegaConf.structured(config, flags={"allow_objects": True})

    if OmegaConf.is_dict(config):
        # Finalize config (convert targets to strings, merge with kwargs)
        config_copy = copy.deepcopy(config)
        config_copy._set_flag(
            flags=["allow_objects", "struct", "readonly"], values=[True, False, False]
        )
        config_copy._set_parent(config._get_parent())
        config = config_copy

        if kwargs:
            config = OmegaConf.merge(config, kwargs)

        OmegaConf.resolve(config)

        _recursive_ = config.pop(_Keys.RECURSIVE, True)
        _convert_ = config.pop(_Keys.CONVERT, ConvertMode.NONE)
        if cache is None:
            cache = InMemoryCache[DictConfig, InstantiatedNode](verbose=False)
        elif cache == DONT_CACHE:
            logger.warning(f"caching is disabled because cache={DONT_CACHE}")
            cache = None
        elif isinstance(cache, Cache):
            pass
        else:
            raise ValueError(f'cache has to be either an instance of Cache, None (use default InMemoryCache) or the '
                             f'string "{DONT_CACHE}" which implies no caching at all')
        instantiated_node = instantiate_node(config, *args, recursive=_recursive_, convert=_convert_, cache=cache)
        return instantiated_node.instance
    else:
        raise InstantiationException(
            "Top level config has to be OmegaConf DictConfig, plain dict, or a Structured Config class or instance"
        )


def _convert_node(node: Any, convert: Union[ConvertMode, str]) -> Any:
    if OmegaConf.is_config(node):
        if convert == ConvertMode.ALL:
            node = OmegaConf.to_container(node, resolve=True)
        elif convert == ConvertMode.PARTIAL:
            node = OmegaConf.to_container(
                node, resolve=True, structured_config_mode=SCMode.DICT_CONFIG
            )
    return node


def instantiate_node(
    node: Any,
    *args: Any,
    convert: Union[str, ConvertMode] = ConvertMode.NONE,
    recursive: bool = True,
    cache: Optional[Cache] = None,
) -> InstantiatedNode:
    # Return None if config is None
    if node is None or (OmegaConf.is_config(node) and node._is_none()):
        return InstantiatedNode(instance=None)

    if not OmegaConf.is_config(node):
        return InstantiatedNode(instance=node)

    # Override parent modes from config if specified
    if OmegaConf.is_dict(node):
        # using getitem instead of get(key, default) because OmegaConf will raise an exception
        # if the key type is incompatible on get.
        convert = node[_Keys.CONVERT] if _Keys.CONVERT in node else convert
        recursive = node[_Keys.RECURSIVE] if _Keys.RECURSIVE in node else recursive

    if not isinstance(recursive, bool):
        raise TypeError(f"_recursive_ flag must be a bool, got {type(recursive)}")

    # If OmegaConf list, create new list of instances if recursive
    if OmegaConf.is_list(node):
        instantiated_nodes = [
            instantiate_node(item, convert=convert, recursive=recursive, cache=cache)
            for item in node._iter_ex(resolve=True)
        ]
        items = [item.instance for item in instantiated_nodes]
        infos = {i: item.info for i, item in enumerate(instantiated_nodes)}
        info = InstantiatedNodeInfo.combine(infos, parent_config=node)

        if convert in (ConvertMode.ALL, ConvertMode.PARTIAL):
            # If ALL or PARTIAL, use plain list as container
            result = items
        else:
            # Otherwise, use ListConfig as container
            lst = OmegaConf.create(items, flags={"allow_objects": True})
            lst._set_parent(node)
            result = lst
        return InstantiatedNode(instance=result, info=info)

    elif OmegaConf.is_dict(node):
        infos = {}
        exclude_keys = set({"_target_", "_convert_", "_recursive_", "_cache_result_", "_result_hash_"})
        if _is_target(node):
            if cache is not None:
                if node in cache:
                    return cache[node]

            target = _resolve_target(node.get(_Keys.TARGET))
            target_info = InstantiatedNodeInfo.from_func(target, cache_result=node.get("_cache_result_", True))
            kwargs = {}
            for key, value in node.items():
                if key not in exclude_keys:
                    if recursive:
                        instantiated_node = instantiate_node(
                            value, convert=convert, recursive=recursive, cache=cache
                        )
                        value = instantiated_node.instance
                        infos[key] = instantiated_node.info
                    kwargs[key] = _convert_node(value, convert)

            # If the current target function is deterministic...
            if not target_info.not_deterministic:
                # ... we can create the result info object before execution ...
                result_info = InstantiatedNodeInfo.combine(infos, target_info=target_info, parent_config=node)
                # ... and check, if we already have a matching result in the cache.
                # An deterministic_config only exists, if it would be different from the original config (which we
                # already queried the cache for above). So it is fine to query it, if it is there.
                if result_info.deterministic_config is not None:
                    if cache is not None and result_info.deterministic_config in cache:
                        return cache[result_info.deterministic_config]
                    # add that as a cache key for the (to be calculated) result of the target function
                    cache_key = result_info.deterministic_config
                else:
                    cache_key = node
            else:
                cache_key = node
                result_info = None

            t_start = datetime.now()
            result_instance = _call_target(target, *args, **kwargs)
            t_delta = datetime.now() - t_start
            # If the target function is not deterministic, we were not able to calculate the info object beforehand.
            # In this case, we set a dummy deterministic config that just contains the hash of the result.
            if result_info is None:
                h = joblib.hash(result_instance)
                result_info = InstantiatedNodeInfo.combine(
                    infos,
                    target_info=target_info,
                    # TODO: check omega config creation (set any flags? parent correct?)
                    deterministic_config=OmegaConf.structured(obj={"_result_hash_": h}, parent=node._parent)
                )
            result_info = dataclasses.replace(result_info, time_target=t_delta)
            result = InstantiatedNode(instance=result_instance, info=result_info)
            if cache is not None and result.info.cache_result:
                cache[cache_key] = result
                # if the target function was not deterministic (in that case cache_key was set to
                # result_info.deterministic_config, but we check if it is != node since there may be None cases),
                # but any child was, we also add the result at the original config to the cache, but we remember that
                # this is not_deterministic.
                if cache_key != node:
                    result_not_deterministic = InstantiatedNode(
                        instance=result_instance, info=dataclasses.replace(result_info, not_deterministic=True)
                    )
                    cache[node] = result_not_deterministic
            return result
        else:
            # If ALL or PARTIAL non structured, instantiate in dict and resolve interpolations eagerly.
            if convert == ConvertMode.ALL or (
                convert == ConvertMode.PARTIAL and node._metadata.object_type is None
            ):
                dict_items = {}
                for key, value in node.items():
                    # list items inherits recursive flag from the containing dict.
                    instantiated_node = instantiate_node(
                        value, convert=convert, recursive=recursive, cache=cache
                    )
                    dict_items[key] = instantiated_node.instance
                    infos[key] = instantiated_node.info
                return InstantiatedNode(instance=dict_items,
                                        info=InstantiatedNodeInfo.combine(infos, parent_config=node))
            else:
                # Otherwise use DictConfig and resolve interpolations lazily.
                cfg = OmegaConf.create({}, flags={"allow_objects": True})
                for key, value in node.items():
                    instantiated_node = instantiate_node(
                        value, convert=convert, recursive=recursive, cache=cache
                    )
                    cfg[key] = instantiated_node.instance
                    infos[key] = instantiated_node.info
                cfg._set_parent(node)
                cfg._metadata.object_type = node._metadata.object_type
                return InstantiatedNode(instance=cfg,
                                        info=InstantiatedNodeInfo.combine(infos, parent_config=node))

    else:
        assert False, f"Unexpected config type : {type(node).__name__}"
