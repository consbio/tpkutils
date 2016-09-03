import os
import sqlite3
from tpkutils import TPK


# First 50 bytes of the tile at z=2,x=0,y=1  (ArcGIS scheme), z=2,x=0,y=2 (xyz scheme)
TEST_TILE_BYTES = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x01\x00\x00\x00\x01\x00\x08\x06\x00\x00\x00\\r\xa8f\x00\x00\x00\tpHYs\x00\x00\x0e\xc4\x00\x00\x0e\xc4\x01'




def test_metadata():
    tpk = TPK('tests/data/ecoregions.tpk')

    assert tpk.version == '1.0.0'
    assert tpk.attribution == ''

    assert tpk.name == 'tilepackage7'
    assert tpk.description == 'map description'
    assert tpk.tags == 'package tags'
    assert tpk.credits == 'map credits'
    assert tpk.use_constraints == ''


def test_read_tile():
    tpk = TPK('tests/data/ecoregions.tpk')
    tile = next(tpk.read_tiles(zoom=[2]))

    assert tile.z == 2
    assert tile.x == 0
    assert tile.y == 1
    assert tile.data[:50] == TEST_TILE_BYTES


def test_export_mbtiles(tmpdir):
    tpk = TPK('tests/data/ecoregions.tpk')
    mbtiles_filename = str(tmpdir.join('test.mbtiles'))

    tpk.to_mbtiles(mbtiles_filename)
    tpk.close()

    assert os.path.exists(mbtiles_filename)

    with sqlite3.connect(mbtiles_filename) as db:
        cursor = db.cursor()

        # Verify tile data (note xyz scheme for select)
        cursor.execute(
            'select tile_data from tiles where zoom_level=2 '
            'and tile_column=0 and tile_row=2')
        data = cursor.fetchone()
        assert len(data) == 1
        assert data[0][:50] == TEST_TILE_BYTES

        # Verify zoom levels present
        cursor.execute('select zoom_level from tiles order by zoom_level')
        zoom_levels = [x[0] for x in cursor.fetchall()]
        assert zoom_levels == [0, 1, 2, 3]

        # Verify bounds in metadata
        cursor.execute('select value from metadata where name="bounds"')
        bounds = cursor.fetchone()
        assert bounds
        assert bounds[0] == ','.join('{0:4f}'.format(v) for v in tpk.bounds)

        cursor.close()
