"""
Tile package reading functions.
see info here: https://gdbgeek.wordpress.com/2012/08/09/demystifying-the-esri-compact-cache/

Tile package files:
*.bundlx: tile index, tile offsets in bundle are stored in 5 byte values
*.bundle: offsets are stored in bundlx, first 4 bytes at offset are length of tile data
conf.xml: basic tileset info
conf.cdi: tileset bounding box
"""
from __future__ import division
from six import iterbytes

import sys
import json
import logging
import math
import time
from xml.etree import ElementTree
from zipfile import ZipFile

import hashlib
import os
from collections import namedtuple
from io import BytesIO

from pymbtiles import MBtiles, Tile

logger = logging.getLogger('tpkutils')


BUNDLE_DIM = 128 # bundles are 128 rows x 128 columns tiles
# TODO: bundle size is stored in one of the configuration files
INDEX_SIZE = 5  # tile index is stored in 5 byte values

WORLD_CIRCUMFERENCE = 40075016.69  # circumference of the earth in metres at the equator
ORIGIN_OFFSET = WORLD_CIRCUMFERENCE / 2.0 # half the circumference
TILE_PIXEL_SIZE = 256  # in a map service tileset all tiles are 256x256 pixels

# sha1 hashes of empty tiles (completely black or white)
EMPTY_TILES = {
    '4ae57bed2b996ae0bd820a1b36561e26ef6d1bc8', # completely white JPG
    'aba7a74e3b932e32bdb21d670a16a08a9460591a',  # blank PNG
    '89eff69bee598f8c3217ca5363c2ef356fd0c394',  # blank PNG
    '147ca8bf480d89b17921e24e3c09edcf1cb2228b'
}

# sha1 hash of fully transparent tile
TRANSPARENT_TILES = ('147ca8bf480d89b17921e24e3c09edcf1cb2228b')    # png

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

    return sum(((v & 0xff) * 2 ** (i * 8) for i, v in enumerate(iterbytes(buffer))))


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


class TPK(object):
    def __init__(self, filename):
        """
        Opens a tile package file for reading tiles and metadata.

        Parameters
        ----------
        filename: string
            name of tile package
        """
        self._fp = ZipFile(filename)

        # Fields specifically meant to be updated by user
        self.version = '1.0.0'
        self.attribution = ''

        # Fields that may or may not be populated
        self.legend = []

        # min and max column (longitude) and row (latitude) at the highest exported level
        # read tiles will maintain these values when called with "highest_zoom" parameter
        self.minrow = sys.maxsize       # init very large
        self.maxrow = 0                 # init low
        self.mincolumn = sys.maxsize    # init very large
        self.maxcolumn = 0              # init low

        logger.debug('Reading package metadata')

        # File format, zoom levels, etc in .../<root layer name>/conf.xml
        conf_filename = [f for f in self._fp.namelist() if 'conf.xml' in f][0]
        self.root_name = os.path.split(os.path.dirname(conf_filename))[1]
        xml = ElementTree.fromstring(self._fp.read(conf_filename))

        # resolution = Circumference of earth / (2**zoomLevel * 256)
        # therefore zoomlevel = log2(Circumference of earth/(resolution*256))
        web_tile_zoom_level_from_resolution =  lambda res: int(round(math.log2(WORLD_CIRCUMFERENCE / (res * TILE_PIXEL_SIZE))))

        self.zoom_levels = []

        # we need to map the "nominal" level id to the actual level id as indicated by the resolution
        self.web_tile_level_map = {}    # key = nominal zoom level, value = actual tile map service zoom level
        self.resolution_map = {}    # key = tile map service zoom level, value = resolution

        # iteration builds the "nominal zoom levels list" as well as the actual web tile service level map
        for e in xml.findall('TileCacheInfo/LODInfos/LODInfo'):
            level = int(e.find('LevelID').text)     # ArcGis always numbers the levels starting at zero
            resolution = float(e.find('Resolution').text)  # To determine actual web tile zoom level we need the resolution
            self.zoom_levels.append(level)
            self.web_tile_level_map[level] = web_tile_zoom_level_from_resolution(resolution)
            self.resolution_map[self.web_tile_level_map.get(level)] = resolution

        for k, v in self.web_tile_level_map.items():
            logger.info('Nominal level: {0} == tile map zoom level {1}'.format(k,v))


        self.format = xml.find('TileImageInfo/CacheTileFormat').text

        # Descriptive info in esriinfo/iteminfo.xml
        # Some fields are required by ArcGIS to create tile package
        xml = ElementTree.fromstring(self._fp.read('esriinfo/iteminfo.xml'))
        self.name = xml.find('title').text  # required field, provided automatically
        self.summary = xml.find('summary').text  # required field
        self.tags = xml.find('tags').text or ''  # required field
        self.description = xml.find('description').text or ''  # optional
        self.credits = xml.find('accessinformation').text or ''  # optional, Credits in ArcGIS
        self.use_constraints = xml.find('licenseinfo').text or ''  # optional, Use Constraints in ArcGIS

        # Bounding box, legend, etc is in .../servicedescriptions/mapserver/mapserver.json
        sd = json.loads(self._fp.read('servicedescriptions/mapserver/mapserver.json').decode('utf-8'))
        geoExtent = sd['resourceInfo']['geoFullExtent']
        self.bounds = [geoExtent[k] for k in ('xmin', 'ymin', 'xmax', 'ymax')]

        # convert to dict for easier access
        resources = {r['name']: r for r in sd['resources']}


        def getLabel(element):
            if 'label' in element:
                return element['label']
            if 'values' in element:
                return ', '.join(element['values'])

        if 'legend' in resources:
            for layer in resources['legend']['contents'].get('layers', []):
                self.legend.append(
                    {
                        'name': layer['layerName'],
                        'elements': [
                            {
                                # data:image/png;base64,
                                'imageData': 'data:{0};base64,{1}'.format(
                                    l['contentType'], l['imageData']
                                ),
                                'label': getLabel(l)
                            } for l in layer['legend']
                        ]
                    }
                )



    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def read_tiles(self, zoom=None, highest_zoom=None, flip_y=False):
        """
        Read all non-empty tiles from tile package, optionally limited to zoom
        levels provided.

        Parameters
        ----------
        zoom: int or list-like  (default: None)
            zoom level or list-like of zoom levels
        highest_zoom: int (default: None)
            when processing tiles from the designated highest zoom level record min/max row and column
            this gives us the option of calculating the map bounds from the actual tile coverage
            NOTE: this value has already been "translated" from LevelID to actual WTMS zoom level!
        flip_y: bool  (default False)
            if True, will return tiles in xyz tile scheme.  Otherwise will use
            ArcGIS scheme.

        Returns
        -------
        generator(Tile)
            Only returns non-empty tiles
        """

        discarded_tiles = 0
        if isinstance(zoom, int):
            zoom = [zoom]

        bundles = []
        for name in self._fp.namelist():
            if '{0}/_alllayers/L'.format(self.root_name) in name and '.bundle' in name:
                z = int(name.split('/')[-2].lstrip('L'))
                if zoom is None or z in zoom:
                    bundles.append(name)

        for fname in bundles:
            logger.info('Reading bundle: {0}'.format(fname))
            start = time.time()
            # parse filename to determine row / col offset for bundle
            # offsets are in hex
            root = os.path.splitext(os.path.basename(fname))[0]
            r_off, c_off = [int(x, 16) for x in root.lstrip('R').split('C')]
            # zoom level is from name of containing folder
            z = int(os.path.split(os.path.dirname(fname))[1].lstrip('L'))

            # get the actual web tile service zoom level
            z = self.web_tile_level_map.get(z)

            # max row and column value allowed at this WTMS zoom level:  (2**zoom_level) - 1
            max_row_col = (1 << z) - 1

            # discard 16 byte header
            index_bytes = self._fp.read(fname.replace('.bundle', '.bundlx'))[16:]

            bundle_bytes = BytesIO(self._fp.read(fname))
            index = 0
            max_index = BUNDLE_DIM ** 2
            while index < max_index:
                data = read_tile(
                    bundle_bytes,
                    buffer_to_offset(
                        index_bytes[index * INDEX_SIZE:(index + 1) * INDEX_SIZE]
                    )
                )
                if data:
                    # x = column (longitude), y = row (lattitude)
                    col = int(math.floor(float(index) / BUNDLE_DIM))
                    x = c_off + col
                    y = r_off + (index % BUNDLE_DIM)

                    # ensure resultant row and column values fall within range!
                    if (0 <= x <= max_row_col) and (0 <= y <= max_row_col):
                        if flip_y:
                            y = max_row_col -  y

                        # track min and max row and column at highest zoom level
                        # this gives us the option of calculating the map bounds from the tile coverage
                        if z == highest_zoom:
                            self.mincolumn = min(self.mincolumn, x)
                            self.maxcolumn = max(self.maxcolumn, x)
                            self.minrow = min(self.minrow, y)
                            self.maxrow = max(self.maxrow, y)

                        yield Tile(z, x, y, data)
                    else:
                        logger.debug('Tile out of range, zoom level = {0}, column = {1}, row = {2}'.format(z, x, y))
                        discarded_tiles += 1

                index += 1
            logger.debug('Time to read bundle: {0:2f}'.format(time.time() - start))

        logger.info('Total number of discarded "out of range" tiles = {0}'.format(discarded_tiles))

    def to_mbtiles(self, filename, calc_bounds=False, drop_transparent=False, zoom=None):
        """
        Export tile package to mbtiles v1.1 file, optionally limited to zoom
        levels.  If filename exists, it will be overwritten.  If filename
        does not include the suffix '.mbtiles' it will be added.

        Parameters
        ----------
        filename: string
            name of mbtiles file
        calc_bounds: boolean
            when true calculate the map bounds from the actual tile coverage at the highest exported zoom level
        drop_transparent: boolean
            when true filter out purely transparent tiles, dropping them from the resultant MBTiles db
        zoom: int or list-like of ints, default: None (all tiles exported)
            zoom levels to export to mbtiles
        """

        if self.format.lower() == 'mixed':
            raise ValueError('Mixed format tiles are not supported for export to mbtiles')

        if not filename.endswith('.mbtiles'):
            filename = '{0}.mbtiles'.format(filename)

        with MBtiles(filename, 'w') as mbtiles:
            if zoom is None:
                zoom = self.zoom_levels
            elif isinstance(zoom, int):
                zoom = [zoom]

            zoom_map = self.web_tile_level_map

            zoom = list(zoom)
            zoom.sort()

            highest_zoom = self.web_tile_level_map.get(zoom[-1])

            # if drop_transparent flag is true and the tile is completely transparent we DO NOT want to keep it,
            # othwerwise we DO want to keep it
            keep_tile = lambda tile: not (drop_transparent and hashlib.sha1(tile.data).hexdigest() in TRANSPARENT_TILES)

            mbtiles.write_tiles(filter(keep_tile, self.read_tiles(zoom, highest_zoom, flip_y=True)))

            # populate bounds metatdata from JSON data or calculate from map coverage if desired
            bounds = self.bounds if not calc_bounds else self.calculate_bounds(highest_zoom)

            center = '{0:4f},{1:4f},{2}'.format(
                bounds[0] + (bounds[2] - bounds[0]) / 2.0,
                bounds[1] + (bounds[3] - bounds[1]) / 2.0,
                max(zoom_map.get(zoom[0]), int((zoom_map.get(zoom[0]) + zoom_map.get(zoom[-1])) / 2.0))  # Tune this
            )

            mbtiles.meta.update({
                'name': self.name,
                'description': self.summary,  # not description, which is optional
                'version': self.version,
                'attribution': self.attribution,
                'tags': self.tags,
                'credits': self.credits,
                'use_constraints': self.use_constraints,

                'type': 'overlay',
                'format': self.format.lower().replace('jpeg', 'jpg')[:3],
                'bounds': ','.join('{0:4f}'.format(v) for v in bounds),
                'center': center,
                'minzoom': str(zoom_map.get(zoom[0])),
                'maxzoom': str(zoom_map.get(zoom[-1])),

                'legend': json.dumps(self.legend) if self.legend else ''
            })


    def calculate_bounds(self, highest_zoom):
        """
        :param highest_zoom: highest web map tile zoom level exported
            (Note: also uses self.mincolumn, self.minrow, self.maxcolumn and self.maxcolumn which
             are relative to the given highest zoom level)

        :return: tuple(minX, minY, maxX, maxY) in WGS84
        """
        # resolution allows us to convert pixels to metres
        # once we have metres we can convert that to geographical coordinates
        resolution = self.resolution_map.get(highest_zoom)

        # min and max longitude
        minX = ((self.mincolumn * TILE_PIXEL_SIZE * resolution - ORIGIN_OFFSET)  / ORIGIN_OFFSET) * 180.0
        maxX = (((self.maxcolumn+1) * TILE_PIXEL_SIZE * resolution - ORIGIN_OFFSET)  / ORIGIN_OFFSET) * 180.0

        # min latitude
        lat = ((self.minrow * TILE_PIXEL_SIZE * resolution - ORIGIN_OFFSET)  / ORIGIN_OFFSET) * 180.0
        minY = 180.0 / math.pi * (2 * math.atan(math.exp(lat * math.pi / 180.0)) - math.pi / 2.0)

        # max latitude
        lat = (((self.maxrow+1) * TILE_PIXEL_SIZE * resolution - ORIGIN_OFFSET)  / ORIGIN_OFFSET) * 180.0
        maxY = 180.0 / math.pi * (2 * math.atan(math.exp(lat * math.pi/180)) - math.pi / 2.0)

        logger.info('Bounds calculated from zoom level {0} are {1}, {2}, {3}, {4}'.format(highest_zoom, minX, minY, maxX, maxY))

        return (minX, minY, maxX, maxY)


    def to_disk(self, path, zoom=None, scheme='arcgis', drop_empty=False,
                path_format='{z}/{x}/{y}.{ext}'):
        """
        Export tile package to directory structure: z/x/y.<ext> where <ext> is
        png or jpg.  If output exists, this function will raise an IOError.

        Parameters
        ----------
        path: string
            path in which to create output
        zoom: int or list-like of ints, default: None (all tiles exported)
            zoom levels to export to disk
        scheme: string, one of ('xyz', 'arcgis'), default: arcgis
            tile numbering scheme.  If xyz, y value will be flipped from ArcGIS
            scheme.  (xyz scheme is used by online tile services)
        drop_empty: bool, default False
            if True, tiles that are empty will not be output
        path_format: string with format placeholders {z}, {x}, {y}, {ext}
            Format string must include z, x, y, ext parameters.

        """

        ext = self.format.lower().replace('jpeg', 'jpg')
        if ext == 'mixed':
            raise ValueError('Mixed format tiles are not supported for export to disk')
        ext = ext[:3]

        if not scheme in ('xyz', 'arcgis'):
            raise ValueError('scheme must be xyz or arcgis')

        if not os.path.exists(path):
            os.makedirs(path)
        elif len(os.listdir(path)) > 0:
            raise IOError('Output directory must be empty.')

        if zoom is None:
            zoom = self.zoom_levels
        elif isinstance(zoom, int):
            zoom = [zoom]

        zoom = list(zoom)
        zoom.sort()

        for tile in self.read_tiles(zoom, flip_y=(scheme == 'xyz')):
            if drop_empty and hashlib.sha1(tile.data).hexdigest() in EMPTY_TILES:
                continue

            filename = path_format.format(z=tile.z, x=tile.x, y=tile.y, ext=ext)
            out_path = os.path.join(path, os.path.split(filename)[0])
            if not os.path.exists(out_path):
                os.makedirs(out_path)

            with open(os.path.join(path, filename), 'wb') as outfile:
                outfile.write(tile.data)

    def close(self):
        self._fp.close()
