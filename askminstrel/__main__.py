import logging
from askminstrel import cli

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
        format='%(asctime)s %(levelname)s:%(module)s:%(funcName)s: %(message)s',
        datefmt="%H:%M:%S")

    logging.info('Application starting')
    cli()
