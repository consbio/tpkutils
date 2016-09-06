import os
import sqlite3
import hashlib


# TODO: enable context manager
class Mbtiles(object):
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

        if mode == 'w' and os.path.exists(filename):
                os.remove(filename)

        connect_mode = 'ro' if mode == 'r' else 'rwc'
        self.db = sqlite3.connect(
            'file:{0}?mode={1}'.format(filename, connect_mode), uri=True)  # isolation mode? isolation_level=None  (autocommit)  #TODO: optimize handling of transactions when inserting many times
        self.cursor = self.db.cursor()

        # initialize tables
        schema = open(__file__.replace('.py', '_schema.sql')).read()
        self.cursor.executescript(schema)
        self.db.commit()

    def add_tile(self, z, x, y, data):
        """
        Add a tile to the mbtiles file.

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

    def set_metadata(self, metadata):
        """
        Set the metadata table using a dictionary of string key-value pairs.

        Parameters
        ----------
        metadata: dict
            dictionary containing string key-value pairs
        """

        for k, v in metadata.items():
            self.cursor.execute(
                'INSERT INTO metadata (name, value) values (?, ?)',
                (k, v)
            )

    def close(self):
        """
        Close the mbtiles file.  Vacuums database prior to closing.
        """

        self.cursor.execute('VACUUM')
        self.cursor.close()
        self.db.close()
