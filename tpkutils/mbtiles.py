import os
import sqlite3
import hashlib
import logging


logger = logging.getLogger('tpkutils')


class MBtiles(object):
    """
    Interface for creating and populating mbtiles files.
    """
    def __init__(self, filename, mode='r'):
        """
        Creates an open mbtiles file.  Must be closed after all data are added.

        Parameters
        ----------
        filename: string
            name of output mbtiles file
        mode: string, one of ('r', 'w')
            if 'w', existing mbtiles file will be deleted first
        """

        if mode not in ('r', 'w'):
            raise ValueError("Mode must be 'r' or 'w'")

        if os.path.exists(filename):
            if mode == 'w':
                os.remove(filename)
        elif mode == 'r':
            raise IOError('mbtiles not found: {0}'.format(filename))

        connect_mode = 'ro' if mode == 'r' else 'rwc'
        self.db = sqlite3.connect(
            'file:{0}?mode={1}'.format(filename, connect_mode), uri=True, isolation_level=None)
        self.cursor = self.db.cursor()

        self.cursor.execute('PRAGMA synchronous=OFF')
        self.cursor.execute('PRAGMA journal_mode=OFF')  # TODO: DELETE or WAL?
        self.cursor.execute('PRAGMA locking_mode=EXCLUSIVE')

        # initialize tables
        schema = open(__file__.replace('.py', '_schema.sql')).read()
        self.cursor.executescript(schema)
        self.db.commit()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def add_tile(self, z, x, y, data):
        """
        Add a tile to the mbtiles file.  Note: this is not as performant as
        add_tiles function for inserting several tiles at once.

        Parameters
        ----------
        z: int
            zoom level
        x: int
            tile column
        y: int
            tile row
        data: bytes
            tile data bytes
        """

        id = hashlib.sha1(data).hexdigest()

        self.cursor.execute(
            'INSERT OR IGNORE INTO images (tile_id, tile_data) values (?, ?)',
            (id, sqlite3.Binary(data))  # is this necessary
        )

        self.cursor.execute(
            'INSERT INTO map '
            '(zoom_level, tile_column, tile_row, tile_id) '
            'values(?, ?, ?, ?)',
            (z, x, y, id)
        )

        self.db.commit()

    def add_tiles(self, tiles):
        """
        Add several tiles to mbtiles file, using a single transaction.
        Parameters
        ----------
        tiles: iterable of Tile(z, x, y, data) tuples
        """

        self.cursor.execute('BEGIN')

        try:
            for tile in tiles:
                id = hashlib.sha1(tile.data).hexdigest()
                self.cursor.execute(
                    'INSERT OR IGNORE INTO images (tile_id, tile_data) values (?, ?)',
                    (id, sqlite3.Binary(tile.data))
                )

                self.cursor.execute(
                    'INSERT INTO map '
                    '(zoom_level, tile_column, tile_row, tile_id) '
                    'values(?, ?, ?, ?)',
                    (tile.z, tile.x, tile.y, id)
                )

            self.cursor.execute('COMMIT')

        except self.db.Error:  # pragma: no cover
            logger.exception('Error inserting tiles, rolling back database')
            self.cursor.execute('ROLLBACK')

    def set_metadata(self, metadata):
        """
        Set the metadata table using a dictionary of string key-value pairs.

        Parameters
        ----------
        metadata: dict
            dictionary containing string key-value pairs
        """

        self.cursor.executemany(
            'INSERT INTO metadata (name, value) values (?, ?)',
            metadata.items())

        self.db.commit()

    def close(self):
        """
        Close the mbtiles file.  Vacuums database prior to closing.
        """

        self.cursor.execute('ANALYZE')
        self.cursor.execute('VACUUM')
        self.cursor.close()
        self.db.close()
