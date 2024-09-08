from setuptools import setup, find_packages

setup(
    name='movie_analysis',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'pandas',
        'pycountry',
        'pypopulation',
        'numpy',
    ],
    entry_points={
        'console_scripts': [
            'run-main=main:main',  # Adjust the command and function as needed
        ],
    },
    description='A package for analyzing imdb movie data.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='Kajetan Bialy',
    url='https://github.com/zorndog/Python-Project',  # Adjust with your repo URL if available
)
from setuptools import setup, find_packages
