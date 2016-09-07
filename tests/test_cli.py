import os
import sqlite3
import pytest
from click.testing import CliRunner
from tpkutils.cli import cli


@pytest.fixture(scope='function')
def runner():
    return CliRunner()



def test_export_mbtiles(runner, tmpdir):
    tpk = 'tests/data/ecoregions.tpk'
    mbtiles = str(tmpdir.join('test.mbtiles'))

    result = runner.invoke(cli, ['export', 'mbtiles', tpk, mbtiles])

    assert result.exit_code == 0
    assert os.path.exists(mbtiles)

    with sqlite3.connect(mbtiles) as db:
        cursor = db.cursor()

        # # Verify zoom levels present
        cursor.execute('select zoom_level from tiles order by zoom_level')
        zoom_levels = [x[0] for x in cursor.fetchall()]
        assert zoom_levels == [0, 1, 2, 3]

        cursor.close()


def test_export_mbtiles_zoom(runner, tmpdir):
    tpk = 'tests/data/ecoregions.tpk'
    mbtiles = str(tmpdir.join('test.mbtiles'))

    result = runner.invoke(cli, ['export', 'mbtiles', tpk, mbtiles,
                                 '--zoom', '0,1'])

    assert result.exit_code == 0
    assert os.path.exists(mbtiles)

    with sqlite3.connect(mbtiles) as db:
        cursor = db.cursor()

        # # Verify zoom levels present
        cursor.execute('select zoom_level from tiles order by zoom_level')
        zoom_levels = [x[0] for x in cursor.fetchall()]
        assert zoom_levels == [0, 1]

        cursor.close()