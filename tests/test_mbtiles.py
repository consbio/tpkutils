import sqlite3
import pytest

from tpkutils import TPK
from tpkutils.mbtiles import MBtiles


def test_read_missing_file(tmpdir):
    mbtiles_filename = str(tmpdir.join('test.mbtiles'))
    with pytest.raises(IOError):
        MBtiles(mbtiles_filename)


def test_invalid_mode(tmpdir):
    mbtiles_filename = str(tmpdir.join('test.mbtiles'))

    with pytest.raises(ValueError):
        MBtiles(mbtiles_filename, mode='r+w')


def test_add_tile(tmpdir):
    tpk = TPK('tests/data/states_filled.tpk')
    mbtiles_filename = str(tmpdir.join('test.mbtiles'))

    tile = next(tpk.read_tiles(zoom=1, flip_y=True))
    mbtiles = MBtiles(mbtiles_filename, mode='w')
    mbtiles.add_tile(tile.z, tile.x, tile.y, tile.data)
    mbtiles.close()
    tpk.close()

    with sqlite3.connect(mbtiles_filename) as db:
        cursor = db.cursor()
        cursor.execute('select zoom_level from tiles order by zoom_level')
        zoom_levels = [x[0] for x in cursor.fetchall()]
        assert zoom_levels == [1]

