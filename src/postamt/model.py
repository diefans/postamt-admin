from sqlalchemy import engine_from_config
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.orm.exc import NoResultFound
#from zope.sqlalchemy import ZopeTransactionExtension

import os
from datetime import datetime
import sys

from sqlalchemy import \
    event, UniqueConstraint, not_, Table, Column, ForeignKey, func, ForeignKeyConstraint
from sqlalchemy.orm.util import object_mapper
from sqlalchemy.types import \
    Unicode, Integer, DateTime, Enum, UnicodeText, Boolean, String, Text
from sqlalchemy.orm import relation, synonym, backref



def initialize_sql(engine):
    """Bind the engine to the session and create all tables."""

    DBSession.configure(bind=engine)
    Base.metadata.bind = engine


def create_model(engine):
    """Create all the model tables."""

    Base.metadata.create_all(engine)


DBSession = scoped_session(sessionmaker())
#DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
Base = declarative_base()
Base.query = DBSession.query_property()
metadata = Base.metadata


class Transport(Base):
    """
    CREATE TABLE "Transport" (id INTEGER PRIMARY KEY,
	active INTEGER DEFAULT 1, transport TEXT, nexthop INTEGER,
	mx INTEGER DEFAULT 1, port INTEGER,
	UNIQUE (transport,nexthop,mx,port));
    """
    __tablename__ = "Transport"
    __table_args__ = (UniqueConstraint("transport", "nexthop", "mx", "port"),
                      ForeignKeyConstraint(
                              ['nexthop'],
                              ['Domain.id'],
                              use_alter=True,
                              name='fk_nexthop_domain_id'
                          ))

    id = Column(Integer, primary_key=True)
    active = Column(Boolean, default=True)
    transport = Column(Text)
    nexthop_id = Column('nexthop', Integer)#, ForeignKey("Domain.id"))
    nexthop = relation("Domain", backref="transports", foreign_keys="Transport.nexthop_id")

    # lookup mx
    mx = Column(Boolean, default=True)

    port = Column(Integer)



class Domain(Base):
    """
    CREATE TABLE "Domain" (id INTEGER PRIMARY KEY, name TEXT,
	active INTEGER DEFAULT 1, class INTEGER DEFAULT 0,
	owner INTEGER DEFAULT 0, transport INTEGER,
	rclass INTEGER DEFAULT 30, UNIQUE (name),
	FOREIGN KEY(transport) REFERENCES Transport(id);
    """

    __tablename__ = "Domain"

    id = Column(Integer, primary_key=True)
    name = Column(Text, unique=True)
    active = Column(Boolean, default=True)
    klass = Column('class', Integer, default=0)
    owner = Column(Integer, default=0)
    transport_id = Column('transport', Integer, ForeignKey("Transport.id"))
    transport = relation("Transport", primaryjoin="Domain.transport_id == Transport.id")
    rclass = Column(Integer, default=30)

    def __repr__(self):
        return "{0.name}, {active}, {0.klass}, {0.rclass}"\
            .format(self, active="active" if self.active else "inactive")

    @classmethod
    def find(cls, domain_name):
        try:
            return cls.query\
                .filter(cls.name == domain_name)\
                .one()

        except NoResultFound:
            pass


class Address(Base):
    """
    CREATE TABLE "Address" (id INTEGER PRIMARY KEY,
	localpart TEXT NOT NULL, domain INTEGER NOT NULL,
	active INTEGER DEFAULT 1, transport INTEGER, rclass INTEGER,
	FOREIGN KEY(domain) REFERENCES Domain(id),
	FOREIGN KEY(transport) REFERENCES Transport(id),
	UNIQUE (localpart, domain));
    """

    __tablename__ = "Address"
    __table_args__ = (UniqueConstraint("localpart", "domain"), )

    id = Column(Integer, primary_key=True)
    localpart = Column(Text, nullable=False)
    domain_id = Column('domain', Integer, ForeignKey("Domain.id"))
    domain = relation("Domain", backref="addresses")
    active = Column(Boolean, default=True)
    transport_id = Column('transport', Integer, ForeignKey("Transport.id"))
    transport = relation("Transport", backref="addresses")
    rclass = Column(Integer, default=None, nullable=True)

    @property
    def name(self):
        return "{0.localpart}@{0.domain.name}".format(self)

    def __repr__(self):
        return "{0.name}, {active}, {0.rclass}"\
            .format(self, active="active" if self.active else "inactive")

    @classmethod
    def find(cls, address_name):
        """Lookup of address by joining the domain."""

        localpart, domain_name = address_name.split("@", 1)

        try:
            return cls.query\
                .join(Domain)\
                .filter(cls.localpart == localpart)\
                .filter(Domain.name == domain_name)\
                .one()

        except NoResultFound:
            pass


class Alias(Base):
    """
    CREATE TABLE "Alias" (id INTEGER PRIMARY KEY,
	address INTEGER NOT NULL, active INTEGER DEFAULT 1,
	target INTEGER NOT NULL, extension TEXT,
	FOREIGN KEY(address) REFERENCES Address(id)
	FOREIGN KEY(target) REFERENCES Address(id)
	UNIQUE(address, target, extension));
    """

    __tablename__ = "Alias"
    __table_args__ = (UniqueConstraint("address", "target", "extension"), )

    id = Column(Integer, primary_key=True)
    address_id = Column('address', Integer, ForeignKey("Address.id"), nullable=False)
    address = relation("Address", backref="sources", primaryjoin="Alias.address_id == Address.id")
    active = Column(Boolean, default=True)
    target_id = Column('target', Integer, ForeignKey("Address.id"), nullable=False)
    target = relation("Address", backref="targets", primaryjoin="Alias.target_id == Address.id")
    extension = Column(Text, nullable=True)

    def __repr__(self):
        return "{0.address.name} -> {0.target.name}, {active}"\
            .format(self, active="active" if self.active else "inactive")


class VMailbox(Base):
    """
    CREATE TABLE "VMailbox" (id INTEGER PRIMARY KEY,
	active INTEGER DEFAULT 1, uid INTEGER,
	gid INTEGER, home TEXT, password TEXT,
	FOREIGN KEY(id) REFERENCES Address(id));
    """

    __tablename__ = "VMailbox"

    id = Column('id', Integer, ForeignKey("Address.id"), primary_key=True)
    address = relation("Address", backref="mailbox")
    active = Column(Boolean, default=True)
    uid = Column(Integer)
    gid = Column(Integer)
    home = Column(Text)
    password = Column(Text)

    def __repr__(self):
        return "{0.address.name}, {active}, {0.home}"\
            .format(self, active="active" if self.active else "inactive")


class BScat(Base):
    """
    CREATE TABLE "BScat" (id INTEGER PRIMARY KEY,
	sender TEXT NOT NULL, priority INTEGER NOT NULL,
	target TEXT NOT NULL, UNIQUE (sender, priority));
    """

    __tablename__ = "BScat"
    __table_args__ = (UniqueConstraint("sender", "priority"), )

    id = Column(Integer, primary_key=True)
    sender = Column(Text, nullable=False)
    priority = Column(Integer, nullable=False)
    target = Column(Text, nullable=False)


def includeme(config):
    """ Bind sql engine."""

    engine = engine_from_config(config.registry.settings, "sqlalchemy.")
    initialize_sql(engine)
