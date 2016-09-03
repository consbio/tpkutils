import logging
import os
import sys
import time
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

@cli.group()
def export():
    pass


@export.command(short_help='Export the tile package to mbtiles')
@click.argument('tpk_filename', type=click.Path(exists=True))
@click.argument('mbtiles_filename', type=click.Path())
@click.option(
    '-z', '--zoom', type=click.STRING, default=None,
    help='Limit zoom levels to export: "0,1,2"')
@click.option(
    '-o', '--overwrite', is_flag=True, default=False,
    help='Overwrite existing mbtiles file', show_default=True)

@click.option('-v', '--verbose', count=True, help='Verbose output')
def mbtiles(tpk_filename, mbtiles_filename, zoom, overwrite, verbose):
    """Export the tile package to mbtiles format"""

    configure_logging(verbose)

    if os.path.exists(mbtiles_filename) and not overwrite:
        raise click.BadArgumentUsage(
            'Output exists and overwrite is false.  Use -o option to overwrite')

    start = time.time()

    tpk = TPK(tpk_filename)
    tpk.to_mbtiles(mbtiles_filename, zoom, overwrite)
    tpk.close()

    print('Read tiles in {0:2f} seconds'.format(time.time() - start))

if __name__ == '__main__':
    cli()