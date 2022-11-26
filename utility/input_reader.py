import yaml


def read_input(path: str, prefix: str, suffix: str) -> list:
    """
    Read input url file and return parsed urls
    :param path: Filepath to the input urls
    :param prefix: possible prefix defined in config yml
    :param suffix: possible suffix defined in config yml
    :return: list of URL from the input file
    """
    with open(path) as f:
        urls = [prefix + line.rstrip() + suffix for line in f]
    return urls


def get_config(path: str) -> dict:
    """
    Read the config.yml file and convert to dict
    :param path: Path to the config file
    :return: config as a dict format
    """
    with open(path, 'r') as stream:
        doc = yaml.safe_load(stream)
    return doc
