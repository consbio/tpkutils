# ArcGIS Tile Package Utilities

This library provides a interface into reading tiles and metadata [ArcGIS Tile Packages](http://desktop.arcgis.com/en/arcmap/10.3/map/working-with-arcmap/about-tile-packages.htm) which contain tile caches using the [ArcGIS Compact Tile Cache](https://server.arcgis.com/en/server/10.3/publish-services/windows/inside-the-compact-cache-storage-format.htm)

## Goals
* easy access to tiles in a tile package
* export to mbtiles, for hosting on any of a variety of mbtiles servers, such as [mbtileserver](https://github.com/consbio/mbtileserver)



## Usage

### Python API

Open a tile package:
```
from tpkutils import TPK

tpk = TPK('my_tiles.tpk')
```


#### Tile access

You can iterate over individual tiles - for instance, to save to disk.  Tiles are returned as a 
`namedtuple`: `Tile(z, x, y, data)`:
```
for tile in tpk.read_tiles():
    with open('{0}_{1}_{2}.png'.format(tile.x, tile.y, tile.z), 'wb') as outfile:
        outfile.write(tile.data)
```

You can also just read tiles for a  given zoom level or levels:
```
tpk.read_tiles(zoom=[4])
```

*Note:* no direct interface to read a single tile or tiles specified by x or y is currently provided.



#### Export to mbtiles

You can export a tile package to a [MapBox mbtiles v1.1](https://github.com/mapbox/mbtiles-spec/blob/master/1.1/spec.md)  file:
```
tpk.to_mbtiles('my_tiles.mbtiles')
```

Or just export a subset of zoom levels:
```
tpk.to_mbtiles('fewer_tiles.mbtiles', zoom=[0,1,2,3,4])
```




## Note
Developed and tested using image tile packages created using ArcGIS 10.3;
however, these appear to use the 10.1 compact bundle format.

ArcGIS Server 10.3 introduced a new version of the compact bundle,
which is not handled here yet.  If you want this, please submit an issue
with a small test file in 10.3 format.

Tile packages created using other versions may not work correctly
(please log an issue with test data).

Versions from ArcGIS older than 10.1 are unlikely to be supported.

The interface for reading tiles and exporting to mbtiles uses the xyz
scheme.  This means that the tile y value is flipped from the
underlying ArcGIS scheme.


## Credits:
Tile package format is described [here](https://gdbgeek.wordpress.com/2012/08/09/demystifying-the-esri-compact-cache/).

Inspired by:
* [tiler-arcgis-bundle](https://github.com/FuZhenn/tiler-arcgis-bundle)
* [mbutiles](https://github.com/mapbox/mbutils)
* [node-mbtiles](https://github.com/mapbox/node-mbtiles)

SQL for creating mbtiles database derived from
[node-mbtiles](https://github.com/mapbox/node-mbtiles)

ArcGIS is a trademark of of [ESRI](http://esri.com) and is used here
to refer to specific technologies.  No endorsement by ESRI is implied.