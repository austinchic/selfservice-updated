from flask import Flask, Blueprint, request, session, g, redirect, url_for, abort, render_template, flash, jsonify, Response
from flask.ext.sqlalchemy import SQLAlchemy

from flask.ext import admin, wtf, login
from flask.ext.admin.contrib import sqlamodel
from flask.ext.admin.contrib.sqlamodel import filters
from flask.ext.admin.actions import action
from time import sleep
from app import main
import uuid
from datetime import date

import json, requests

shark = Blueprint('shark', __name__, url_prefix='/packet_capture')
from shark_models import Job

### Force authentication ###
@shark.before_request
def login_required():
    if login.current_user.is_anonymous() == True:
        return redirect(url_for('login_view') + '?next=/packet_capture/')

@shark.route("/")
def index():
    jobs = main.db.session.query(Job).filter(Job.user==login.current_user).all()

    ### if a job returns 404, delete it and remove from jobs list. ###
    for i in jobs:
        req = i.get_status()
        print req
        if isinstance(req, requests.Response):
            if req.status_code == 404:
                jobs.remove(i)
                i.delete()

    return render_template('shark/shark_home.html', user=login.current_user, jobs=jobs)

#### API ####
@shark.route("/api/create", methods=["POST"])
def create_job():

    job_host = request.form.get('job_filter')
    job_filter = "host " + str(job_host)
    job_name = request.form.get('job_name')
    job_size = request.form.get('job_size')
    job_interface = request.form.get('job_interface')

    try:
        job_size = long(job_size)
    except:
        pass

    if job_name == "" or job_name.isspace() or len(job_name) > 25 is True:
        flash('Error creating new capture job: invalid name.')
    elif job_interface == "null":
        flash('Error creating new capture job: invalid interface.')
    elif job_size is None or isinstance( job_size, long ) is False:
        flash('Error creating new capture job: invalid size.')
    else:
        job_size = long(job_size)
        j = Job(job_name, job_filter, job_interface, job_size, login.current_user)
        if getattr(j, 'error', None) is None:
            main.db.session.add(j)
            main.db.session.commit()
            flash("Created new job successfully.")
        else:
            flash(j.error.text)

    return redirect(url_for('shark.index'))

@shark.route("/api/start/<id>", methods=["GET"])
def job_start(id):
    job = main.db.session.query(Job).get(id)

    if user_owns_job(job, login.current_user) is True:
        job.start()
        return "Started"
    else:
        return "Unauthorized"

@shark.route("/api/stop/<id>", methods=["GET"])
def job_stop(id):
    job = main.db.session.query(Job).get(id)
    
    if user_owns_job(job, login.current_user) is True:
        job.stop()
        return "Stopped"
    else:
        return "Unauthorized"

@shark.route("/api/delete/<id>", methods=["GET"])
def job_delete(id):
    job = main.db.session.query(Job).get(id)

    if user_owns_job(job, login.current_user) is True:
        job.delete()
        return "Deleted"
    else:
        return "Unauthorized"

@shark.route("/api/status/<id>", methods=["GET"])
def job_status(id):
    try:
        job = main.db.session.query(Job).get(id)

        if user_owns_job(job, login.current_user) is True:
            return jsonify(job.get_status())
        else:
            return "Unauthorized"
    except:
        return "Unauthorized"

@shark.route("/api/download/<id>", methods=["GET"])
def download_capture(id):
    job = main.db.session.query(Job).get(id)

    if user_owns_job(job, login.current_user) is True:
        r = job.download()
        if r.status_code is 200:
            return Response(r.content, headers=r.headers, content_type='application/vnd.tcpdump.pcap')
        else:
            return redirect(url_for('shark.index'))
    else:
        return "Unauthorized"

### Checks to see if a user has permission to modify a job ###
def user_owns_job(job, user):
    try:
        if user == job.user:
            return True
        else:
            return False
    except:
        return False