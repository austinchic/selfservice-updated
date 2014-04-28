#!/usr/bin/env python
from flask import Flask, redirect, url_for, session, request, g,\
        render_template, jsonify, make_response, Blueprint, flash

from flask.ext.sqlalchemy import SQLAlchemy

from flask.ext import admin, wtf, login
from flask.ext.admin.contrib import sqlamodel
from flask.ext.admin.contrib.sqlamodel import filters
import os

main = Flask(__name__)
main.config.from_pyfile('config/config.cfg')

### Authentication ###
from lib.ldapauth import LDAPAuth
filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config/ldap.cfg')
ldap_auth = LDAPAuth(filename);

# Create in-memory database
main.db = SQLAlchemy(main)

# Create models
class User(main.db.Model):
    id = main.db.Column(main.db.Integer, primary_key=True)
    username = main.db.Column(main.db.String(80), unique=True)
    email = main.db.Column(main.db.String(120), unique=True)
    active = main.db.Column(main.db.Boolean)
    admin = main.db.Column(main.db.Boolean)

    # Flask-Login integration

    def is_admin(self):
        return self.admin

    def is_authenticated(self):
        return True

    def is_active(self):
        return self.active

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id

    def __unicode__(self):
        return self.username

# add to app namespace
main.User = User

# Define login and registration forms (for flask-login)        
class LoginForm(wtf.Form):
    login = wtf.TextField(validators=[wtf.required()])
    password = wtf.PasswordField(validators=[wtf.required()])

    def validate_login(self, field):
        user = self.get_user()

        if ldap_auth.auth(self.login.data, self.password.data) != 1:
            flash(u'Login failed', category='error')
            raise wtf.ValidationError('Invalid user/password')

        if user is None:
            # add user to db
            user = User()
            user.username = self.login.data
            user.active = True
            user.admin = True if user.username == "bmays" or user.username == "cjohnson" else False
            main.db.session.add(user)
            main.db.session.commit()

    def get_user(self):
        return main.db.session.query(User).filter_by(username=self.login.data).first()

# Initialize flask-login
def init_login():
    main.login_manager = login.LoginManager()
    main.login_manager.setup_app(main)

    # Create user loader function
    @main.login_manager.user_loader
    def load_user(user_id):
        return main.db.session.query(User).get(user_id)

### Routes ###
@main.route('/')
def index():
    return render_template('index.html', user=login.current_user)

@main.route('/login/', methods=('GET', 'POST'))
def login_view():
    form = LoginForm(request.form)
    if form.validate_on_submit():
        user = form.get_user()
        login.login_user(user)
        
        if request.args.get('next') is not None:
            return redirect(request.args.get('next'))

        return redirect(url_for('index'))

    return render_template('login.html', form=form)

@main.route('/logout/')
@login.login_required
def logout_view():
    login.logout_user()
    return redirect(url_for('index'))

######################

##### Admin Pages ####
class AdminIndexView(admin.AdminIndexView):
    def is_accessible(self):
        if login.current_user.is_anonymous() == True:
            return False

        return login.current_user.is_admin()

    @admin.base.expose('/')
    def index(self):
        return render_template("admin/index.html", admin_view=self)

# View for admin page that restricts access using Flask-Login
class AdminModelView(sqlamodel.ModelView):
    def is_accessible(self):
        if login.current_user.is_anonymous() == True:
            return False

        return login.current_user.is_admin()


# Create admin
main.admin = admin.Admin(main, 'Polycom Engineering Services - Self Service', index_view=AdminIndexView())
main.admin.main = main

# Add views
main.admin.add_view(AdminModelView(User, main.db.session))
######################

####### VLANS ########
from vlan_app.vlan import vlan
main.register_blueprint(vlan, url_prefix='/vlan')
######################

####### SHARK ########
from shark_app.shark import shark
main.register_blueprint(shark, url_prefix='/packet_capture')
######################

# Create DB
main.db.create_all()

init_login()


