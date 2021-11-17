# Hydra Cached
Hydra instantiate, but cached!

This project allows executing processing [pipelines](#pipelines) defined in python files. 

## Setup
```
python -m pip install git+https://github.com/ArneBinder/hydra-cached
```

## Usage
```
usage: instantiate [-h] [--config_object CONFIG_OBJECT] [--persist_cache]
               [--cache_dir CACHE_DIR] [--cache_verbose] [--display_config]
               [--exclude_persisting_targets EXCLUDE_PERSISTING_TARGETS]
               [--log_level LOG_LEVEL]
               config

Execute a processing pipeline from a config object defined in a python module.

positional arguments:
  config                Name of the module that has to contain a config dict
                        which will be instantiated via
                        execution.hydra.instantiate(config).

optional arguments:
  -h, --help            show this help message and exit
  --config_object CONFIG_OBJECT, -o CONFIG_OBJECT
                        Object from the config module that will be
                        instantiated (default: "config").
  --persist_cache, -p   A flag to enable cache persistence (loading from and
                        dumping to a cache directory, see --cache_dir)
  --cache_dir CACHE_DIR, -c CACHE_DIR
                        Cache directory used to load/dump the cache (only
                        relevant if --persist_cache is set). Defaults to
                        "cache"
  --cache_verbose, -v   A flag to enable verbose logging for the cache.
  --display_config, -d  A flag, if enabled, log the config as yaml string to
                        the console.
  --exclude_persisting_targets EXCLUDE_PERSISTING_TARGETS, -e EXCLUDE_PERSISTING_TARGETS
                        Comma separated list of strings that identify targets
                        to exclude from cache persistence. Use hydra_cached.ex
                        ecution.hydra.convert_target_to_string() to get the
                        correct string representation for a callable/class.
                        default: empty string
  --log_level LOG_LEVEL, -l LOG_LEVEL
                        Log level for the console logger. default: INFO
```

Yoiu can find a working example config in [this repo](https://github.com/ArneBinder/hydra-cached-example).


## Pipelines

A pipeline is defined in a Python module that contains at least one dict like object (default: `config`, see
parameter `--config_object`) which may be arbitrary nested. The pipeline is executed by instantiating that config
object, i.e. the config object is recursively processed by calling all values of keys `_target_` as functions with the
remaining key value pairs as keyword arguments, see method `instantiate` in 
[hydra.py](hydra_cached/execution/hydra.py) for further details and additional special keys. This functionality
is provided by the [hydra package](https://hydra.cc/docs/intro/). However, the hydra instantiate method is slightly
modified to allow for caching of intermediate results. By doing so, it is possible to reuse object definitions within
one pipeline without the need to recalculate them. Per default, a simple 
[in memory cache](hydra_cached/execution/caching/memory.py) is used that will not be persisted.

Pipelines are intended to work without external parameters, e.g. all input/output locations are defined within the config. 
However, if necessary, you can use environment variables to parametrize the config.
