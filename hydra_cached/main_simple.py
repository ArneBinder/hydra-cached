import argparse
import importlib
import logging

from hydra_cached.execution.hydra import instantiate


if __name__ == "__main__":
    # initialize here to set log level also for imported modules
    logging.basicConfig(level=logging.getLevelName("INFO"))

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "config",
        type=str,
        help="Name of the config_module that has to contain the config dict that will be instantiated with "
             "hydra.instantiate(config_module.config)."
    )

    args = parser.parse_args()
    config_module = importlib.import_module(name=args.config)

    result = instantiate(config_module.config, _convert_='partial')

    print("done")
