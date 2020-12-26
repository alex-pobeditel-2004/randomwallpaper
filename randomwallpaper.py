import ctypes
import os
import logging
import pathlib
import random
import sys
import requests
import ruamel.yaml

from typing import Optional

from bs4 import BeautifulSoup

DEFAULT_DIRECTORY = 'randomwallpapers'
CONFIG = 'config.yaml'
HOST = 'https://wallhaven.cc'

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:76.0) Gecko/20100101 Firefox/76.0'

# Initialize YAML parser:
yaml = ruamel.yaml.YAML(typ='safe')

# Initialize logger:
logger = logging.getLogger('RandomWallpaper')
logging.basicConfig(format='[%(levelname)s] %(message)s', level=logging.INFO)


def get_api_key(login, password):
    """
    Login to the site and find API key in the profile settings
    :param login: username
    :param password: password
    :return: API key string
    """

    headers = {
        'User-Agent': UA
    }

    s = requests.Session()
    s.headers.update(headers)

    # Searching for CSRF token:
    try:
        r = s.get(HOST + '/login')
    except requests.exceptions.ConnectionError as error:
        logger.error(str(error))
        return False

    soup = BeautifulSoup(r.text, features='html.parser')
    token = soup.find(id='login').find('input', value=True)['value']

    payload = {
        '_token': token,
        'username': login,
        'password': password
    }
    s.post(HOST + '/auth/login', data=payload)

    r = s.get(HOST + '/settings/account')
    soup = BeautifulSoup(r.text, features='html.parser')
    api_key = soup.find('input', readonly='readonly')

    if not api_key:
        return False
    else:
        return api_key['value']


def parse_config() -> Optional[dict]:
    """
    Analyze config file
    :return: parsed config (dict)
    """
    config_path = pathlib.Path(__file__).parent / CONFIG
    try:
        with open(config_path, 'rt', encoding='utf-8') as config_file:
            config = yaml.load(config_file)
    except OSError:
        logger.error('Cannot open config file {}'.format(config_path))
        return None
    except (ruamel.yaml.constructor.DuplicateKeyError,
            ruamel.yaml.scanner.ScannerError,
            ruamel.yaml.parser.ParserError) as error:
        logger.error('Failed to parse config {}:\n{}'.format(config_path, error))
        return None
    else:
        parsed_config = dict()

    try:
        # Choose a directory for wallpapers:
        if config['paths']:
            for item in [pathlib.Path(x) for x in config['paths'] if x]:
                if item.is_dir():
                    path = item
                    break
            else:
                logger.error('No valid path was found in the config file {}'.format(config_path))
                return None
        else:
            # Try default if no path is configured:
            path = pathlib.Path.cwd() / DEFAULT_DIRECTORY
            if not path.is_dir():
                try:
                    path.mkdir()
                    logger.info('Created the directory in default path: {}'.format(path))
                except OSError:
                    logger.error('Failed to create directory in default path: {}'.format(path))
                    return None
        parsed_config['path'] = path

        # Optional sections:
        if config['resolutions']:
            parsed_config['resolutions'] = ','.join(config['resolutions'])
            if len(config['resolutions']) == 1:
                parsed_config['atleast'] = parsed_config['resolutions']
        if config['ratios']:
            parsed_config['ratios'] = ','.join(config['ratios'])

        parsed_config['categories'] = config['categories']

        if config['purity'][-1] == '1':
            if config['api_key']:
                parsed_config['api_key'] = config['api_key']
            elif config['login'] and config['password']:
                parsed_config['api_key'] = get_api_key(config['login'], config['password'])
                if not parsed_config['api_key']:
                    logger.error('Failed to get API key, credentials which were provided '
                                 'in the config file {} may be invalid or page parsing failed.\nYou still can '
                                 'paste your API key into the config manually'.format(config_path))
                    return None
                else:
                    logger.info('Your API key: {}'.format(parsed_config['api_key']))
            else:
                logger.error('NSFW purity was checked but no API key or credentials '
                             'were provided in the config file {}'.format(config_path))
                return None

        parsed_config['purity'] = config['purity']

    except KeyError as error:
        logger.error('Looks like your config file {} is malformed: {}'.format(config_path, error))
        return None

    return parsed_config


def get_wallpaper(config: dict) -> Optional[str]:
    """
    Find and download random wallpaper
    :param config: Dictionary with config
    :return: Downloaded image path
    """

    s = requests.Session()

    # Main parameters:
    payload = {
        'sorting': 'random',
        'categories': config['categories'],
        'purity': config['purity']
    }

    # Optional parameters:
    if config.get('atleast', None):
        payload['atleast'] = config['atleast']
    elif config.get('resolutions', None):
        payload['resolutions'] = config['resolutions']

    if config.get('ratios', None):
        payload['ratios'] = config['ratios']

    if config.get('api_key', None):
        payload['apikey'] = config['api_key']

    # Getting the image list:
    r = s.get(HOST + '/api/v1/search', params=payload, timeout=10)

    # Checking response and choosing random image from random result:
    try:
        image = random.choice(r.json()['data'])
    except KeyError:
        if r.json().get('error', None):
            logger.error('API key can be invalid:\n{}'.format(r.json().get('error')))
        else:
            logger.error('Got unexpected result:\n{}'.format(r.text))
        return None

    logger.info(f'Downloading wallpaper: {image["url"]}')

    # Downloading the image:
    r = s.get(image['path'], params=payload, timeout=30)
    logger.info('Downloaded successfully!')

    output_path = config['path'] / pathlib.Path(image['path']).name
    try:
        with open(output_path, 'wb') as output_file:
            output_file.write(r.content)
    except OSError as error:
        logger.error(f'Failed to write file {output_path}:\n{error}')

    return output_path


def set_wallpaper(path):
    if sys.platform.startswith('win'):
        # Windows way
        spi_setdeskwallpaper = 20
        spif_sendchange = 3
        ctypes.windll.user32.SystemParametersInfoW(spi_setdeskwallpaper, 0, str(path), spif_sendchange)
        return True
    elif sys.platform.startswith('linux'):
        # Linux way
        de = os.environ.get('DESKTOP_SESSION')
        if de in ['cinnamon', 'gnome', 'mate']:
            # GNOME-heritage way
            os.system('gsettings set org.{}.desktop.background picture-uri "file://{}"'.format(de, path))
            return True
    elif sys.platform.startswith('darwin'):
        os.system('osascript -e \'tell application "Finder" to set desktop picture to POSIX file "{}"\''.format(path))
        return True

    logger.error("Don't really know what to do with file {}, you can change wallpaper manually anyway".format(path))
    return False


def main():
    config = parse_config()

    if config:
        path = get_wallpaper(config)
    else:
        sys.exit(1)

    if path:
        set_wallpaper(path)
        sys.exit(0)

    sys.exit(1)


if __name__ == "__main__":
    main()
