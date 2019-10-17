from setuptools import setup


setup(
    name="tpkutils",
    version="0.7.0",
    packages=["tpkutils"],
    url="https://github.com/consbio/tpkutils",
    license="ISC",
    author="Brendan Ward",
    author_email="bcward@consbio.org",
    description="ArcGIS Tile Package Utilities",
    long_description_content_type="text/markdown",
    long_description=open("README.md").read(),
    install_requires=["click", "pymbtiles>=0.5.0", "six", "mercantile"],
    include_package_data=True,
    extras_require={"test": ["pytest", "pytest-cov"]},
    entry_points={"console_scripts": "tpk=tpkutils.cli:cli"},
)
