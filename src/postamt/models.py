from sqlalchemy import engine_from_config
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from zope.sqlalchemy import ZopeTransactionExtension

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
    nexthop = Column(Integer)#, ForeignKey("Domain.id"))

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
    transport = Column(Integer, ForeignKey("Transport.id"))
    rclass = Column(Integer, default=30)


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
    domain = Column(Integer, ForeignKey("Domain.id"))
    active = Column(Boolean, default=True)
    transport = Column(Integer, ForeignKey("Transport.id"))
    rclass = Column(Integer, default=30)


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
    address = Column(Integer, ForeignKey("Address.id"), nullable=False)
    active = Column(Boolean, default=True)
    target = Column(Integer, ForeignKey("Address.id"), nullable=False)
    extension = Column(Text, nullable=False)


class VMailbox(Base):
    """
    CREATE TABLE "VMailbox" (id INTEGER PRIMARY KEY,
	active INTEGER DEFAULT 1, uid INTEGER,
	gid INTEGER, home TEXT, password TEXT,
	FOREIGN KEY(id) REFERENCES Address(id));
    """

    __tablename__ = "VMailbox"

    id = Column(Integer, ForeignKey("Address.id"), primary_key=True)
    active = Column(Boolean, default=True)
    uid = Column(Integer)
    gid = Column(Integer)
    home = Column(Text)
    password = Column(Text)


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


class UserUtil(object):
    def __init__(self, registry):
        self.password_context = registry.queryUtility(ICryptContext)
        print "pwc", id(self), id(self.password_context)

    def encrypt(self, raw_password):
        """Encrypt a password with bcrypt."""

        password = self.password_context.encrypt(raw_password.strip())
        return unicode(password)

    def verify(self, raw_password, password):
        """Verifies the raw_password against a password hash."""

        return self.password_context.verify(raw_password, password)

    def verify_login(self, username, password):
        user = User.by_name(username)
        if user:
            return user if self.verify(password, user.password) else None

    def create_user(self, username, password, email):
        user = User(
            name=username,
            password=self.encrypt(password),
            email=email
        )
        DBSession.add(user)
        DBSession.commit()

        return user


def get_user_util(request):
    return UserUtil(request.registry)


def create_defaults(user_util):

    # basic db entries
    admin_group = Group.query.filter(Group.name == "admin").first()
    if not admin_group:
        admin_group = Group(name="admin")

        DBSession.add(admin_group)

    user = User.by_name('foobar')
    if not user:
        user = user_util.create_user('foobar', "xyzwort", "diefans@gmail.com")
        user.groups.append(admin_group)

        DBSession.add(user)

    DBSession.commit()


def includeme(config):
    """ Bind sql engine."""

    engine = engine_from_config(config.registry.settings, "sqlalchemy.")
    initialize_sql(engine)
