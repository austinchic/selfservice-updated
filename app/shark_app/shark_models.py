from flask import Flask, Blueprint, request, session, g, redirect, url_for, abort, render_template, flash, jsonify, Response
from flask.ext.sqlalchemy import SQLAlchemy
import requests
from app import main

import json

######## SHARK API ########
import lib.shark_api as shark_api
######################

# create many to many relationship
user_sharkjob_table = main.db.Table('user_sharkjob', main.db.Model.metadata,
    main.db.Column('user_id', main.db.Integer, main.db.ForeignKey('user.id')),
    main.db.Column('job_id', main.db.Integer, main.db.ForeignKey('job.id')))

class Job(main.db.Model):
    id = main.db.Column(main.db.Integer, primary_key=True)
    job_name = main.db.Column(main.db.String(80))
    job_filter = main.db.Column(main.db.String(500))
    job_interface = main.db.Column(main.db.String(120))
    job_id = main.db.Column(main.db.String(120))        ## used for riverbed api
    job_limit = main.db.Column(main.db.Integer)

    user = main.db.relationship('User', secondary=user_sharkjob_table, uselist=False)

    def __unicode__(self):
        return self.name

    def __init__(self, name, job_filter, interface, limit, user):
        self.api = shark_api.SharkAPI()
        self.job_name = name
        self.job_filter = job_filter
        self.job_interface = interface
        self.job_limit = limit
        self.job_snapshot_size = 65535  # in bytes, number of packets in the capture
        self.job_status = {}            # stores state, size, start time and end time
        self.user = user
        self.user_notified = False      # used to notify user once when the job is done

        # send post request to api, on return populate id && status
        payload = {
            "name": self.job_name,
            "bpf_filter": self.job_filter,
            "interface_name": self.job_interface,
            "start_immediately": False,
            "snap_length": self.job_snapshot_size,
            "packet_retention": {"size_limit": self.job_limit},
            "stop_rule": {}
        }

        response = self.api.create_job(payload)
        if response.status_code == 201:
            resp = json.loads(response.text)
            self.job_id = resp.get('id')
        else:
            self.error = response

    def download(self):
        if getattr(self, "api", None) is None:
            self.api = shark_api.SharkAPI()

        return self.api.download_job(self.job_id)

    def start(self):
        if getattr(self, "api", None) is None:
            self.api = shark_api.SharkAPI()

        self.api.start_job(self.job_id)

    def stop(self):
        if self.is_stopped() == False:
            self.api.stop_job(self.job_id)

    def get_status(self):
        if getattr(self, "api", None) is None:
            self.api = shark_api.SharkAPI()

        job = self.api.get_job(self.job_id)
        if isinstance(job, requests.Response):
            return job

        return job.get('status')

    def is_stopped(self):
        return self.get_status().get('state') == "STOPPED"

    def delete(self):
        if getattr(self, "api", None) is None:
            self.api = shark_api.SharkAPI()

        self.api.delete_job(self.job_id)
        main.db.session.delete(self)
        main.db.session.commit()
