import math


def geo_bounds(xmin, ymin, xmax, ymax):
    """
    Project web mercator bounds to geographic.

    Parameters
    ----------
    xmin: float
    ymin: float
    xmax: float
    ymax: float

    Returns
    -------
    [xmin, ymin, xmax, ymax] in geographic coordinates
    """

    merc_max = 20037508.342789244
    if any(abs(v) > merc_max for v in (xmin, xmax, ymin, ymax)):
        raise ValueError('Web Mercator bounds must be within world domain')

    sma = 6378137.0  # semi-major axis for WGS84
    rad2deg = 180.0 / math.pi  # radians to degrees

    lons = [(x * rad2deg / sma) for x in (xmin, xmax)]
    lats = [
        ((math.pi * 0.5) - 2.0 * math.atan(math.exp(-y / sma))) * rad2deg
        for y in (ymin, ymax)
    ]
    return [lons[0], lats[0], lons[1], lats[1]]




### Possibly useful, saved below

# only useful for a specific tile but need index
# row = int(BUNDLE_DIM * int(y / BUNDLE_DIM))
# column = int(BUNDLE_DIM * int(x / BUNDLE_DIM))
# index = BUNDLE_DIM * (x - column) + (y - row) # offset into file
# def get_tile_offset(bundlx, index):
#     bundlx.seek(16 + INDEX_SIZE * index)
#     return buffer_to_offset(bundlx.read(INDEX_SIZE))

#
# def read_bundle_tiles(bundle_filename):
#     """
#     Read all non-empty tiles from bundle.
#
#     Parameters
#     ----------
#     bundle_filename: string
#         name of ArcGIS bundle filename
#
#     Returns
#     -------
#     generator(Tile)
#         Only returns non-empty tiles
#     """
#
#     # parse filename to determine row / col offset for bundle
#     # offsets are in hex
#     file_root = os.path.splitext(os.path.basename(bundle_filename))[0]
#     r_offset, c_offset = [int(x, 16) for x in file_root.lstrip('R').split('C')]
#     # zoom level is from name of containing folder
#     z = int(os.path.split(os.path.dirname(bundle_filename))[1].lstrip('L'))
#
#     with open(bundle_filename.replace('.bundle', '.bundlx'), 'rb') as bundlx:
#         bundlx.seek(16)  # 16 byte header
#         index_bytes = bundlx.read()
#
#     with open(bundle_filename, 'rb') as bundle:
#         index = 0
#         max_index = BUNDLE_DIM**2
#         while index < max_index:
#             data = read_tile(
#                 bundle,
#                 buffer_to_offset(index_bytes[index * INDEX_SIZE:(index + 1) * INDEX_SIZE])
#             )
#             if data:
#                 row = math.floor(float(index) / BUNDLE_DIM)
#                 col = index - row * BUNDLE_DIM
#                 yield Tile(c_offset + col, r_offset + row, z, data)
#
#             index += 1
#
#
# def read_all_tiles(folder):
#     """
#     Read all non-empty tiles from all zoom levels in folder using a generator
#     expression.
#
#     Parameters
#     ----------
#     folder: string
#         folder containing _alllayers directory
#
#     Returns
#     -------
#     generator(Tile)
#         Only returns non-empty tiles
#     """
#
#     for f in glob.glob('{0}/_alllayers/L*/*.bundle'.format(folder)):
#         yield from read_bundle_tiles(f)
#
#
# def read_zoom_level_tiles(folder, zoom):
#     """
#     Read all non-empty tiles from the zoom level using a generator expression.
#
#     Parameters
#     ----------
#     folder: string
#         folder containing _alllayers directory
#
#     zoom: int or list-like
#         zoom level or list-like of zoom levels
#
#     Returns
#     -------
#     generator(Tile)
#         Only returns non-empty tiles
#     -------
#
#     """
#     if isinstance(zoom, int):
#         zoom = [zoom]
#
#     for z in zoom:
#         print('zoom', z)
#         for f in glob.glob('{0}/_alllayers/L{1:02}/*.bundle'.format(folder, z)):
#             yield from read_bundle_tiles(f)
