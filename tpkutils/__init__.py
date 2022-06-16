"""
Tile package reading functions.
see info here: https://gdbgeek.wordpress.com/2012/08/09/demystifying-the-esri-compact-cache/

Tile package files:
*.bundlx: tile index, tile offsets in bundle are stored in 5 byte values
*.bundle: offsets are stored in bundlx, first 4 bytes at offset are length of tile data
conf.xml: basic tileset info
conf.cdi: tileset bounding box
"""
from math import log2

import json
import logging
import math
import time
from xml.etree import ElementTree
from zipfile import ZipFile

import hashlib
import os
from io import BytesIO

from pymbtiles import MBtiles, Tile
import mercantile


logger = logging.getLogger("tpkutils")


BUNDLE_DIM = 128  # bundles are 128 rows x 128 columns tiles
# TODO: bundle size is stored in one of the configuration files
INDEX_SIZE = 5  # tile index is stored in 5 byte values

WORLD_CIRCUMFERENCE = 40075016.69  # circumference of the earth in metres at the equator
ORIGIN_OFFSET = WORLD_CIRCUMFERENCE / 2.0  # half the circumference
TILE_PIXEL_SIZE = 256  # in a map service tileset all tiles are 256x256 pixels

# sha1 hashes of empty tiles (completely black or white)
EMPTY_TILES = {
    "4ae57bed2b996ae0bd820a1b36561e26ef6d1bc8",  # completely white JPG
    "aba7a74e3b932e32bdb21d670a16a08a9460591a",  # blank PNG
    "89eff69bee598f8c3217ca5363c2ef356fd0c394",  # blank PNG
    "147ca8bf480d89b17921e24e3c09edcf1cb2228b",
    "147ca8bf480d89b17921e24e3c09edcf1cb2228b",  # completely transparent PNG
}


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

    return sum(((v & 0xFF) * 2 ** (i * 8) for i, v in enumerate(buffer)))


def calculate_zoom_from_resolution(resolution, tile_size=TILE_PIXEL_SIZE):
    """Calculate the zoom level for a given resolution and tile size.

    Given that
    `resolution = Circumference of earth / (2**zoomLevel * tile_size)`

    Zoom level is calculated by
    `zoomlevel = log2(Circumference of earth/(resolution * tile_size))`

    Parameters
    ----------
    resolution : float
    tile_size : int
        size of tile in pixels along one edge (default: 256)

    Returns
    -------
    int : Zoom level
    """

    return int(round(log2(WORLD_CIRCUMFERENCE / (resolution * tile_size))))


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
        self.version = "1.0.0"
        self.attribution = ""

        # Fields that may or may not be populated
        self.legend = []

        logger.debug("Reading package metadata")

        # File format, zoom levels, etc in .../<root layer name>/conf.xml
        conf_filename = [f for f in self._fp.namelist() if "conf.xml" in f][0]
        self.root_name = os.path.split(os.path.dirname(conf_filename))[1]
        xml = ElementTree.fromstring(self._fp.read(conf_filename))

        self.format = xml.find("TileImageInfo/CacheTileFormat").text

        cache_xml = xml.find("TileCacheInfo")

        self.tile_size = int(cache_xml.find("TileCols").text)

        # Levels of detail in original TPK (ordinal, starting at 0)
        self.lods = []
        self.zoom_levels = []

        # iteration builds the "nominal zoom levels list" as well as the actual web tile service level map
        for e in cache_xml.findall("LODInfos/LODInfo"):
            # NOTE: ArcGIS always numbers the levels starting at zero, regardless of actual zoom level
            lod = int(e.find("LevelID").text)
            self.lods.append(lod)

            # To determine actual web tile zoom level we need the resolution
            resolution = float(e.find("Resolution").text)
            zoom_level = calculate_zoom_from_resolution(resolution, self.tile_size)
            self.zoom_levels.append(zoom_level)

        # Descriptive info in esriinfo/iteminfo.xml
        # Some fields are required by ArcGIS to create tile package
        xml = ElementTree.fromstring(self._fp.read("esriinfo/iteminfo.xml"))
        self.name = xml.find("title").text  # required field, provided automatically
        self.summary = xml.find("summary").text  # required field
        self.tags = xml.find("tags").text or ""  # required field
        self.description = xml.find("description").text or ""  # optional

        # optional, Credits in ArcGIS
        self.credits = xml.find("accessinformation").text or ""

        # optional, Use Constraints in ArcGIS
        self.use_constraints = xml.find("licenseinfo").text or ""

        # Bounding box, legend, etc is in .../servicedescriptions/mapserver/mapserver.json
        # NOTE: this may not accurately represent the outer bounds of available tiles
        sd = json.loads(
            self._fp.read("servicedescriptions/mapserver/mapserver.json").decode(
                "utf-8"
            )
        )
        geoExtent = sd["resourceInfo"]["geoFullExtent"]
        self.bounds = [geoExtent[k] for k in ("xmin", "ymin", "xmax", "ymax")]

        # convert to dict for easier access
        resources = {r["name"]: r for r in sd["resources"]}

        def getLabel(element):
            if "label" in element:
                return element["label"]
            if "values" in element:
                return ", ".join(element["values"])

        if "legend" in resources:
            for layer in resources["legend"]["contents"].get("layers", []):
                self.legend.append(
                    {
                        "name": layer["layerName"],
                        "elements": [
                            {
                                # data:image/png;base64,
                                "imageData": "data:{0};base64,{1}".format(
                                    l["contentType"], l["imageData"]
                                ),
                                "label": getLabel(l),
                            }
                            for l in layer["legend"]
                        ],
                    }
                )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def read_tiles(self, zoom=None, flip_y=False):
        """
        Read all non-empty tiles from tile package, optionally limited to zoom
        levels provided.

        Parameters
        ----------
        zoom: int or list-like  (default: None)
            zoom level or list-like of zoom levels
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
            if "{0}/_alllayers/L".format(self.root_name) in name and ".bundle" in name:

                # Only extract tiles for specified zoom levels
                lod = int(name.split("/")[-2].lstrip("L"))
                z = self.zoom_levels[lod]
                if zoom is None or z in zoom:
                    bundles.append(name)

        for fname in bundles:
            logger.info("Reading bundle: {0}".format(fname))
            start = time.time()
            # parse filename to determine row / col offset for bundle
            # offsets are in hex
            root = os.path.splitext(os.path.basename(fname))[0]
            r_off, c_off = [int(x, 16) for x in root.lstrip("R").split("C")]

            # LOD is derived from name of containing folder
            lod = int(os.path.split(os.path.dirname(fname))[1].lstrip("L"))

            # Resolve the ordinal level to zoom level
            z = self.zoom_levels[lod]

            # max row and column value allowed at this WTMS zoom level:  (2**zoom_level) - 1
            max_row_col = (1 << z) - 1

            # discard 16 byte header
            index_bytes = self._fp.read(fname.replace(".bundle", ".bundlx"))[16:]

            bundle_bytes = BytesIO(self._fp.read(fname))
            index = 0
            max_index = BUNDLE_DIM ** 2
            while index < max_index:
                data = read_tile(
                    bundle_bytes,
                    buffer_to_offset(
                        index_bytes[index * INDEX_SIZE : (index + 1) * INDEX_SIZE]
                    ),
                )
                if data:
                    # x = column (longitude), y = row (latitude)
                    col = int(math.floor(float(index) / BUNDLE_DIM))
                    x = c_off + col
                    y = r_off + (index % BUNDLE_DIM)

                    # ensure resultant row and column values fall within range!
                    if (0 <= x <= max_row_col) and (0 <= y <= max_row_col):
                        if flip_y:
                            y = max_row_col - y

                        yield Tile(z, x, y, data)
                    else:
                        logger.debug(
                            "Tile out of range, zoom level = {0}, column = {1}, row = {2}".format(
                                z, x, y
                            )
                        )
                        discarded_tiles += 1

                index += 1
            logger.debug("Time to read bundle: {0:2f}".format(time.time() - start))

        logger.info(
            'Total number of discarded "out of range" tiles = {0}'.format(
                discarded_tiles
            )
        )

    def to_mbtiles(self, filename, zoom=None, tile_bounds=False, drop_empty=False):
        """
        Export tile package to mbtiles v1.1 file, optionally limited to zoom
        levels.  If filename exists, it will be overwritten.  If filename
        does not include the suffix '.mbtiles' it will be added.

        Parameters
        ----------
        filename: string
            name of mbtiles file
        zoom: int or list-like of ints, default: None (all tiles exported)
            zoom levels to export to mbtiles
        tile_bounds: bool
            if True, will use the tile bounds of the highest zoom level exported to determine tileset bounds
        drop_empty: bool, default False
            if True, tiles that are empty will not be output
        """

        if self.format.lower() == "mixed":
            raise ValueError(
                "Mixed format tiles are not supported for export to mbtiles"
            )

        if not filename.endswith(".mbtiles"):
            filename = "{0}.mbtiles".format(filename)

        with MBtiles(filename, "w") as mbtiles:
            if zoom is None:
                zoom = self.zoom_levels
            elif isinstance(zoom, int):
                zoom = [zoom]
            zoom = sorted(zoom)

            # Zooms for which at least some tiles have not been dropped
            real_zooms = set()

            def tile_generator():
                for tile in self.read_tiles(zoom, flip_y=True):
                    if (
                        drop_empty
                        and hashlib.sha1(tile.data).hexdigest() in EMPTY_TILES
                    ):
                        continue
                    real_zooms.add(tile.z)
                    yield tile

            mbtiles.write_tiles(tile_generator())

            zoom = sorted(real_zooms)

            if tile_bounds:
                # Calculate bounds based on maximum zoom to be exported
                highest_zoom = zoom[-1]
                min_row, max_row = mbtiles.row_range(highest_zoom)
                min_col, max_col = mbtiles.col_range(highest_zoom)

                # get upper left coordinate
                xmin, ymax = mercantile.ul(min_col, min_row, highest_zoom)

                # get bottom right coordinate
                # since we are using ul(), we need to go 1 tile beyond the range to get the right side of the
                # tiles we have
                xmax, ymin = mercantile.ul(max_col + 1, max_row + 1, highest_zoom)

                bounds = (xmin, ymin, xmax, ymax)

            else:
                bounds = self.bounds

            # Center zoom level is middle zoom level
            center = "{0:4f},{1:4f},{2}".format(
                bounds[0] + (bounds[2] - bounds[0]) / 2.0,
                bounds[1] + (bounds[3] - bounds[1]) / 2.0,
                (zoom[0] + zoom[-1]) // 2,
            )

            mbtiles.meta.update(
                {
                    "name": self.name,
                    "description": self.summary,  # not description, which is optional
                    "version": self.version,
                    "attribution": self.attribution,
                    "tags": self.tags,
                    "credits": self.credits,
                    "use_constraints": self.use_constraints,
                    "type": "overlay",
                    "format": self.format.lower().replace("jpeg", "jpg")[:3],
                    "bounds": ",".join("{0:4f}".format(v) for v in bounds),
                    "center": center,
                    "minzoom": zoom[0],
                    "maxzoom": zoom[-1],
                    "legend": json.dumps(self.legend) if self.legend else "",
                }
            )

    def to_disk(
        self,
        path,
        zoom=None,
        scheme="arcgis",
        drop_empty=False,
        path_format="{z}/{x}/{y}.{ext}",
    ):
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

        ext = self.format.lower().replace("jpeg", "jpg")
        if ext == "mixed":
            raise ValueError("Mixed format tiles are not supported for export to disk")
        ext = ext[:3]

        if not scheme in ("xyz", "arcgis"):
            raise ValueError("scheme must be xyz or arcgis")

        if not os.path.exists(path):
            os.makedirs(path)
        elif len(os.listdir(path)) > 0:
            raise IOError("Output directory must be empty.")

        if zoom is None:
            zoom = self.zoom_levels
        elif isinstance(zoom, int):
            zoom = [zoom]

        zoom = list(zoom)
        zoom.sort()

        for tile in self.read_tiles(zoom, flip_y=(scheme == "xyz")):
            if drop_empty and hashlib.sha1(tile.data).hexdigest() in EMPTY_TILES:
                continue

            filename = path_format.format(z=tile.z, x=tile.x, y=tile.y, ext=ext)
            out_path = os.path.join(path, os.path.split(filename)[0])
            if not os.path.exists(out_path):
                os.makedirs(out_path)

            with open(os.path.join(path, filename), "wb") as outfile:
                outfile.write(tile.data)

    def close(self):
        self._fp.close()
