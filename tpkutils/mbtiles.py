# see: https://github.com/mapbox/mbutil/blob/master/mbutil/util.py
# see: https://github.com/mapbox/rio-mbtiles/blob/master/mbtiles/scripts/cli.py
# optimization see: https://github.com/lukasmartinelli/mbtoolbox


import os
import sqlite3

# TODO: enable context manager
class Mbtiles(object):
    def __init__(self, filename, overwrite=False):
        if os.path.exists(filename) and not overwrite:
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


    def close(self):
        self.cursor.close()
        self.db.close()