from flask import Flask, Blueprint, request, session, g, redirect, url_for, abort, render_template, flash, jsonify, Response
from flask.ext.sqlalchemy import SQLAlchemy

from flask.ext import admin, wtf, login
from flask.ext.admin.contrib import sqlamodel
from flask.ext.admin.contrib.sqlamodel import filters
from flask.ext.admin.actions import action
from time import sleep
from app import main

import json

vlan = Blueprint('vlan', __name__)

import vlan_views
from vlan_models import Port, Switch, Vlan, Site, Portgroup, Vlangroup, get_ports

@vlan.route("/")
def index():
    if login.current_user.is_anonymous() == True:
        return redirect(url_for('login_view') + '?next=/vlan/')

    portgrp = main.db.session.query(Portgroup).filter(Portgroup.assigned_to.any(main.User.username==login.current_user.username)).all()
    ports = main.db.session.query(Port).filter(Port.assigned_to.any(main.User.username==login.current_user.username)).all();
    
    # go thru each group and extract ports, using set get rid of duplicates
    temp_ports = []
    for i in portgrp:
        temp_ports += set(i.ports)

    ports = set(temp_ports + ports)

    for port in ports:
        # setting current vlan for this ports
        port.current_vlan = port.getVLAN()

    vlangrp = main.db.session.query(Vlangroup).filter(Vlangroup.assigned_to.any(main.User.username==login.current_user.username)).all()
    vlans = main.db.session.query(Vlan).filter(Vlan.assigned_to.any(main.User.username==login.current_user.username)).all();

    temp_vlans = []
    for i in vlangrp:
        temp_vlans += set(i.vlans)

    vlans = set(vlans + temp_vlans)
    vlans = sorted(vlans, key=lambda v: v.number)

    return render_template('vlan/vlan_home.html', user=login.current_user, ports=ports, vlans=vlans)

#### API ####
@vlan.route("/api/set", methods=["POST"])
def setPortController():
    switch_id = request.form.get('switch_id')
    port_id = request.form.get('port_id')
    new_vlan = request.form.get('new_vlan')

    port_auth = filter( lambda user: user == login.current_user, Port.query.get(port_id).assigned_to )
    vlan_auth = filter( lambda user: user == login.current_user, Vlan.query.filter(Vlan.number==new_vlan).first().assigned_to )

    if len(port_auth) > 0 and len(vlan_auth) > 0:
        ret = str(Port.query.get(port_id).setVLAN(new_vlan))
        return ret

    return "Unauthorized request"

@vlan.route("/api/get_ports", methods=["POST"])
def getPortsController():
    switch_id = request.form.get('switch_id')
    data = get_ports(switch_id)
    data = map(lambda x: dict({'id': x.id, 'name': x.name, 'number': x.number}), data)

    new_data = {}

    for i in data:
        id = i.get("id");
        new_data[id] = {}
        new_data[id]["id"] = i.get("id")
        new_data[id]["name"] = i.get("name")
        new_data[id]["number"] = i.get("number")

    obj = {"length": len(new_data), "data": new_data}
    return jsonify(obj);

@vlan.route("/api/add_port", methods=["POST"])
def addPortController():
    if login.current_user.is_admin() == False:
        return "failure"

    port_id = request.form.get("port")
    user_id = request.form.get("user")

    user = main.User.query.get(user_id)
    port = Port.query.get(port_id)

    if (user in port.assigned_to) == False:
        port.assigned_to.append(user)
        main.db.session.commit()

    return "success"

@vlan.route("/api/remove_port", methods=["POST"])
def removePortController():
    if login.current_user.is_admin() == False:
        return "failure"

    port_id = request.form.get("port")
    user_id = request.form.get("user")

    user = main.User.query.get(user_id)
    port = Port.query.get(port_id)

    if (user in port.assigned_to) == True:
        port.assigned_to.remove(user)
        main.db.session.commit()

    return "success"