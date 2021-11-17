import argparse
import importlib
import logging
from datetime import timedelta
from functools import partial

from omegaconf import DictConfig

logger = logging.getLogger(__name__)

def main():

    parser = argparse.ArgumentParser(description="Execute a processing pipeline from a config object defined in a "
                                                 "python module.")
    parser.add_argument(
        "config",
        type=str,
        help="Name of the module that has to contain a config dict which will be instantiated via "
             "execution.hydra.instantiate(config)."
    )
    parser.add_argument(
        "--config_object", "-o",
        type=str,
        help="Object from the config module that will be instantiated (default: \"config\").",
        default="config"
    )
    parser.add_argument(
        "--persist_cache", "-p",
        action='store_true',
        help="A flag to enable cache persistence (loading from and dumping to a cache directory, see --cache_dir)",
    )
    parser.add_argument(
        "--cache_dir", "-c",
        type=str,
        help="Cache directory used to load/dump the cache (only relevant if --persist_cache is set). Defaults to "
             "\"cache\"",
        default="cache"
    )
    parser.add_argument(
        "--cache_verbose", "-v",
        help="A flag to enable verbose logging for the cache.",
        action="store_true"
    )
    parser.add_argument(
        "--display_config", "-d",
        action='store_true',
        help="A flag, if enabled, log the config as yaml string to the console.",
    )
    parser.add_argument(
        "--exclude_persisting_targets", "-e",
        type=str,
        default="",
        help="Comma separated list of strings that identify targets to exclude from cache persistence. Use "
             "hydra_cached.execution.hydra.convert_target_to_string() to get the correct string representation "
             "for a callable/class. default: empty string"
    )
    parser.add_argument(
        "--log_level", "-l",
        type=str,
        default="INFO",
        help="Log level for the console logger. default: INFO"
    )

    args = parser.parse_args()

    # initialize here to set log level also for imported modules
    logging.basicConfig(level=logging.getLevelName(args.log_level))

    from hydra_cached.execution.hydra import instantiate, InstantiatedNode
    from hydra_cached.execution.caching import DumpableInMemoryCache, InMemoryCache
    from hydra_cached.execution.caching.dumpable import exclude_targets_constraint, \
        not_deterministic_constraint, exclude_target_time_none_or_lesser_then
    from hydra_cached.execution.yaml_utils import config_to_yaml

    config_module = importlib.import_module(name=args.config)
    config = getattr(config_module, args.config_object)

    if args.display_config:
        logger.info(f'config to instantiate:\n{config_to_yaml(config)}')

    if args.persist_cache:
        logger.warning("USE A DUMPABLE CACHE (i.e. load an already dumped cache, if available, and dump it after "
                       "execution). THIS IS EXPERIMENTAL!")
        cache = DumpableInMemoryCache[InstantiatedNode](directory=args.cache_dir, verbose=args.cache_verbose)
    else:
        # Use an in memory cache to avoid recalculation of re-occurring parts of the config
        cache = InMemoryCache[DictConfig, InstantiatedNode](verbose=args.cache_verbose)

    # put into try/finally to dump all partial results that were calculated so far if an exception occurs
    try:
        result = instantiate(config=config, _convert_='partial', cache=cache)
        print("instantiation done")
    finally:
        if isinstance(cache, DumpableInMemoryCache):
            cache.dump(constraints=[
                # do not dump the output of certain functions
                partial(exclude_targets_constraint, exclude_targets=args.exclude_persisting_targets.split(",")),
                # Do not dump results of not deterministic functions. This requires that respective functions are
                # marked with the decorator `execution.hydra_utils.not_deterministic`.
                # Note: The feature "not deterministic" does not propagate up the execution tree, i.e functions that
                # depend on results of not deterministic functions are not considered as not deterministic. This is
                # fine because the subconfigs for not deterministic functions are replaced with the hash of the
                # function result when creating the key for the cache entries of results that depend on these.
                not_deterministic_constraint,
                # only dump entries whose execution time is at least 1 second
                partial(exclude_target_time_none_or_lesser_then, min_time=timedelta(seconds=1))
            ])


if __name__ == "__main__":
    main()
