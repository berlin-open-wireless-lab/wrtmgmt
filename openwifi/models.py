from sqlalchemy import (
    Column,
    Integer,
    Text,
    ForeignKey,
    Table,
    Boolean,
    Binary,
    DateTime
    )

from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy.orm import (
    backref,
    relationship,
    scoped_session,
    sessionmaker,
    )

from zope.sqlalchemy import ZopeTransactionExtension

from .guid import GUID

from pkg_resources import iter_entry_points
import importlib

import pyuci
import json

DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
Base = declarative_base()

# import Plugin
for iter_entry in iter_entry_points(group="OpenWifi.plugin", name="models"):
    importlib.import_module(iter_entry.load())

essid_association_table = Table('essid_association', Base.metadata,
        Column('radio_id', Integer, ForeignKey('radio.id')),
        Column('essid_id', Integer, ForeignKey('essid.id')))

template_association_table = Table('template_association', Base.metadata,
        Column('templates_id', Text, ForeignKey('templates.id')),
        Column('openwrt_id', GUID, ForeignKey('openwrt.uuid')))

ssh_key_association_table = Table('sshkey_association', Base.metadata,
        Column('sshkey_id', Integer, ForeignKey('ssh_auth_keys.id')),
        Column('openwrt_id', GUID, ForeignKey('openwrt.uuid')))

class OpenWrt(Base):
    __tablename__ = 'openwrt'
    uuid = Column(GUID, primary_key=True)
    name = Column(Text, nullable=True)
    address = Column(Text) # ip or host
    distribution = Column(Text) # lazus / polar / openWrt
    version = Column(Text) # 1,2, ... 10.04 , ... trunk
    configured = Column(Boolean)
    configuration = Column(Text)
    login = Column(Text)
    password = Column(Text)
    master_conf_id = Column(Integer, ForeignKey('MasterConfigurations.id'))
    templates = relationship("Templates",secondary=template_association_table,backref="openwrt")
    ssh_keys = relationship("SshKey",secondary=ssh_key_association_table,backref="openwrt")
    capabilities = Column(Text)
    communication_protocol = Column(Text)

    def __init__(self, name, address, distribution, version, device_uuid, login, password, configured=False):
        self.set(name, address, distribution, version, device_uuid, login, password, configured)

    def set(self, name, address, distribution, version, device_uuid, login, password, configured=False):
        self.name = name
        self.address = address
        self.distribution = distribution
        self.version = version
        self.configured = configured
        self.login = login
        self.password = password
        try:
            self.uuid = device_uuid
        except ValueError:
            self.uuid = device_uuid

    def jsonParsable(self):
        if self.configuration:
            conf = json.loads(self.configuration)
        else:
            conf = None
        return {'name'         : self.name,
                'address'      : self.address,
                'distribution' : self.distribution,
                'version'      : self.version,
                'configured'   : self.configured,
                'configuration': conf,
                'login'        : self.login,
                'password'     : self.password,
                'uuid'         : str(self.uuid) }

    def setData(self, key, value):
        if key == 'name':
            self.name = value
        if key == 'address':
            self.address = value
        if key == 'distribution':
            self.distribution = value
        if key == 'version':
            self.version = value
        if key == 'configuration':
            self.configuration = value
        if key == 'login':
            self.login = value
        if key == 'password':
            self.password = value

class ConfigArchive(Base):
    __tablename__ = "configarchive"
    date = Column(DateTime)
    configuration = Column(Text)
    router_uuid = Column(GUID)
    id = Column(Text, primary_key=True)

    def __init__(self, date, configuration, router_uuid, id):
        self.configuration = configuration
        self.date          = date
        self.router_uuid   = router_uuid
        self.id            = id

class OpenWifiSettings(Base):
    __tablename__ = 'OpenWifiSettings'
    key = Column(Text, primary_key=True)
    value = Column(Text)

    def __init__(self, key, value):
        self.key = key
        self.value = value

class Templates(Base):
    __tablename__ = "templates"
    name = Column(Text)
    id   = Column(Text, primary_key=True)
    metaconf = Column(Text)

    def __init__(self, name, metaconf, id):
        self.name = name
        self.metaconf = metaconf
        self.id = id

class AccessPoint(Base):
    __tablename__ = 'accesspoint'
    id = Column(Integer, primary_key=True)
    name = Column(Text, unique=True)
    address = Column(Text) # ip or host
    sshkey = relationship('SshKey') # private key to access this ap
    sshkey_id = Column(Integer, ForeignKey('ssh_auth_keys.id'))
    sshhostkey = Column(Text) # remote host key
    hardware = Column(Text)
    radio = relationship("Radio", backref='accesspoint')

    def __init__(self, name, address, hardware, radio_amount_2ghz, radio_amount_5ghz):
        self.name = name
        self.hardware = hardware
        self.address = address

        for i in range(radio_amount_2ghz):
            self.radio.append(Radio('unspecific', 2))

        for i in range(radio_amount_5ghz):
            self.radio.append(Radio('unspecific', 5))

class Radio(Base):
    __tablename__ = 'radio'
    id = Column(Integer, primary_key=True)
    ap_id = Column(Integer, ForeignKey('accesspoint.id'))
    hardware = Column(Text)
    # replace band with enum(2, 5, 2+5)
    band = Column(Integer) # 2 => 2ghz, 5 => 5ghz
    channel = Column(Integer)
    essid = relationship("Essid", secondary=essid_association_table)
    txpower = Column(Integer)

    def __init__(self, hardware, band):
        self.hardware = hardware
        self.band = band

class Essid(Base):
    __tablename__ = 'essid'
    id = Column(Integer, primary_key=True)
    essid = Column(Text)
    bssid = Column(Text)

    def __init__(self):
        pass

class SshKey(Base):
    __tablename__ = 'ssh_auth_keys'
    id = Column(Integer, primary_key=True)
    comment = Column(Text)
    key = Column(Text)

    def __init__(self,key,comment,id):
        self.id = id
        self.comment = comment
        self.key = key


class MasterConfiguration(Base):
    __tablename__ = "MasterConfigurations"
    id = Column(Integer, primary_key=True)
    configurations = relationship("Configuration", backref="masterconf")
    openwrt = relationship("OpenWrt", backref="masterconf")
    links = relationship("ConfigurationLink", backref="masterconf")

    def __init__(self, id):
        self.id = id

    def exportUCI(self):
        uci = pyuci.Uci()
        for conf in self.configurations:
            package = uci.add_package(conf.package)
            package.add_config_json(json.loads(conf.data))
        return uci

    def exportJSON(self):
        uci = self.exportUCI()
        return uci.export_json()

from_conf_to_link = Table('from_conf_to_link_table', Base.metadata,
        Column('conf_id', Integer, ForeignKey('Configurations.id')),
        Column('link_id', Integer, ForeignKey('Links.id')))

from_link_to_conf = Table('from_link_to_conf_table', Base.metadata,
        Column('link_id', Integer, ForeignKey('Links.id')),
        Column('conf_id', Integer, ForeignKey('Configurations.id')))

class Configuration(Base):
    __tablename__ = "Configurations"
    id = Column(Integer, primary_key=True)
    name = Column(Text)
    data = Column(Text)
    package = Column(Text)
    to_links = relationship("ConfigurationLink", secondary=from_conf_to_link, backref="from_config")
    master_conf_id = Column(Integer, ForeignKey('MasterConfigurations.id'))

    def __init__(self, id):
        self.id = id

    def getLinkByName(self, name):
        for link in self.to_links:
            if link.data == name:
                return link

class ConfigurationLink(Base):
    __tablename__ = "Links"
    id = Column(Integer, primary_key=True)
    data = Column(Text)
    to_config = relationship("Configuration", secondary=from_link_to_conf, backref="from_links")
    master_conf_id = Column(Integer, ForeignKey('MasterConfigurations.id'))

    def __init__(self, id):
        self.id = id
