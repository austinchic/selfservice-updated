from flask import Flask, Blueprint, request, session, g, redirect, url_for, abort, render_template, flash, jsonify, Response
from flask.ext.sqlalchemy import SQLAlchemy

from time import sleep
from app import main

import json

######## SNMP ########
import lib.snmp as snmp
######################

class Site(main.db.Model):
    id = main.db.Column(main.db.Integer, primary_key=True, nullable=False)
    name = main.db.Column(main.db.String(80), unique=True, nullable=False)

    def __unicode__(self):
        return self.name

class Switch(main.db.Model):
    id = main.db.Column(main.db.Integer, primary_key=True)
    name = main.db.Column(main.db.String(80), unique=True, nullable=False)
    host_address = main.db.Column(main.db.String(120), nullable=False)
    host_port = main.db.Column(main.db.Integer, nullable=False)
    vlan_oid = main.db.Column(main.db.String(120), nullable=False)
    interface_oid = main.db.Column(main.db.String(120), nullable=False)
    site_id = main.db.Column(main.db.Integer, main.db.ForeignKey(Site.id), nullable=False)
    site = main.db.relationship(Site, backref='switch')
    community_read = main.db.Column(main.db.String(120), nullable=False)
    community_write = main.db.Column(main.db.String(120), nullable=False)

    def updatePorts(self):
        # convert string OID to a tuple
        vlan_oid = snmp.convertOID(self.interface_oid)
        results = snmp.snmpWalk(self.host_address, self.host_port, vlan_oid, self.community_read)

        for i in results:
            query = Port.query.filter(Port.number==i).filter(Port.switch_id==self.id)
            count = query.count()

            # updating current records
            for m in query.all():
                m.name = results[i]

            if count == 0:
                p = Port()
                p.switch = self
                p.number = i
                p.name = results[i]
            
                main.db.session.add(p)
        main.db.session.commit()

    def __unicode__(self):
        return self.name

user_port_table = main.db.Table('user_port', main.db.Model.metadata,
    main.db.Column('user_id', main.db.Integer, main.db.ForeignKey('user.id')),
    main.db.Column('port_id', main.db.Integer, main.db.ForeignKey('port.id')))

class Port(main.db.Model):
    id = main.db.Column(main.db.Integer, primary_key=True, nullable=False)
    name = main.db.Column(main.db.String(80), nullable=False)
    number = main.db.Column(main.db.Integer, nullable=False)
    switch_id = main.db.Column(main.db.Integer, main.db.ForeignKey(Switch.id), nullable=False)
    switch = main.db.relationship(Switch, backref='port')
    assigned_to = main.db.relationship('User', secondary=user_port_table)

    def __unicode__(self):
        return self.name

    def getVLAN(self):
        # convert string OID to a tuple
        vlan_oid = snmp.convertOID(self.switch.vlan_oid)
        # getting current vlan for this port
        return snmp.snmpGet(self.switch.host_address, self.switch.host_port, vlan_oid, int(self.number), self.switch.community_read)

    def setVLAN(self, new_vlan):

        # used to shut/open the port after setting a new vlan
        valve_oid = (1,3,6,1,2,1,2,2,1,7)

        # convert string OID to a tuple
        vlan_oid = snmp.convertOID(self.switch.vlan_oid)

        # setting current vlan for this port
        ret = snmp.snmpSet(self.switch.host_address, self.switch.host_port, vlan_oid, int(self.number), new_vlan, self.switch.community_write)

        # closing the port
        snmp.snmpSet(self.switch.host_address, self.switch.host_port, valve_oid, int(self.number), 2, self.switch.community_write)

        # waiting 5 seconds
        sleep(5)

        # opening port
        snmp.snmpSet(self.switch.host_address, self.switch.host_port, valve_oid, int(self.number), 1, self.switch.community_write)

        return ret
        
# create many to many relationship
user_vlan_table = main.db.Table('user_vlan', main.db.Model.metadata,
    main.db.Column('user_id', main.db.Integer, main.db.ForeignKey('user.id')),
    main.db.Column('vlan_id', main.db.Integer, main.db.ForeignKey('vlan.id')))

class Vlan(main.db.Model):
    id = main.db.Column(main.db.Integer, primary_key=True)
    name = main.db.Column(main.db.String(80))
    number = main.db.Column(main.db.Integer, unique=True, nullable=False)
    assigned_to = main.db.relationship('User', secondary=user_vlan_table, backref="user")
    
    def __unicode__(self):
        return self.name


# Groups of Objects

portgroup_port_table = main.db.Table('portgroup_port', main.db.Model.metadata, 
    main.db.Column('portgroup_id', main.db.Integer, main.db.ForeignKey('portgroup.id')), 
    main.db.Column('port_id', main.db.Integer, main.db.ForeignKey('port.id')))

portgroup_user_table = main.db.Table('portgroup_user', main.db.Model.metadata,
    main.db.Column('portgroup_id', main.db.Integer, main.db.ForeignKey('portgroup.id')), 
    main.db.Column('user_id', main.db.Integer, main.db.ForeignKey('user.id')))

class Portgroup(main.db.Model):
    id = main.db.Column(main.db.Integer, primary_key=True)
    name = main.db.Column(main.db.String(80))
    ports = main.db.relationship('Port', secondary=portgroup_port_table)

    assigned_to = main.db.relationship('User', secondary=portgroup_user_table)
    def __unicode__(self):
        return self.name


vlangroup_vlan_table = main.db.Table('vlangroup_vlan', main.db.Model.metadata, 
    main.db.Column('vlangroup_id', main.db.Integer, main.db.ForeignKey('vlangroup.id')), 
    main.db.Column('vlan_id', main.db.Integer, main.db.ForeignKey('vlan.id')))

vlangroup_user_table = main.db.Table('vlangroup_user', main.db.Model.metadata,
    main.db.Column('vlangroup_id', main.db.Integer, main.db.ForeignKey('vlangroup.id')), 
    main.db.Column('user_id', main.db.Integer, main.db.ForeignKey('user.id')))

class Vlangroup(main.db.Model):
    id = main.db.Column(main.db.Integer, primary_key=True)
    name = main.db.Column(main.db.String(80))
    vlans = main.db.relationship('Vlan', secondary=vlangroup_vlan_table)

    assigned_to = main.db.relationship('User', secondary=vlangroup_user_table)
    def __unicode__(self):
        return self.name

def get_switches():
    switches = Switch.query.all()
    return switches

def get_ports(switch_id):
    ports = Port.query.filter(Port.switch_id==switch_id).all()
    ports = filter(lambda port: port != None, ports);
    return ports

def get_vlans():
    vlans = Vlan.query.all()
    return vlans

