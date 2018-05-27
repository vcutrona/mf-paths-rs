try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

config = {
    'description': 'Progetto tesi',
    'author': 'Vincenzo Cutrona',
    #'url': 'URL to get it at.',
    #'download_url': 'Where to download it.',
    'author_email': 'v.cutrona1@gmail.com',
    'version': '0.1',
    'install_requires': ['nose'],
    'packages': ['preprocessing'],
    'scripts': [],
    'name': 'tesi'
}

setup(**config)