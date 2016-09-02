# see: https://github.com/mapbox/mbutil/blob/master/mbutil/util.py
# see: https://github.com/mapbox/rio-mbtiles/blob/master/mbtiles/scripts/cli.py
# optimization see: https://github.com/lukasmartinelli/mbtoolbox

# Note: y might need to be flipped: https://github.com/mapbox/mbutil/blob/master/mbutil/util.py#L174


import os
import sqlite3
import hashlib


# TODO: enable context manager
class Mbtiles(object):
    def __init__(self, filename, overwrite=False):
        if os.path.exists(filename):
            if overwrite:
                os.remove(filename)
            else:
                raise IOError(
                    'Destination mbtiles file already exists, '
                    'will not overwrite: {0}'.format(filename)
                )
        self.db = sqlite3.connect(filename)  # isolation mode? isolation_level=None  (autocommit)  #TODO: optimize handling of transactions when inserting many times
        self.cursor = self.db.cursor()

        # initialize tables
        schema = open(__file__.replace('.py', '_schema.sql')).read()
        self.cursor.executescript(schema)
        self.db.commit()

    def add_tile(self, z, x, y, data):
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
        # data type casting?  All values are strings
        for k, v in metadata.items():
            self.cursor.execute(
                'INSERT INTO metadata (name, value) values (?, ?)',
                (k, v)
            )

    def close(self):
        self.cursor.execute('VACUUM')
        self.cursor.close()
        self.db.close()
