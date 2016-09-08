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

        # Verify zoom levels present
        cursor.execute('select zoom_level from tiles order by zoom_level')
        zoom_levels = [x[0] for x in cursor.fetchall()]
        assert zoom_levels == [0, 1]

        cursor.close()


def test_export_mbtiles_existing_output(runner, tmpdir):
    tpk = 'tests/data/ecoregions.tpk'
    mbtiles = str(tmpdir.join('test.mbtiles'))

    result = runner.invoke(cli, ['export', 'mbtiles', tpk, mbtiles])
    assert result.exit_code == 0
    assert os.path.exists(mbtiles)

    result = runner.invoke(cli, ['export', 'mbtiles', tpk, mbtiles])
    assert result.exit_code == 1
    assert 'Output exists and overwrite is false' in result.output

    result = runner.invoke(cli, ['export', 'mbtiles', tpk, mbtiles, '--overwrite'])
    assert result.exit_code == 0
    assert os.path.exists(mbtiles)


def test_export_mbtiles_verbosity(runner, tmpdir):
    tpk = 'tests/data/ecoregions.tpk'
    mbtiles = str(tmpdir.join('test.mbtiles'))
    result = runner.invoke(cli, ['export', 'mbtiles', tpk, mbtiles, '-v'])
    assert result.exit_code == 0
    # assert 'INFO:tpkutils' in result.output  # not working w/ pytest

    mbtiles = str(tmpdir.join('test2.mbtiles'))
    result = runner.invoke(cli, ['export', 'mbtiles', tpk, mbtiles, '-v', '-v'])
    assert result.exit_code == 0
    # assert 'DEBUG:tpkutils' in result.output  # not working w/ pytest


def test_export_disk(runner, tmpdir):
    tpk = 'tests/data/ecoregions.tpk'
    path = str(tmpdir.join('tiles'))

    result = runner.invoke(cli, ['export', 'disk', tpk, path])
    assert result.exit_code == 0
    assert os.path.exists(path)
    assert os.path.exists(os.path.join(path, '0/0_0.png'))


def test_export_disk_zoom(runner, tmpdir):
    tpk = 'tests/data/ecoregions.tpk'
    path = str(tmpdir.join('tiles'))

    result = runner.invoke(cli, ['export', 'disk', tpk, path,
                                 '--zoom', '1'])

    assert result.exit_code == 0
    assert os.path.exists(path)
    print(os.listdir(os.path.join(path, '1')))
    assert os.path.exists(os.path.join(path, '1/0_1.png'))
    assert not os.path.exists(os.path.join(path, '0/0_0.png'))


def test_export_disk_existing_output(runner, tmpdir):
    tpk = 'tests/data/ecoregions.tpk'
    path = str(tmpdir.join('tiles'))

    result = runner.invoke(cli, ['export', 'disk', tpk, path])
    assert result.exit_code == 0
    assert os.path.exists(path)

    result = runner.invoke(cli, ['export', 'disk', tpk, path])
    assert result.exit_code == 1
    assert 'Output directory must be empty' in result.output