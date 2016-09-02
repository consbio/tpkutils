# ArcGIS Tile Package Utilities

This library provides a interface into reading tiles and metadata
[ArcGIS Tile Packages](http://desktop.arcgis.com/en/arcmap/10.3/map/working-with-arcmap/about-tile-packages.htm)
which contain tile caches using the 
[ArcGIS Compact Tile Cache](https://server.arcgis.com/en/server/10.3/publish-services/windows/inside-the-compact-cache-storage-format.htm)


## Usage

Open a tile package:
```
from tpkutils import TPK

tpk = TPK('my_tiles.tpk')
```


Export to a 
[MapBox mbtiles v1.1](https://github.com/mapbox/mbtiles-spec/blob/master/1.1/spec.md) 
file:
```
tpk.to_mbtiles('my_tiles.mbtiles')
```

Or just export a subset of zoom levels:
```
tpk.to_mbtiles('fewer_tiles.mbtiles', zoom=[0,1,2,3,4])
```


For more direct access, iterate over individual tiles - for instance,
to save to disk.  Tiles are returned as a 
`namedtuple`: `Tile(z, x, y, data)`:
```
for tile in tpk.read_tiles():
    with open('{0}_{1}_{2}.png'.format(tile.x, tile.y, tile.z), 'wb') as outfile:
        outfile.write(tile.data)
```




## Note
Developed and tested using image tile packages created using ArcGIS 10.3.

Tile packages created using other versions may not work correctly
(please log an issue with test data).

Versions from ArcGIS older than 10.1 are unlikely to be supported.



## Credits:
Tile package format is described [here](https://gdbgeek.wordpress.com/2012/08/09/demystifying-the-esri-compact-cache/).

Inspired by [tiler-arcgis-bundle](https://github.com/FuZhenn/tiler-arcgis-bundle).