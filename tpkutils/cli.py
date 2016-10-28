import logging
import os
import sys
import time
import click
import pkg_resources
import webbrowser

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
    '--overwrite', is_flag=True, default=False,
    help='Overwrite existing mbtiles file', show_default=True)

@click.option('-v', '--verbose', count=True, help='Verbose output')
def mbtiles(tpk_filename, mbtiles_filename, zoom, overwrite, verbose):
    """Export the tile package to mbtiles format"""

    configure_logging(verbose)

    if os.path.exists(mbtiles_filename) and not overwrite:
        raise click.ClickException(
            'Output exists and overwrite is false. '
            'Use --overwrite option to overwrite')

    start = time.time()

    if zoom is not None:
        zoom = [int(v) for v in zoom.split(',')]

    tpk = TPK(tpk_filename)
    tpk.to_mbtiles(mbtiles_filename, zoom)
    tpk.close()

    print('Exported tiles in {0:2f} seconds'.format(time.time() - start))


@export.command(short_help='Export the tile package to disk')
@click.argument('tpk_filename', type=click.Path(exists=True))
@click.argument('path', type=click.Path())
@click.option(
    '-z', '--zoom', type=click.STRING, default=None,
    help='Limit zoom levels to export: "0,1,2"')
@click.option(
    '--scheme', type=click.Choice(('xyz', 'arcgis')), default='arcgis',
    help='Tile numbering scheme: xyz or arcgis', show_default=True)
@click.option(
    '--drop-empty', type=click.BOOL, is_flag=True, default=False,
    help='Drop empty tiles from output'
)
@click.option(
    '--path-format', type=click.STRING, default='{z}/{x}/{y}.{ext}',
    help='Format expression for output tile files, within output path. '
         'Must contain parameters for z, x, y, and ext (extension).',
    show_default=True
)
@click.option('-p', '--preview', is_flag=True, default=False,
              help='Preview the exported tiles in a simple map.')
@click.option('-v', '--verbose', count=True, help='Verbose output')
def disk(tpk_filename, path, zoom, scheme, drop_empty, path_format,
         preview, verbose):
    """Export the tile package to disk: z/x/y.<ext> or pattern specified using
    --path-format option.

    Will use the 'arcgis' tile scheme by default.  If using with an XYZ tile
    server or client, use the 'xyz' tile scheme.

    Not recommended for higher zoom levels as this will produce large
    directory trees."""

    configure_logging(verbose)

    if os.path.exists(path) and len(os.listdir(path)) > 0:
        raise click.ClickException('Output directory must be empty.')

    start = time.time()

    if zoom is not None:
        zoom = [int(v) for v in zoom.split(',')]

    with TPK(tpk_filename) as tpk:
        tpk.to_disk(path, zoom, scheme, drop_empty, path_format)

        if preview:
            template_filename = os.path.join(pkg_resources.resource_filename(__name__, 'preview_template.html'))
            with open(template_filename) as infile:
                template = infile.read()

            template = template.replace(
                '{{BOUNDS}}', '[[{1}, {0}], [{3}, {2}]]'.format(*tpk.bounds)
            ).replace(
                '{{MINZOOM}}', str(tpk.zoom_levels[0])
            ).replace(
                '{{MAXZOOM}}', str(tpk.zoom_levels[-1])
            ).replace(
                '{{URL}}',
                os.path.join(
                    os.path.abspath(path),
                    path_format.replace('{ext}', tpk.format.lower().replace('jpeg', 'jpg')[:3])
                )
            )

            outfilename = os.path.join(path, 'preview.html')
            with open(outfilename, 'w') as outfile:
                outfile.write(template)

            webbrowser.open(outfilename)


    print('Exported tiles in {0:2f} seconds'.format(time.time() - start))
