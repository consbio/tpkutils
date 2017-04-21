import os
import sqlite3
import pytest
import hashlib


from tpkutils import TPK



# First 50 bytes of the tile at z=2,x=0,y=1  (ArcGIS scheme), z=2,x=0,y=2 (xyz scheme)
TILE_2_0_2_SHA1 = '20e903aa7604a7c1a6d05f2f68e10a23ce5695f2'

def test_metadata():
    with TPK('tests/data/states_filled.tpk') as tpk:
        assert tpk.version == '1.0.0'
        assert tpk.attribution == ''

        assert tpk.name == 'states_filled'
        assert tpk.summary == 'states'
        assert tpk.tags == 'states'
        assert tpk.description == ''
        assert tpk.credits == 'US Census Bureau'
        assert tpk.use_constraints == ''

        assert tpk.bounds == [-179.23108600000003, -14.601813000000014, 179.859681, 71.441059]


def test_read_tile():
    with TPK('tests/data/states_filled.tpk') as tpk:
        tile = next(tpk.read_tiles(zoom=[2]))

        assert tile.z == 2
        assert tile.x == 0
        assert tile.y == 1
        assert hashlib.sha1(tile.data).hexdigest() == TILE_2_0_2_SHA1

        tile2 = next(tpk.read_tiles(zoom=2))
        assert tile2 == tile


def test_export_mbtiles(tmpdir):
    with TPK('tests/data/states_filled.tpk') as tpk:
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
        assert len(data) == 1  # make sure we got one tile back
        assert hashlib.sha1(data[0]).hexdigest() == TILE_2_0_2_SHA1

        # Verify zoom levels present
        cursor.execute('select distinct zoom_level from tiles order by zoom_level')
        zoom_levels = {x[0] for x in cursor.fetchall()}
        assert zoom_levels == {0, 1, 2, 3, 4}

        # Verify bounds in metadata
        cursor.execute('select value from metadata where name="bounds"')
        bounds = cursor.fetchone()
        assert bounds
        assert bounds[0] == ','.join('{0:4f}'.format(v) for v in tpk.bounds)

        cursor.close()


def test_export_mbtiles_add_suffix(tmpdir):
    tpk = TPK('tests/data/states_filled.tpk')
    mbtiles_filename = str(tmpdir.join('test'))

    tpk.to_mbtiles(mbtiles_filename)
    tpk.close()

    assert os.path.exists('{0}.mbtiles'.format(mbtiles_filename))


def test_export_mbtiles_int_zoom(tmpdir):
    tpk = TPK('tests/data/states_filled.tpk')
    mbtiles_filename = str(tmpdir.join('test.mbtiles'))

    tpk.to_mbtiles(mbtiles_filename, zoom=1)
    tpk.close()

    assert os.path.exists(mbtiles_filename)


def test_export_mbtiles_mixed_format(tmpdir):
    tpk = TPK('tests/data/states_filled.tpk')
    tpk.format = 'mixed'  # this is a hack to make test fail, need a test file for this

    mbtiles_filename = str(tmpdir.join('test.mbtiles'))

    with pytest.raises(ValueError):
        tpk.to_mbtiles(mbtiles_filename)

    tpk.close()


def test_export_disk_existing_output(tmpdir):
    tpk = TPK('tests/data/states_filled.tpk')
    path = str(tmpdir.join('tiles'))
    os.makedirs(path)
    with open(os.path.join(path, 'test.txt'), 'w') as outfile:
        outfile.write('Foo')

    with pytest.raises(IOError):
        tpk.to_disk(path)

    tpk.close()


def test_export_disk_int_zoom(tmpdir):
    tpk = TPK('tests/data/states_filled.tpk')
    path = str(tmpdir.join('tiles'))

    tpk.to_disk(path, zoom=1)
    tpk.close()

    assert os.path.exists(path)
    assert os.path.exists(os.path.join(path, '1/0/0.png'))
    assert not os.path.exists(os.path.join(path, '0/0/0.png'))


def test_export_disk_mixed_format(tmpdir):
    tpk = TPK('tests/data/states_filled.tpk')
    tpk.format = 'mixed'  # this is a hack to make test fail, need a test file for this

    path = str(tmpdir.join('tiles'))

    with pytest.raises(ValueError):
        tpk.to_disk(path)

    tpk.close()


def test_export_disk_invalid_scheme(tmpdir):
    tpk = TPK('tests/data/states_filled.tpk')
    path = str(tmpdir.join('tiles'))

    with pytest.raises(ValueError):
        tpk.to_disk(path, scheme='bad')

    tpk.close()


def test_alt_root_name(tmpdir):
    tpk = TPK('tests/data/alt_root_name.tpk')
    mbtiles_filename = str(tmpdir.join('test'))

    tpk.to_mbtiles(mbtiles_filename)
    tpk.close()

    assert os.path.exists('{0}.mbtiles'.format(mbtiles_filename))