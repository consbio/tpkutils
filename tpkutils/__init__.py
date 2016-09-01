"""
Tile package reading functions.
see info here: https://gdbgeek.wordpress.com/2012/08/09/demystifying-the-esri-compact-cache/

Tile package files:
*.bundlx: tile index, tile offsets in bundle are stored in 5 byte values
*.bundle: offsets are stored in bundlx, first 4 bytes at offset are length of tile data
conf.xml: basic tileset info
conf.cdi: tileset bounding box
"""


import os
import glob
import math
from collections import namedtuple, defaultdict
from zipfile import ZipFile
from io import BytesIO
import hashlib


BUNDLE_DIM = 128 # bundles are 128 rows x 128 columns tiles
INDEX_SIZE = 5  # tile index is stored in 5 byte values


Tile = namedtuple('Tile', ['x', 'y', 'z', 'data'])


def buffer_to_offset(buffer):
    """
    Convert a byte buffer into an integer offset according to ArcGIS packing
    scheme:

    (buffer[0] & 0xff) +
    (buffer[1] & 0xff) * 2 ** 8 +
    (buffer[2] & 0xff) * 2 ** 16 +
    (buffer[3] & 0xff) * 2 ** 24 ...

    Parameters
    ----------
    buffer: list[bytes]
        byte buffer

    Returns
    -------
    int: offset
    """

    return sum(((v & 0xff) * 2 ** (i * 8) for i, v in enumerate(buffer)))


def read_tile(bundle, offset):
    """
    Read tile bytes at offset position in bundle.

    Parameters
    ----------
    bundle: ArcGIS tile bundle file
    offset: offset in bytes to beginning of tile data block (first 4 bytes are length)

    Returns
    -------
    tile_bytes: bytes (may be empty)
    """

    bundle.seek(offset)
    return bundle.read(buffer_to_offset(bundle.read(4)))



def read_bundle_tiles(bundle_filename):
    """
    Read all non-empty tiles from bundle.

    Parameters
    ----------
    bundle_filename: string
        name of ArcGIS bundle filename

    Returns
    -------
    generator(Tile)
        Only returns non-empty tiles
    """

    # parse filename to determine row / col offset for bundle
    # offsets are in hex
    file_root = os.path.splitext(os.path.basename(bundle_filename))[0]
    r_offset, c_offset = [int(x, 16) for x in file_root.lstrip('R').split('C')]
    # zoom level is from name of containing folder
    z = int(os.path.split(os.path.dirname(bundle_filename))[1].lstrip('L'))

    with open(bundle_filename.replace('.bundle', '.bundlx'), 'rb') as bundlx:
        bundlx.seek(16)  # 16 byte header
        index_bytes = bundlx.read()

    with open(bundle_filename, 'rb') as bundle:
        index = 0
        max_index = BUNDLE_DIM**2
        while index < max_index:
            data = read_tile(
                bundle,
                buffer_to_offset(index_bytes[index * INDEX_SIZE:(index + 1) * INDEX_SIZE])
            )
            if data:
                row = math.floor(float(index) / BUNDLE_DIM)
                col = index - row * BUNDLE_DIM
                yield Tile(c_offset + col, r_offset + row, z, data)

            index += 1


def read_all_tiles(folder):
    """
    Read all non-empty tiles from all zoom levels in folder using a generator
    expression.

    Parameters
    ----------
    folder: string
        folder containing _alllayers directory

    Returns
    -------
    generator(Tile)
        Only returns non-empty tiles
    """

    for f in glob.glob('{0}/_alllayers/L*/*.bundle'.format(folder)):
        yield from read_bundle_tiles(f)


def read_zoom_level_tiles(folder, zoom):
    """
    Read all non-empty tiles from the zoom level using a generator expression.

    Parameters
    ----------
    folder: string
        folder containing _alllayers directory

    zoom: int or list-like
        zoom level or list-like of zoom levels

    Returns
    -------
    generator(Tile)
        Only returns non-empty tiles
    -------

    """
    if isinstance(zoom, int):
        zoom = [zoom]

    for z in zoom:
        print('zoom', z)
        for f in glob.glob('{0}/_alllayers/L{1:02}/*.bundle'.format(folder, z)):
            yield from read_bundle_tiles(f)


def read_tpk_tiles(filename, zoom=None):
    """
    Read all non-empty tiles from tile package, optionally limited to zoom
    levels provided.

    Parameters
    ----------
    filename: string
        name of ArcGIS tile package
    zoom: int or list-like  (default: None)
        zoom level or list-like of zoom levels

    Returns
    -------
    generator(Tile)
        Only returns non-empty tiles
    """

    if isinstance(zoom, int):
        zoom = [zoom]

    with ZipFile(filename) as tpk:

        bundles = []
        for name in tpk.namelist():
            if 'Layers/_alllayers/L' in name and '.bundle' in name:
                z = int(name.split('/')[-2].lstrip('L'))
                if zoom is None or z in zoom:
                    bundles.append(name)

        for fname in bundles:
            # parse filename to determine row / col offset for bundle
            # offsets are in hex
            file_root = os.path.splitext(os.path.basename(fname))[0]
            r_off, c_off = [int(x, 16) for x in file_root.lstrip('R').split('C')]
            # zoom level is from name of containing folder
            z = int(os.path.split(os.path.dirname(fname))[1].lstrip('L'))

            # discard 16 byte header
            index_bytes=tpk.read(fname.replace('.bundle', '.bundlx'))[16:]

            bundle_bytes = BytesIO(tpk.read(fname))
            index = 0
            max_index = BUNDLE_DIM ** 2
            while index < max_index:
                data = read_tile(
                    bundle_bytes,
                    buffer_to_offset(index_bytes[index * INDEX_SIZE:(index + 1) * INDEX_SIZE])
                )
                if data:
                    row = math.floor(float(index) / BUNDLE_DIM)
                    col = index - row * BUNDLE_DIM
                    yield Tile(c_off + col, r_off + row, z, data)

                index += 1