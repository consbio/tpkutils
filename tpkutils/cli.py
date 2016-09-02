import logging
import sys
import click
from tpkutils import TPK


logger = logging.getLogger('tpkutils')


def configure_logging(verbose):
    if verbose == 2:
        level = logging.DEBUG
    elif verbose == 1:
        level = logging.INFO
    else:
        level = logging.ERROR
    logging.basicConfig(stream=sys.stderr, level=level)



@click.group()
def cli():
    pass


@cli.command(short_help='Export the tile package to mbtiles')
@click.argument('tpk_filename', type=click.Path(exists=True))
@click.argument('mbtiles_filename', type=click.Path())
@click.option(
    '-z', '--zoom', type=click.STRING, default=None,
    help='Limit zoom levels to export: "0,1,2"')
@click.option(
    '-o', '--overwrite', default=False,
    help='Overwrite existing mbtiles file', show_default=True)

@click.option('-v', '--verbose', count=True, help='Verbose output')
def mbtiles(tpk_filename, mbtiles_filename, zoom, overwrite, verbose):
    """Export the tile package to mbtiles format"""

    configure_logging(verbose)

    tpk = TPK(tpk_filename)
    tpk.to_mbtiles(mbtiles_filename, zoom, overwrite)


if __name__ == '__main__':
    cli()