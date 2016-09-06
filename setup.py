import os
from setuptools import setup


long_description = 'Utility to read and export ArcGIS Tile Packages'


if os.path.exists('README.md'):
    try:
        # Use pypandoc to convert markdown readme to reStructuredText as required by pypi
        # Requires pandoc to be installed.  See: http://johnmacfarlane.net/pandoc/installing.html
        from pypandoc import convert
        read_md = lambda f: convert(f, 'rst', format='md')
        long_description = read_md('README.md')
    except:
        pass


setup(
    name='tpkutils',
    version='0.1.0',
    packages=['tpkutils'],
    url='https://github.com/consbio/tkutils',
    license='ISC',
    author='Brendan Ward',
    author_email='bcward@consbio.org',
    description='ArcGIS Tile Package Utilities',
    long_description=long_description,
    install_requires=['click'],
    include_package_data=True,
    extras_require={
        'test': ['pytest', 'pytest-cov'],
    },
    entry_points={
        'console_scripts': 'tpk=tpkutils.cli:cli'
    }
)
