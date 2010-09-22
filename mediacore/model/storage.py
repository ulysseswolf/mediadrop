# This file is a part of MediaCore, Copyright 2009 Simple Station Inc.
#
# MediaCore is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# MediaCore is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging

from datetime import datetime

from sqlalchemy import Table, Column
from sqlalchemy.orm import dynamic_loader, mapper, reconstructor
from sqlalchemy.orm.interfaces import MapperExtension
from sqlalchemy.types import Boolean, DateTime, Integer, Unicode, PickleType

from mediacore.lib.storage import StorageEngine
from mediacore.model.media import MediaFile, MediaFileQuery
from mediacore.model.meta import DBSession, metadata

log = logging.getLogger(__name__)

storage = Table('storage', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('engine_type', Unicode(30), nullable=False),
    Column('display_name', Unicode(100), nullable=False, unique=True),
    Column('pickled_data', PickleType, nullable=False),
    Column('is_primary', Boolean, nullable=False, default=False),
    Column('created_on', DateTime, nullable=False, default=datetime.now),
    Column('modified_on', DateTime, nullable=False, default=datetime.now,
                                                    onupdate=datetime.now),
    mysql_engine='InnoDB',
    mysql_charset='utf8',
)

storage_mapper = mapper(
    StorageEngine, storage,
    polymorphic_on=storage.c.engine_type,
    properties={
        # Rename the data attr since its automatically de-pickled by sqlalchemy
        '_data': storage.c.pickled_data,

        # Avoid conflict with the abstract StorageEngine.engine_type property
        '_engine_type': storage.c.engine_type,

        # Make the storage engine available on MediaFile instances
        'files': dynamic_loader(
            MediaFile,
            backref='storage',
            query_class=MediaFileQuery,
            passive_deletes=True,
        ),
    },
)

def add_engine_type(engine_cls):
    """Register this storage engine with the ORM."""
    log.debug('Registering engine %r: %r', engine_cls.engine_type, engine_cls)
    mapper(engine_cls,
           inherits=storage_mapper,
           polymorphic_identity=engine_cls.engine_type)

# Add our built-in storage engines to the polymorphic ORM mapping.
for engine in StorageEngine:
    add_engine_type(engine)

# Automatically add new engines as they're registered by plugins.
StorageEngine.add_register_observer(add_engine_type)

def fetch_engines():
    """Return all engines ordered in descending priority.

    :rtype: list
    :returns: Instances of :class:`~mediacore.lib.storage.StorageEngine`
        subclasses.

    """
    query = DBSession.query(StorageEngine)\
        .order_by(StorageEngine.is_primary.asc(),
                  StorageEngine.created_on.desc())
    return query.all()
