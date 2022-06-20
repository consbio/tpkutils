# ArcGIS Tile Package Utilities

A Python 3 library for reading tiles and exporting tools from
[ArcGIS Tile Packages](http://desktop.arcgis.com/en/arcmap/10.3/map/working-with-arcmap/about-tile-packages.htm)
which contain tile caches using the
[ArcGIS Compact Tile Cache](https://server.arcgis.com/en/server/10.3/publish-services/windows/inside-the-compact-cache-storage-format.htm)

![Python Tests](https://github.com/consbio/tpkutils/actions/workflows/python-tests.yml/badge.svg)

## Goals

-   easy access to tiles in a tile package
-   export to mbtiles, for hosting on any of a variety of mbtiles servers,
    such as [mbtileserver](https://github.com/consbio/mbtileserver)

## Our workflow

-   create beautiful maps in ArcGIS Desktop
-   [export to ArcGIS tile package](http://desktop.arcgis.com/en/arcmap/10.3/map/working-with-arcmap/how-to-create-a-tile-package.htm)
-   convert to mbtiles format using this package
-   host as an XYZ tile service using [mbtileserver](https://github.com/consbio/mbtileserver)

## Installation

```
pip install tpkutils --upgrade
```

## Usage

### Python API

Open a tile package:

```
from tpkutils import TPK

tpk = TPK('my_tiles.tpk')

# close when done
tpk.close()
```

Or use `with`:

```
with TPK('my_tiles.tpk') as tpk:
```

You can query basic information about the tile package:

```
tpk.bounds  # tuple of (xmin, ymin, xmax, ymax) in geographic coordinates
tpk.zoom_levels  # list of zoom levels available in package [0,1,...]
```

#### Tile access

You can iterate over individual tiles - for instance, to save to disk.
Tiles are returned as a
`namedtuple`: `Tile(z, x, y, data)`:

```
for tile in tpk.read_tiles():
    with open('{0}_{1}_{2}.png'.format(tile.x, tile.y, tile.z), 'wb') as outfile:
        outfile.write(tile.data)
```

You can also just read tiles for a given zoom level or levels:

```
tpk.read_tiles(zoom=[4])
```

By default, tiles are returned according to the ArcGIS tile scheme.
To output tiles in xyz scheme, the y-value needs to be flipped:

```
tpk.read_tiles(flip_y=True)
```

_Note:_ no direct interface to read a single tile or tiles specified by
x or y is currently provided.

### Export to mbtiles

You can export a tile package to a [MapBox mbtiles v1.1](https://github.com/mapbox/mbtiles-spec/blob/master/1.1/spec.md) file:

```
tpk.to_mbtiles('my_tiles.mbtiles')
```

Or just export a subset of zoom levels:

```
tpk.to_mbtiles('fewer_tiles.mbtiles', zoom=[0,1,2,3,4])
```

_Note:_

-   tiles are output to mbtiles format in xyz tile scheme.
-   [mixed format](http://desktop.arcgis.com/en/arcmap/10.3/map/working-with-arcmap/about-tile-packages.htm)
    tiles are not supported for export to mbtiles.

### Export to disk

You can export the tile package to disk. Files are written to
'[z]/[x]/[y].[ext]' where [ext] is one png or jpg. Alternative file
names can be provided using the `--path-format` option.

By default, tiles will be written in the 'arcgis' tile scheme.
If using tiles in an XYZ tilevserver or client, use the 'xyz' tile
scheme.

Output directory must be empty.

```
tpk.to_disk('my_tiles')
```

You can export a subset of zoom levels, use the 'xyz' scheme, and
omit empty (completely blank PNG or completely white JPG) tiles:

```
tpk.to_disk('my_tiles', zoom=[0,1,2], scheme='xyz', drop_empty=True)
```

_Note:_

-   not recommended for large tile packages, as this will
    potentially create a large number of directories and files.
-   'mixed' format is not supported

### Metadata / descriptive attributes

Basic attributes describing the tile package are extracted from
configuration files in the tile package. These are typically populated
from the user interface for the ArcGIS tile package tool:

-   name: autopopulated by ArcGIS tile package tool, based on filename of map document
-   description: optional field in ArcGIS tile package tool
-   summary: required field in ArcGIS tile package tool
-   tags: required field in ArcGIS tile package tool
-   credits: optional field in ArcGIS tile package tool
-   use_constraints: optional field in ArcGIS tile package tool

#### MBtiles metadata

The metadata table in the mbtiles file is created from the attributes
of the tile package. Right now, any of these attributes can be
overwritten to control the contents of this table:

```
tpk.name = 'Some new name'
tpk.description = 'This is a much better description'
tpk.to_mbtiles(...)
```

Two additional attributes are exposed specifically for use in mbtiles:

```
tpk.version  # version of tileset, defaults to 1.0.0
tpk.attribution  # copyright / attribution statement.  Used by some
                 # clients for attribution info shown on map.
```

## Command line interface

You can also use the command line to perform export operations:

```
$ tpk export mbtiles --help
Usage: tpk export mbtiles [OPTIONS] TPK_FILENAME MBTILES_FILENAME

  Export the tile package to mbtiles format

Options:
  -z, --zoom TEXT  Limit zoom levels to export: "0,1,2"
  --overwrite      Overwrite existing mbtiles file  [default: False]
  -v, --verbose    Verbose output
  --help           Show this message and exit.
```

```
$ tpk export disk --help
Usage: tpk export disk [OPTIONS] TPK_FILENAME PATH

  Export the tile package to disk: z/x/y.<ext> or pattern specified using
  --path-format option.

  Will use the 'arcgis' tile scheme by default.  If using with an XYZ tile
  server or client, use the 'xyz' tile scheme.

  Not recommended for higher zoom levels as this will produce large
  directory trees.

Options:
  -z, --zoom TEXT        Limit zoom levels to export: "0,1,2"
  --scheme [xyz|arcgis]  Tile numbering scheme: xyz or arcgis  [default:
                         arcgis]
  --drop-empty           Drop empty tiles from output
  --path-format TEXT     Format expression for output tile files, within
                         output path. Must contain parameters for z, x, y, and
                         ext (extension).  [default: {z}/{x}/{y}.{ext}]
  -p, --preview          Preview the exported tiles in a simple map.
  -v, --verbose          Verbose output
  --help                 Show this message and exit.
```

## Note

All tile packages are assumed to follow the Web Mercator Tiling Scheme
(Google/Bing/etc), and be in the Web Mercator coordinate reference system.

Developed and tested using image tile packages created using ArcGIS 10.3;
however, these appear to use the 10.1 compact bundle format.

ArcGIS Server 10.3 introduced a new version of the compact bundle,
which is not handled here yet. If you want this, please submit an issue
with a small test file in 10.3 format.

Tile packages created using other versions may not work correctly
(please log an issue with test data).

Versions from ArcGIS older than 10.1 are unlikely to be supported.


## Changes:

### 0.8.0 (unreleased)
- removed Python 2 support


### 0.7.0

-   added ability to drop empty tiles when exporting to mbtiles via `drop_empty` option
-   added ability to drop completely transparent tiles in addition to completely white or black tiles
-   added ability to calculate tile bounds from highest zoom level exported to mbtiles
-   corrected zoom levels for tilesets where tiles start at zoom levels greater than 0
-   added `--tile-bounds` option to command line interface to calculate bounds from tiles available at highest exported zoom level
-   added `--drop-empty` option to command line interface to drop empty tiles when creating mbtiles

## Credits:

Tile package format is described [here](https://gdbgeek.wordpress.com/2012/08/09/demystifying-the-esri-compact-cache/).

Inspired by:

-   [tiler-arcgis-bundle](https://github.com/FuZhenn/tiler-arcgis-bundle)
-   [mbutil](https://github.com/mapbox/mbutil)
-   [node-mbtiles](https://github.com/mapbox/node-mbtiles)

SQL for creating mbtiles database derived from
[node-mbtiles](https://github.com/mapbox/node-mbtiles)

ArcGIS is a trademark of of [ESRI](http://esri.com) and is used here
to refer to specific technologies. No endorsement by ESRI is implied.

## License:

See LICENSE.md
