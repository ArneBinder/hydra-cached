# Hydra Cached
Hydra instantiate, but cached!

## Setup
```
pip -r requirements.txt
```

## Usage
```
usage: hydra_cached/main.py [-h] [--config_object CONFIG_OBJECT] [--persist_cache]
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