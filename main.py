from flask import Flask, render_template, request, url_for, redirect, flash, send_from_directory, Blueprint, session
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_wtf import FlaskForm
import pandas
from datetime import datetime, timedelta
import my_functions
from wtforms import StringField, SubmitField, PasswordField, BooleanField, ValidationError, EmailField, IntegerField, \
    SelectField
from wtforms.validators import DataRequired, EqualTo, Length, InputRequired
from flask_bootstrap import Bootstrap
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from sqlalchemy import select, delete, update, inspect
from flask_migrate import Migrate
from sqlalchemy.orm import Session
import time
import random
import MySQLdb
import plotly
import plotly.express as px
import json
import plotly.io as pio
import threading
import os

test = True
app = Flask(__name__)
draft_bp = Blueprint('draft', __name__)
socketio = SocketIO(
    app,
    async_mode='gevent',          # Change from 'eventlet' to 'gevent'
    message_queue=os.environ.get('REDIS_URL'),
    cors_allowed_origins='*'
)

# --- Timer Management ---
nomination_timers = {}  # nomination_id: threading.Timer

app.config['SECRET_KEY'] = 'secret-key-goes-here'
# Old SQLite DB
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
# New
# app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://username:password@localhost/db_name'
# if test:
#     import no_push
#     app.config['SQLALCHEMY_DATABASE_URI'] = no_push.my_sql_config
# Heroku SQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://urpkh4m7l378b:p0ca7da822b3823177e9879b78d7561c458d2185364439e2a6b51828147a8ee3c@cd5vlri6nnqe17.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/d1vrtkcrdmm43p'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db, compare_type=True)
Bootstrap(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

year = 2022
weeks = [num for num in range(1, 15)]
week_choices = {number: str(number) for number in range(1, 16)}

"get_data should be set to true to request data from the CFB API"
get_data = False
""
get_upcoming_games = False
updated_users_with_teams = {}


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), nullable=False, unique=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(1000), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow())
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_account = db.Column(db.Boolean, default=False)
    league_manager = db.relationship('League', backref='manager', cascade="all, delete-orphan")
    leagues = db.relationship('List_of_leagues_update1', backref='member', cascade="all, delete-orphan")
    player_teams = db.relationship('Player_weekly_info', backref='player_teams', cascade="all, delete-orphan")
    waiver_info = db.relationship('Waiver_Info', backref='user_waiver_info', cascade="all, delete-orphan")
    league_membership = db.relationship('League_members_update1', backref='member2', cascade="all, delete-orphan")

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return '<Name %r>' % self.name


class League(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    league_name = db.Column(db.String(100), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow())
    league_manager = db.Column(db.Integer, db.ForeignKey('user.id'))
    league_id_for_list_of_leagues = db.relationship('List_of_leagues_update1', backref='league_id',
                                                    cascade="all, delete-orphan")
    league_members = db.relationship('League_members_update1', backref='members', cascade="all, delete-orphan")
    players_teams = db.relationship('Player_weekly_info', backref='players_teams', cascade="all, delete-orphan")
    waiver_info = db.relationship('Waiver_Info', backref='league_waiver_info', cascade="all, delete-orphan")
    league_password = db.Column(db.String(100))
    draft_complete = db.Column(db.Boolean, default=False)
    draft_date = db.Column(db.DateTime, nullable=True)
    waivers_already_executed = db.Column(db.Boolean, default=False)
    matchups_already_generated = db.Column(db.Boolean, default=False)


class League_members_update1(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    league_id = db.Column(db.Integer, db.ForeignKey('league.id'))
    member = db.Column(db.Integer, db.ForeignKey('user.id'))


class List_of_leagues_update1(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    league = db.Column(db.Integer, db.ForeignKey('league.id'))


class Player_weekly_info(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    league = db.Column(db.Integer, db.ForeignKey('league.id'))
    week = db.Column(db.Integer, default=1)
    faab = db.Column(db.Integer, default=100)
    previous_weeks_score = db.Column(db.Float, default=0)
    this_weeks_score = db.Column(db.Float, default=0)
    total_wins = db.Column(db.Integer, default=0)
    team_1 = db.Column(db.String(100), nullable=True, default=None)
    team_2 = db.Column(db.String(100), nullable=True, default=None)
    team_3 = db.Column(db.String(100), nullable=True, default=None)
    team_4 = db.Column(db.String(100), nullable=True, default=None)


class Football_Teams(db.Model):
    __tablename__ = 'Football_Teams' if os.environ.get('FLASK_ENV') == 'development' else 'football__teams'
    id = db.Column(db.Integer, primary_key=True)
    team = db.Column(db.String(100), nullable=True)
    updated_this_week = db.Column(db.Boolean, default=False)
    playing_now = db.Column(db.Boolean, default=False)
    upcoming_opponent = db.Column(db.String(100), nullable=True)
    previous_opponent = db.Column(db.String(100), nullable=True, default="")
    previous_result = db.Column(db.String(1), nullable=True, default="")
    date_and_time_of_game = db.Column(db.DateTime)
    current_score = db.Column(db.Float, default=0)
    conference = db.Column(db.String(30), nullable=True)
    chance_to_win = db.Column(db.Float, default=0)
    ap_ranking = db.Column(db.Integer, default=None)
    opponent_ap_ranking = db.Column(db.Integer, default=None)
    opponent_p5 = db.Column(db.Boolean, default=False)
    week0_score = db.Column(db.Float)
    week1_score = db.Column(db.Float)
    week2_score = db.Column(db.Float)
    week3_score = db.Column(db.Float)
    week4_score = db.Column(db.Float)
    week5_score = db.Column(db.Float)
    week6_score = db.Column(db.Float)
    week7_score = db.Column(db.Float)
    week8_score = db.Column(db.Float)
    week9_score = db.Column(db.Float)
    week10_score = db.Column(db.Float)
    week11_score = db.Column(db.Float)
    week12_score = db.Column(db.Float)
    week13_score = db.Column(db.Float)
    week14_score = db.Column(db.Float)
    week15_score = db.Column(db.Float)
    week0_opponent = db.Column(db.String(50), nullable=True, default="")
    week1_opponent = db.Column(db.String(50), nullable=True, default="")
    week2_opponent = db.Column(db.String(50), nullable=True, default="")
    week3_opponent = db.Column(db.String(50), nullable=True, default="")
    week4_opponent = db.Column(db.String(50), nullable=True, default="")
    week5_opponent = db.Column(db.String(50), nullable=True, default="")
    week6_opponent = db.Column(db.String(50), nullable=True, default="")
    week7_opponent = db.Column(db.String(50), nullable=True, default="")
    week8_opponent = db.Column(db.String(50), nullable=True, default="")
    week9_opponent = db.Column(db.String(50), nullable=True, default="")
    week10_opponent = db.Column(db.String(50), nullable=True, default="")
    week11_opponent = db.Column(db.String(50), nullable=True, default="")
    week12_opponent = db.Column(db.String(50), nullable=True, default="")
    week13_opponent = db.Column(db.String(50), nullable=True, default="")
    week14_opponent = db.Column(db.String(50), nullable=True, default="")
    week15_opponent = db.Column(db.String(50), nullable=True, default="")


class Waiver_Info(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    league = db.Column(db.Integer, db.ForeignKey('league.id'))
    team_to_add_id = db.Column(db.Integer, nullable=False)
    team_to_drop_id = db.Column(db.Integer, nullable=False)
    faab_submitted = db.Column(db.Integer, nullable=False)
    priority = db.Column(db.Integer, nullable=False)


class Executed_Waivers_update1(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    league = db.Column(db.Integer, db.ForeignKey('league.id'))
    added_team = db.Column(db.Integer, nullable=False)
    dropped_team = db.Column(db.Integer, nullable=False)
    faab_used = db.Column(db.Integer, nullable=False)
    date_and_time_added = db.Column(db.DateTime, default=datetime.utcnow())


class HistoryOfWaivers(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    league = db.Column(db.Integer, db.ForeignKey('league.id'))
    team_to_add_id = db.Column(db.Integer, nullable=False)
    team_to_drop_id = db.Column(db.Integer, nullable=False)
    faab_submitted = db.Column(db.Integer, nullable=False)
    priority = db.Column(db.Integer, nullable=False)
    date_and_time_added = db.Column(db.DateTime, default=datetime.utcnow(), nullable=True)


class Matchup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    week = db.Column(db.Integer, default=1)
    league = db.Column(db.Integer, db.ForeignKey('league.id'))
    user_id1 = db.Column(db.Integer, db.ForeignKey('user.id'))
    user_id2 = db.Column(db.Integer, db.ForeignKey('user.id'))
    user1_score = db.Column(db.Integer, default=0)
    user2_score = db.Column(db.Integer, default=0)


class Analysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    num_of_visits = db.Column(db.Integer)
    league = db.Column(db.Integer, nullable=True)
    endpoint = db.Column(db.String(100))


class DraftRoom(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    league_id = db.Column(db.Integer, db.ForeignKey('league.id'), nullable=False, unique=True)
    status = db.Column(db.String(20), default='waiting')  # waiting, active, complete


class DraftNomination(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    draft_room_id = db.Column(db.Integer, db.ForeignKey('draft_room.id'))
    nominated_team_id = db.Column(db.Integer, db.ForeignKey(f'{Football_Teams.__tablename__}.id'))
    nominated_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    current_bid = db.Column(db.Integer, default=1)
    current_winner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    status = db.Column(db.String(20), default='active')  # active, sold, cancelled
    timer_end = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class DraftBid(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nomination_id = db.Column(db.Integer, db.ForeignKey('draft_nomination.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    amount = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class DraftParticipant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    draft_room_id = db.Column(db.Integer, db.ForeignKey('draft_room.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    budget_remaining = db.Column(db.Integer, default=1000)
    is_commissioner = db.Column(db.Boolean, default=False)
    is_connected = db.Column(db.Boolean, default=False)
    user = db.relationship('User', backref='draft_participants')


class UserForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    username = StringField("Username", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired()])
    password = SelectField("Password", coerce=str, validate_choice=False)
    password_confirm = SelectField("Confirm Password", validators=[EqualTo('password', message='Passwords must match')], coerce=str, validate_choice=False)
    # password_hash = PasswordField("Password", validators=[DataRequired(),
    #                                                       EqualTo('password_hash2', message='Passwords must match')])
    # password_hash2 = PasswordField("Confirm Password", validators=[DataRequired()])
    submit = SubmitField("Submit")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Submit")


class LeagueForm(FlaskForm):
    league_name = StringField("League Name", validators=[DataRequired()])
    league_password = StringField("League Password", validators=[DataRequired()])
    submit = SubmitField("Submit")


class JoinLeagueForm(FlaskForm):
    league_password = StringField("League Password", validators=[DataRequired()])
    submit = SubmitField("Join!")


class LeagueSetup(FlaskForm):
    user = SelectField("Player", coerce=int)
    team1 = SelectField("Team 1", coerce=int)
    team2 = SelectField("Team 2", coerce=int)
    team3 = SelectField("Team 3", coerce=int)
    team4 = SelectField("Team 4", coerce=int)
    faab = IntegerField("faab", validators=[DataRequired()])
    submit = SubmitField("Submit")


class DropComplete(FlaskForm):
    faab = IntegerField("Faab", validators=[DataRequired()])
    submit = SubmitField("Submit")


class AlreadyUpdatedDropComplete(FlaskForm):
    submit = SubmitField("Submit")


class UpdateFaab(FlaskForm):
    faab = IntegerField("Faab", validators=[DataRequired()])
    submit = SubmitField("Submit")





with app.app_context():
    db.create_all()

"""
This loop replaces all teams that have an '&' in their name to '%26' because the API won't find it if an '&' is passed
in. Teams_dict is then made to pass into the save_to_spreadsheet function. A dictionary is made so it can be saved to a
csv with a list of 0s and 1s (1s representing a win, 0s representing a loss or no game played)
"""



# new_teams = []
# with open("Teams.txt", encoding='ISO-8859-1') as file:
#     text = file.read()
#     teams = text.split(",")
#     for team in teams:
#         new_team = team.replace("&", "%26")
#         new_teams.append(new_team)
#
# teams_dict = {team: [] for team in teams}
#
# if get_upcoming_games:
#     my_functions.upcoming_games_master(teams_dict=teams_dict, year=year)
# data = pandas.read_csv("This_weeks_games.csv", encoding='latin-1')
# team_games = data.to_dict()
# final_team_games = my_functions.convert_dict_to_simple_dict(team_games)
#
# if get_data:
#     my_functions.save_data(league_number=1, new_teams=new_teams, year=year, teams_dict=teams_dict)

# Invalid URL
@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


# Server Error
@app.errorhandler(500)
def page_not_found(e):
    return render_template("500.html"), 500

@app.route("/")
def home():
    return render_template("index.html")


def redirect_dest(fallback):
    dest_url = request.args.get('next')
    print(dest_url)
    if not dest_url:
        dest_url = url_for(fallback)
    return redirect(dest_url)


@login_manager.unauthorized_handler
def handle_needs_login():
    flash("You have to be logged in to access this page.")
    next = url_for(request.endpoint,**request.view_args)
    return redirect(url_for('login', next=next))

@app.route("/login", methods=['GET', 'POST'])
def login():
    form = LoginForm()
    next_url = request.form.get("next")
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            if user.locked_account == True:
                flash("Account is locked. Please talk to Ken to have it reset")
                return render_template("login.html", form=form)
            elif check_password_hash(user.password_hash, form.password.data):
                login_user(user)
                db.session.query(User).filter(User.id == user.id).update({"failed_login_attempts": 0})
                db.session.commit()
                if next_url:
                    return redirect(next_url)
                else:
                    return redirect(url_for('UserDashboard'))
            else:
                previous_failed_login_attempts = user.failed_login_attempts
                try:
                    db.session.query(User).filter(User.id == user.id).update({"failed_login_attempts": previous_failed_login_attempts + 1})
                except TypeError:
                    db.session.query(User).filter(User.id == user.id).update({"failed_login_attempts": 1})
                if user.failed_login_attempts > 9:
                    db.session.query(User).filter(User.id == user.id).update({"locked_account": True})
                    db.session.query(User).filter(User.id == user.id).update({"failed_login_attempts": 0})
                    flash("Account is locked. Please talk to Ken to have it reset")
                else:
                    flash("That login combination is incorrect")
                db.session.commit()
                print(user.failed_login_attempts)
                return render_template("login.html", form=form)
        else:
            flash("That email isn't registered in the system")
    return render_template("login.html", form=form)


@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    flash("You have been logged out!")
    return redirect(url_for('login'))


@app.route('/user/add', methods=['GET', 'POST'])
def add_user():
    form = UserForm()
    name = None
    passwords = my_functions.get_password_list()
    passwords2 = [(str(word), word) for word in passwords]
    form.password.choices = passwords2
    form.password_confirm.choices = passwords2

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None:
            password = form.password.data
            password_match = form.password_confirm.data
            if password == password_match:
                salted_and_hashed_pw = generate_password_hash(password, method="pbkdf2:sha256", salt_length=8)
                # salted_and_hashed_pw = generate_password_hash(form.password_hash.data, method="pbkdf2:sha256",
                #                                               salt_length=8)
                user = User(name=form.name.data, email=form.email.data, password_hash=salted_and_hashed_pw,
                            username=form.username.data)
                db.session.add(user)
                db.session.commit()
            else:
                flash("Passwords don't match!")
        name = form.name.data
        form.name.data = ''
        form.email.data = ''
        form.username.data = ''
        flash("User Added Successfully!")
    else:
        flash("Not committed")
    our_users = User.query.order_by(User.date_added)
    return render_template("add_user.html", form=form, name=name, our_users=our_users, passwords=passwords)


@app.route('/update/<int:id>', methods=['GET', 'POST'])
def update(id):
    form = UserForm()
    name_to_update = User.query.get(id)
    passwords = my_functions.get_password_list()
    passwords2 = [(str(word), word) for word in passwords]
    form.password.choices = passwords2
    form.password_confirm.choices = passwords2
    if request.method == "POST" and form.password.data == form.password_confirm.data:
        name_to_update.name = request.form['name']
        name_to_update.email = request.form['email']
        name_to_update.password_hash = generate_password_hash(form.password.data, method="pbkdf2:sha256",
                                                              salt_length=8)
        name_to_update.username = request.form['username']
        try:
            db.session.commit()
            flash("User Updated Successfully!")
            return render_template("update.html", form=form, name_to_update=name_to_update, passwords=passwords)
        except:
            flash("Error!")
            return render_template("update.html", form=form, name_to_update=name_to_update, id=id, passwords=passwords)
    elif request.method == "POST" and form.password.data != form.password_confirm.data:
        flash("Passwords must match")
        return render_template("update.html", form=form, name_to_update=name_to_update, id=id, passwords=passwords)
    else:
        return render_template("update.html", form=form, name_to_update=name_to_update, id=id, passwords=passwords)


@app.route('/delete/<int:id>', methods=['GET', 'POST'])
def delete_user(id):
    user_to_delete = User.query.get(id)
    form = UserForm()
    name = None
    try:
        db.session.delete(user_to_delete)
        db.session.commit()
        flash("User deleted")
        our_users = User.query.order_by(User.date_added)
        return render_template("add_user.html", form=form, name=name, our_users=our_users)
    except:
        flash("Error!")
        return render_template("add_user.html", form=form, name=name, our_users=our_users)


@app.route("/create_league", methods=['GET', 'POST'])
@login_required
def create_league():
    # Add analysis to db if the user visiting is not me
    if current_user.id != 13:
        num_of_visits = Analysis.query.filter(Analysis.endpoint == "create_league").first().num_of_visits
        db.session.query(Analysis).filter(Analysis.endpoint == "create_league").update(
            {"num_of_visits": num_of_visits + 1})
        db.session.commit()

    # Initialize form and get leagues_list to send to website for the navbar
    form = LeagueForm()
    leagues = List_of_leagues_update1.query.filter_by(user_id=current_user.id)
    leagues_list = [(League.query.filter_by(id=item.league).first().league_name, item.league) for item in
                    leagues]
    if form.validate_on_submit():
        # Create league and make the current user the league manager
        league = League(league_name=form.league_name.data, league_manager=current_user.id,
                        league_password=form.league_password.data)
        db.session.add(league)
        db.session.commit()

        # Make the current user a member of the league
        league_member = League_members_update1(league_id=league.id, member=current_user.id)
        db.session.add(league_member)
        db.session.commit()

        # Add this league to the list of leagues for the current user
        league_to_add = List_of_leagues_update1(user_id=current_user.id, league=league.id)
        db.session.add(league_to_add)
        db.session.commit()

        # Setup player's weekly info table (assign 4 teams as none, give faab of $100)
        initial_player_setup = Player_weekly_info(user_id=current_user.id, league=league.id)
        db.session.add(initial_player_setup)
        db.session.commit()

        # Setup analysis table
        # join_league_analysis = Analysis(num_of_visits=0, endpoint="join_league")
        # create_league_analysis = Analysis(num_of_visits=0, endpoint="create_league")
        # userdashboard_analysis = Analysis(num_of_visits=0, endpoint="userdashboard")
        league_dashboard_analysis = Analysis(num_of_visits=0, endpoint="league_dashboard", league=league.id)
        add_team_analysis = Analysis(num_of_visits=0, endpoint="add_team", league=league.id)
        update_faab_analysis = Analysis(num_of_visits=0, endpoint="update_faab", league=league.id)
        db.session.add(league_dashboard_analysis)
        db.session.add(add_team_analysis)
        db.session.add(update_faab_analysis)
        db.session.commit()

        return redirect(url_for('league_dashboard', league_id=league.id, leagues_list=leagues_list))

    form.league_name.data = ''
    all_leagues = League.query.order_by(League.date_created)
    league_members = League_members_update1.query.order_by(League_members_update1.league_id)
    return render_template("create_league.html", form=form, all_leagues=all_leagues, league_members=league_members, leagues_list=leagues_list)


@app.route("/delete_league/<int:id>", methods=['GET', 'POST'])
def delete_league(id):
    league_to_delete = League.query.get(id)
    form = LeagueForm()
    leagues = List_of_leagues_update1.query.filter_by(user_id=current_user.id)
    leagues_list = [(League.query.filter_by(id=item.league).first().league_name, item.league) for item in
                    leagues]
    try:
        db.session.delete(league_to_delete)
        db.session.commit()
        flash("League deleted")
        all_leagues = League.query.order_by(League.date_created)
        league_members = League_members_update1.query.order_by(League_members_update1.league_id)
        return render_template("create_league.html", form=form, all_leagues=all_leagues, league_members=league_members, leagues_list=leagues_list)
    except:
        db.session.rollback()
        flash("Error!")
        all_leagues = League.query.order_by(League.date_created)
        league_members = League_members_update1.query.order_by(League_members_update1.league_id)
        return render_template("create_league.html", form=form, all_leagues=all_leagues, league_members=league_members, leagues_list=leagues_list)


@app.route("/join_league/league_id=<int:league_id>", methods=['GET', 'POST'])
@login_manager.unauthorized_handler
def join_league(league_id):
    # Add analysis to db if the user is not me
    num_of_visits = Analysis.query.filter(Analysis.endpoint == "join_league").first().num_of_visits
    db.session.query(Analysis).filter(Analysis.endpoint == "join_league").update(
        {"num_of_visits": num_of_visits + 1})
    db.session.commit()

    try:
        form = JoinLeagueForm()
        leagues = List_of_leagues_update1.query.filter_by(user_id=current_user.id)
        leagues_list = [(League.query.filter_by(id=item.league).first().league_name, item.league) for item in
                        leagues]
        if form.validate_on_submit():
            league_password = League.query.get(league_id).league_password

            if form.league_password.data == league_password:
                league_members = League_members_update1.query.order_by(League_members_update1.league_id)
                league_member_ids = []
                for member in league_members:
                    if member.league_id == league_id:
                        name = User.query.filter_by(id=member.member).first().id
                        league_member_ids.append(name)

                if current_user.id not in league_member_ids:
                    # Make the current user a member of the league
                    league_member = League_members_update1(league_id=league_id, member=current_user.id)
                    db.session.add(league_member)
                    db.session.commit()

                    # Add this league to the list of leagues for the current user
                    league_to_add = List_of_leagues_update1(user_id=current_user.id, league=league_id)
                    db.session.add(league_to_add)
                    db.session.commit()

                    # Setup player's weekly info table (assign 4 teams as none, give faab of $100)
                    initial_player_setup = Player_weekly_info(user_id=current_user.id, league=league_id)
                    db.session.add(initial_player_setup)
                    db.session.commit()

                    flash("You have been added to the league!")
                else:
                    flash("You're already in the league! You will be redirected to the league page")
                    time.sleep(3)
                    return redirect(url_for('league_dashboard', league_id=league_id, leagues_list=leagues_list))

                return redirect(url_for('league_dashboard', league_id=league_id, leagues_list=leagues_list))
            else:
                flash("That password is not correct. Please try again")
                form.league_password.data = ''
                return render_template("join_league.html", form=form, leagues_list=leagues_list)

        form.league_password.data = ''
        return render_template("join_league.html", form=form, leagues_list=leagues_list)
    except AttributeError:
        return redirect(url_for('login', next=request.endpoint, league_id=league_id))


@app.route("/league_dashboard/league=<int:league_id>", methods=['GET', 'POST'])
@login_required
def league_dashboard(league_id):
    # Add analysis to db if the user is not me
    if current_user.id != 13:
        num_of_visits = Analysis.query.filter(Analysis.endpoint == "league_dashboard", Analysis.league == league_id).first().num_of_visits
        db.session.query(Analysis).filter(Analysis.endpoint == "league_dashboard", Analysis.league == league_id).update(
            {"num_of_visits": num_of_visits + 1})
        db.session.commit()

    # Get many different queries for use later in the league_dashboard script
    league_members = League_members_update1.query.order_by(League_members_update1.league_id)
    league_member_names = [User.query.filter_by(id=member.member).first().name for member in league_members
                           if member.league_id == league_id]
    league_manager = League.query.filter_by(id=league_id).first().league_manager

    user_waivers = Waiver_Info.query.filter_by(user_id=current_user.id, league=league_id).all()
    user_waivers_list = [(Football_Teams.query.filter_by(id=waiver.team_to_add_id).first().team,
                          Football_Teams.query.filter_by(id=waiver.team_to_drop_id).first().team,
                          waiver.faab_submitted, waiver.id) for waiver in user_waivers]
    faab = Player_weekly_info.query.filter_by(user_id=current_user.id, league=league_id).first().faab
    sorted_user_waivers_list = sorted(user_waivers_list, key=lambda waiver: waiver[2], reverse=True)

    league_members_weekly_info = Player_weekly_info.query.filter_by(league=league_id).all()

    # Returns all info for the Standings tab as a list of unions
    # Attribute error means that no one has any teams, which will lead to errors in the html file
    league_scores_with_names_list = []
    for member in league_members_weekly_info:
        try:
            league_scores_with_names_list.append((User.query.filter_by(id=member.user_id).first().name, member.this_weeks_score,
                                    member.previous_weeks_score, Football_Teams.query.filter_by(id=member.team_1).first().team,
                                    Football_Teams.query.filter_by(id=member.team_2).first().team,
                                    Football_Teams.query.filter_by(id=member.team_3).first().team,
                                    Football_Teams.query.filter_by(id=member.team_4).first().team,
                                    Player_weekly_info.query.filter_by(user_id=member.user_id).filter_by(league=league_id).first().faab,
                                    Player_weekly_info.query.filter_by(user_id=member.user_id).filter_by(league=league_id).first().total_wins))
        except AttributeError:
            pass

    # League_scores_with_names_initial is to sort the members based upon wins first, then total score to try to show the tiebreaker as total wins
    league_scores_with_names_initial = sorted(league_scores_with_names_list, key=lambda kv: kv[8], reverse=True)
    league_scores_with_names = sorted(league_scores_with_names_initial, key=lambda kv: kv[1], reverse=True)
    print(f'league_scores_with_names: {league_scores_with_names}')
    # except AttributeError:
    #     league_scores_with_names = []

    league_member_ids = [User.query.filter_by(id=member.member).first().id for member in league_members
                           if member.league_id == league_id]
    week, postseason = my_functions.determine_week_number()

    # Gets all teams that the user can't pickup due to being owned by the user or another user
    ineligible_teams = []
    for member in league_member_ids:
        try:
            ineligible_teams.append(Football_Teams.query.filter_by(
                id=int(Player_weekly_info.query.filter_by(league=league_id, user_id=member).first().team_1)).first().team)
            ineligible_teams.append(Football_Teams.query.filter_by(
                id=int(Player_weekly_info.query.filter_by(league=league_id, user_id=member).first().team_2)).first().team)
            ineligible_teams.append(Football_Teams.query.filter_by(
                id=int(Player_weekly_info.query.filter_by(league=league_id, user_id=member).first().team_3)).first().team)
            ineligible_teams.append(Football_Teams.query.filter_by(
                id=int(Player_weekly_info.query.filter_by(league=league_id, user_id=member).first().team_4)).first().team)
        except TypeError:
            pass
    print(f'ineligible teams: {ineligible_teams}')

    # Gets all the user's teams to get the dict that will be passed in for the standings table
    try:
        user_teams = [Football_Teams.query.filter_by(id=int(
            Player_weekly_info.query.filter_by(league=league_id, user_id=current_user.id).first().team_1)).first().team,
                      Football_Teams.query.filter_by(id=int(
                          Player_weekly_info.query.filter_by(league=league_id,
                                                             user_id=current_user.id).first().team_2)).first().team,
                      Football_Teams.query.filter_by(id=int(
                          Player_weekly_info.query.filter_by(league=league_id,
                                                             user_id=current_user.id).first().team_3)).first().team,
                      Football_Teams.query.filter_by(id=int(
                          Player_weekly_info.query.filter_by(league=league_id,
                                                             user_id=current_user.id).first().team_4)).first().team]
    except TypeError:
        user_teams = []

    # Pass in dict where team is the key and values are a list made for the standings table (points, conference, next opponent, previous opponent)
    time_correction_delta = timedelta(hours=6)
    all_teams = Football_Teams.query.order_by(Football_Teams.id)
    eligible_teams_dict = {}
    user_teams_dict = {}
    for team in all_teams:
        print(team.team)
        print(f'{team.ap_ranking} {team.team}')
        try:
            upcoming_opponent_ranking = team.opponent_ap_ranking
            print(f'upcoming opponent info: {upcoming_opponent_ranking}, {team.upcoming_opponent}')
            if upcoming_opponent_ranking is None:
                upcoming_opponent_ranking = ""
        except AttributeError:
            # AttributeError most likely will be due to NoneType being the query result, so return "" which is the default
            upcoming_opponent_ranking = ""
        if team.team not in ineligible_teams:
            if team.date_and_time_of_game is not None:
                eligible_teams_dict[team.team] = [team.current_score, team.conference, team.upcoming_opponent, team.previous_opponent,
                                       team.previous_result, datetime.strftime(team.date_and_time_of_game - time_correction_delta, "%a %I:%M%p"),
                                                  team.chance_to_win, upcoming_opponent_ranking, team.ap_ranking]
            else:
                eligible_teams_dict[team.team] = [team.current_score, team.conference, team.upcoming_opponent, team.previous_opponent,
                                                  team.previous_result, "no game", team.chance_to_win, upcoming_opponent_ranking, team.ap_ranking]
        if team.team in user_teams:
            if team.date_and_time_of_game is not None:
                user_teams_dict[team.team] = [team.current_score, team.conference, team.upcoming_opponent, team.previous_opponent,
                               team.previous_result, datetime.strftime(team.date_and_time_of_game - time_correction_delta, "%a %I:%M%p"),
                                              team.chance_to_win, upcoming_opponent_ranking, team.ap_ranking]
            else:
                user_teams_dict[team.team] = [team.current_score, team.conference, team.upcoming_opponent, team.previous_opponent,
                                              team.previous_result, "no game", team.chance_to_win, upcoming_opponent_ranking, team.ap_ranking]
    # eligible_teams_dict = {team.team: [team.current_score, team.conference, team.upcoming_opponent, team.previous_opponent,
    #                                    team.previous_result, datetime.strftime(team.date_and_time_of_game - time_correction_delta, "%a %I:%M%p")] for team in all_teams if team.team not in ineligible_teams}
    # user_teams_dict = {team.team: [team.current_score, team.conference, team.upcoming_opponent, team.previous_opponent,
    #                                team.previous_result, datetime.strftime(team.date_and_time_of_game - time_correction_delta, "%a %I:%M%p")] for team in all_teams if team.team in user_teams}
    try:
        eligible_teams_dict_sorted = dict(sorted(eligible_teams_dict.items(), key=lambda kv: kv[1], reverse=True))
        user_teams_dict_sorted = dict(sorted(user_teams_dict.items(), key=lambda kv: kv[1], reverse=True))
    except TypeError:
        eligible_teams_dict_sorted = eligible_teams_dict
        user_teams_dict_sorted = user_teams_dict
    eligible_teams = list(eligible_teams_dict_sorted)

    # For the navbar, passes in all the leagues so user can click on a league to go to the league dashboard
    current_user_teams = list(user_teams_dict_sorted.keys())
    leagues = List_of_leagues_update1.query.filter_by(user_id=current_user.id)
    leagues_list = [(League.query.filter_by(id=item.league).first().league_name, item.league) for item in
                    leagues]

    # Sends all waivers that have succeeded in the league so user can see all the successful waivers
    all_executed_waivers = Executed_Waivers_update1.query.filter_by(league=league_id).all()
    executed_waivers = [(User.query.filter_by(id=waiver.user_id).first().name, Football_Teams.query.filter_by(id=waiver.added_team).first().team, Football_Teams.query.filter_by(id=waiver.dropped_team).first().team,
                         waiver.faab_used, waiver.date_and_time_added) for waiver in all_executed_waivers]

    # Sends all of the user's waiver history so they can see what waivers of theirs have been processed
    your_waiver_history = HistoryOfWaivers.query.filter(HistoryOfWaivers.user_id == current_user.id, HistoryOfWaivers.league == league_id).all()
    your_waiver_history_list = [(waiver.id, Football_Teams.query.filter_by(id=waiver.team_to_add_id).first().team, Football_Teams.query.filter_by(id=waiver.team_to_drop_id).first().team, waiver.faab_submitted, waiver.date_and_time_added) for waiver in your_waiver_history]

    # Determines if it's time for playoffs. If it is, allow the top people to preference which playoff representative they want
    if postseason:
        playoff_teams = []
    else:
        playoff_teams = []


    return render_template("league_dashboard.html", league_members=league_members, league_id=league_id,
                           league_member_names=league_member_names, league_manager=league_manager,
                           eligible_teams=eligible_teams, current_user_teams=current_user_teams,
                           eligible_teams_dict_sorted=eligible_teams_dict_sorted, user_teams_dict_sorted=user_teams_dict_sorted,
                           user_waivers_list=sorted_user_waivers_list, faab=faab, league_scores_with_names=league_scores_with_names,
                           leagues_list=leagues_list, executed_waivers=executed_waivers, your_waiver_history=your_waiver_history_list,
                           postseason=postseason, playoff_teams=playoff_teams)


# @app.route("/team_schedule/team_id=<int:team_id>", methods=['GET', 'POST'])
# @login_required
# def league_dashboard(team_id):
#
#     return render_template("team_schedule.html")

@app.route("/add_team/league=<int:league_id>", methods=['GET', 'POST'])
@login_required
def add_team(league_id):
    # Add analysis to db if the user is not me
    if current_user.id != 13:
        num_of_visits = Analysis.query.filter(Analysis.endpoint == "add_team",
                                              Analysis.league == league_id).first().num_of_visits
        db.session.query(Analysis).filter(Analysis.endpoint == "add_team", Analysis.league == league_id).update(
            {"num_of_visits": num_of_visits + 1})
        db.session.commit()

    league_members = League_members_update1.query.order_by(League_members_update1.league_id)
    league_member_ids = [User.query.filter_by(id=member.member).first().id for member in league_members
                         if member.league_id == league_id]
    # Gets all teams that the user can't pickup due to being owned by the user or another user
    ineligible_teams = []
    for member in league_member_ids:
        try:
            ineligible_teams.append(Football_Teams.query.filter_by(
                id=int(Player_weekly_info.query.filter_by(league=league_id, user_id=member).first().team_1)).first().team)
            ineligible_teams.append(Football_Teams.query.filter_by(
                id=int(Player_weekly_info.query.filter_by(league=league_id, user_id=member).first().team_2)).first().team)
            ineligible_teams.append(Football_Teams.query.filter_by(
                id=int(Player_weekly_info.query.filter_by(league=league_id, user_id=member).first().team_3)).first().team)
            ineligible_teams.append(Football_Teams.query.filter_by(
                    id=int(Player_weekly_info.query.filter_by(league=league_id, user_id=member).first().team_4)).first().team)
        except TypeError:
            # Occurs when person who made the league isn't in the league
            pass
    print(ineligible_teams)

    # Displays the user's current teams that they can choose to drop from
    try:
        user_teams = [Football_Teams.query.filter_by(id=int(
            Player_weekly_info.query.filter_by(league=league_id, user_id=current_user.id).first().team_1)).first().team,
                      Football_Teams.query.filter_by(id=int(
                          Player_weekly_info.query.filter_by(league=league_id,
                                                             user_id=current_user.id).first().team_2)).first().team,
                      Football_Teams.query.filter_by(id=int(
                          Player_weekly_info.query.filter_by(league=league_id,
                                                             user_id=current_user.id).first().team_3)).first().team,
                      Football_Teams.query.filter_by(id=int(
                          Player_weekly_info.query.filter_by(league=league_id,
                                                             user_id=current_user.id).first().team_4)).first().team]
    except TypeError:
        user_teams = []

    all_teams = Football_Teams.query.order_by(Football_Teams.id)
    eligible_teams_dict = {team.team: [team.current_score, team.conference, team.id, team.date_and_time_of_game] for team in all_teams if
                           team.team not in ineligible_teams if team.team != "Washington State" and team.team != "Oregon State"}
    user_teams_dict = {team.team: [team.current_score, team.conference] for team in all_teams if
                       team.team in user_teams}
    try:
        eligible_teams_dict_sorted = dict(sorted(eligible_teams_dict.items(), key=lambda kv: kv[1], reverse=True))
        user_teams_dict_sorted = dict(sorted(user_teams_dict.items(), key=lambda kv: kv[1], reverse=True))
    except TypeError:
        eligible_teams_dict_sorted = eligible_teams_dict
        user_teams_dict_sorted = user_teams_dict

    eligible_teams = list(eligible_teams_dict_sorted)
    current_user_teams = list(user_teams_dict_sorted.keys())
    league_name = League.query.filter_by(id=league_id).first().league_name
    already_updated = League.query.filter_by(id=league_id).first().waivers_already_executed
    print(f'already updated: {already_updated}')

    leagues = List_of_leagues_update1.query.filter_by(user_id=current_user.id)
    leagues_list = [(League.query.filter_by(id=item.league).first().league_name, item.league) for item in
                    leagues]
    now = datetime.now()

    return render_template("add_team.html", league_members=league_members, league_id=league_id,
                           eligible_teams=eligible_teams, current_user_teams=current_user_teams,
                           eligible_teams_dict_sorted=eligible_teams_dict_sorted,
                           user_teams_dict_sorted=user_teams_dict_sorted, league_name=league_name, leagues_list=leagues_list,
                           already_updated=already_updated, now=now)

@app.route("/drop_team/league=<int:league_id>/team_selected=<int:team_id>", methods=['GET', 'POST'])
@login_required
def drop_team(league_id, team_id):
    league_members = League_members_update1.query.order_by(League_members_update1.league_id)
    team_to_add = Football_Teams.query.filter_by(id=int(team_id)).first()
    team_to_add_list = [team_to_add.team, team_to_add.current_score, team_to_add.conference, team_to_add.id]
    print(team_to_add_list)
    # Gets all teams that the user can't pickup due to being owned by the user or another user

    user_teams = [Football_Teams.query.filter_by(id=int(
        Player_weekly_info.query.filter_by(league=league_id, user_id=current_user.id).first().team_1)).first().team,
                  Football_Teams.query.filter_by(id=int(
                      Player_weekly_info.query.filter_by(league=league_id,
                                                         user_id=current_user.id).first().team_2)).first().team,
                  Football_Teams.query.filter_by(id=int(
                      Player_weekly_info.query.filter_by(league=league_id,
                                                         user_id=current_user.id).first().team_3)).first().team,
                  Football_Teams.query.filter_by(id=int(
                      Player_weekly_info.query.filter_by(league=league_id,
                                                         user_id=current_user.id).first().team_4)).first().team]

    all_teams = Football_Teams.query.order_by(Football_Teams.id)
    user_teams_dict = {team.team: [team.current_score, team.conference, team.id, team.date_and_time_of_game] for team in all_teams if team.team in user_teams}
    try:
        user_teams_dict_sorted = dict(sorted(user_teams_dict.items(), key=lambda kv: kv[1], reverse=True))
    except TypeError:
        user_teams_dict_sorted = user_teams_dict

    current_user_teams = list(user_teams_dict_sorted.keys())
    league_name = League.query.filter_by(id=league_id).first().league_name

    leagues = List_of_leagues_update1.query.filter_by(user_id=current_user.id)
    leagues_list = [(League.query.filter_by(id=item.league).first().league_name, item.league) for item in
                    leagues]
    already_updated = League.query.filter_by(id=league_id).first().waivers_already_executed
    now = datetime.now()
    print(now)
    print(user_teams_dict_sorted)
    for team in user_teams_dict_sorted:
        print(user_teams_dict_sorted[team][3])

    return render_template("drop_team.html", league_members=league_members, league_id=league_id,
                           current_user_teams=current_user_teams, user_teams_dict_sorted=user_teams_dict_sorted,
                           league_name=league_name, team_to_add_list=team_to_add_list, leagues_list=leagues_list,
                           already_updated=already_updated, now=now)


@app.route("/confirm_drop/league=<int:league_id>/drop_team=<int:dropteam_id>/add_team=<int:addteam_id>", methods=['GET', 'POST'])
@login_required
def confirm_drop(league_id, dropteam_id, addteam_id):
    team_to_add = Football_Teams.query.filter_by(id=int(addteam_id)).first()
    team_to_drop = Football_Teams.query.filter_by(id=int(dropteam_id)).first()
    already_updated = League.query.filter_by(id=league_id).first().waivers_already_executed
    now = datetime.utcnow()
    print(already_updated)
    print(team_to_add.date_and_time_of_game)
    print(team_to_drop.date_and_time_of_game)
    print(datetime.utcnow() - datetime.timedelta(hours=6))
    if already_updated and team_to_add.date_and_time_of_game > now and team_to_drop.date_and_time_of_game > now:
        print('not waivers')
        form = AlreadyUpdatedDropComplete()
        waiver_notification = False
    else:
        print('waivers')
        form = DropComplete()
        waiver_notification = True
    user_faab = Player_weekly_info.query.filter_by(user_id=current_user.id, league=league_id).first().faab
    team_to_add = Football_Teams.query.filter_by(id=int(addteam_id)).first()
    team_to_drop = Football_Teams.query.filter_by(id=int(dropteam_id)).first()
    team_to_add_list = [team_to_add.team, team_to_add.current_score, team_to_add.conference, team_to_add.id]
    team_to_drop_list = [team_to_drop.team, team_to_drop.current_score, team_to_add.conference, team_to_drop.id]
    league_name = League.query.filter_by(id=league_id).first().league_name
    leagues = List_of_leagues_update1.query.filter_by(user_id=current_user.id)
    leagues_list = [(League.query.filter_by(id=item.league).first().league_name, item.league) for item in
                    leagues]

    if form.validate_on_submit():
        team_to_add = Football_Teams.query.filter_by(id=int(addteam_id)).first().id
        team_to_drop = Football_Teams.query.filter_by(id=int(dropteam_id)).first().id

        if waiver_notification == True:
            submitted_faab = form.faab.data

            if submitted_faab <= -1:
                flash(f"You must submit faab that is $0 or more...")
                return render_template("confirm_drop.html", form=form, league_id=league_id, league_name=league_name,
                                       team_to_add_list=team_to_add_list, team_to_drop_list=team_to_drop_list,
                                       available_faab=user_faab, leagues_list=leagues_list, already_updated=already_updated)

            if submitted_faab <= user_faab:
                all_waivers = Waiver_Info.query.filter_by(user_id=current_user.id, league=league_id).all()
                number_of_waivers = len(all_waivers)
                if number_of_waivers == 0:
                    waiver_info = Waiver_Info(user_id=current_user.id, league=league_id, team_to_add_id=team_to_add,
                                              team_to_drop_id=team_to_drop, faab_submitted=submitted_faab,
                                              priority=number_of_waivers + 1)
                    db.session.add(waiver_info)
                    db.session.commit()
                    return redirect(url_for('league_dashboard', league_id=league_id, leagues_list=leagues_list))

                for waiver in all_waivers:
                    if waiver.team_to_add_id == team_to_add and waiver.team_to_drop_id == team_to_drop:
                        flash(f"You already have a bid to drop {team_to_drop} and add {team_to_add}. Update the waiver instead")
                        return render_template("confirm_drop.html", form=form, league_id=league_id, league_name=league_name,
                                               team_to_add_list=team_to_add_list, team_to_drop_list=team_to_drop_list,
                                               available_faab=user_faab, leagues_list=leagues_list, already_updated=already_updated)

                    if all_waivers.index(waiver) == number_of_waivers - 1:
                        waiver_info = Waiver_Info(user_id=current_user.id, league=league_id, team_to_add_id=team_to_add,
                                             team_to_drop_id=team_to_drop, faab_submitted=submitted_faab, priority=number_of_waivers + 1)
                        db.session.add(waiver_info)
                        db.session.commit()
                        return redirect(url_for('league_dashboard', league_id=league_id, leagues_list=leagues_list))

        else:
            winner_teams = db.session.query(Player_weekly_info).filter(Player_weekly_info.user_id == current_user.id,
                                                                    Player_weekly_info.league == league_id).first()
            winner_teams_dict = {int(winner_teams.team_1): "team_1", int(winner_teams.team_2): "team_2",
                                 int(winner_teams.team_3): "team_3", int(winner_teams.team_4): "team_4"}

            db.session.query(Player_weekly_info).filter(Player_weekly_info.user_id == current_user.id,
                                                     Player_weekly_info.league == league_id).update(
                {str(winner_teams_dict[dropteam_id]): addteam_id})
            executed_waiver = Executed_Waivers_update1(user_id=current_user.id, league=league_id, added_team=team_to_add,
                                                       dropped_team=team_to_drop, faab_used=0, date_and_time_added=datetime.now())
            db.session.add(executed_waiver)
            db.session.commit()
            return redirect(url_for('league_dashboard', league_id=league_id, leagues_list=leagues_list))

    elif already_updated:
        return render_template("confirm_drop.html", form=form, league_id=league_id, league_name=league_name,
                               team_to_add_list=team_to_add_list, team_to_drop_list=team_to_drop_list,
                               available_faab=user_faab, leagues_list=leagues_list, already_updated=already_updated,
                               waiver_notification=waiver_notification)

    else:
        flash("You don't have enough Faab to make that waiver request. Please update the faab!")
        return render_template("confirm_drop.html", form=form, league_id=league_id, league_name=league_name,
                               team_to_add_list=team_to_add_list, team_to_drop_list=team_to_drop_list,
                               available_faab=user_faab, leagues_list=leagues_list, already_updated=already_updated,
                               waiver_notification=waiver_notification)

    return render_template("confirm_drop.html", form=form, league_id=league_id, league_name=league_name,
                           team_to_add_list=team_to_add_list, team_to_drop_list=team_to_drop_list,
                           available_faab=user_faab, leagues_list=leagues_list, already_updated=already_updated,
                           waiver_notification=waiver_notification)


@app.route("/confirm_delete_waiver/waiver=<int:id>/league=<int:league_id>", methods=['GET', 'POST'])
def confirm_delete_waiver(id, league_id):
    waiver_to_delete = Waiver_Info.query.get(id)
    team_to_add = Football_Teams.query.filter_by(id=waiver_to_delete.team_to_add_id).first().team
    team_to_drop = Football_Teams.query.filter_by(id=waiver_to_delete.team_to_drop_id).first().team
    faab = waiver_to_delete.faab_submitted
    leagues = List_of_leagues_update1.query.filter_by(user_id=current_user.id)
    leagues_list = [(League.query.filter_by(id=item.league).first().league_name, item.league) for item in
                    leagues]
    return render_template("confirm_delete_waiver.html", team_to_add=team_to_add, team_to_drop=team_to_drop,
                           league_id=league_id, faab=faab, waiver_id=id, leagues_list=leagues_list)

@app.route("/delete_waiver/waiver=<int:id>/league=<int:league_id>", methods=['GET', 'POST'])
def delete_waiver(id, league_id):
    waiver_to_delete = Waiver_Info.query.get(id)
    leagues = List_of_leagues_update1.query.filter_by(user_id=current_user.id)
    leagues_list = [(League.query.filter_by(id=item.league).first().league_name, item.league) for item in
                    leagues]
    try:
        db.session.delete(waiver_to_delete)
        db.session.commit()
        flash("Waiver deleted")
        return redirect(url_for('league_dashboard', league_id=league_id, leagues_list=leagues_list))
    except:
        db.session.rollback()
        flash("Error!")
        return redirect(url_for('league_dashboard', league_id=league_id, leagues_list=leagues_list))


@app.route("/update_faab/waiver=<int:id>/league=<int:league_id>", methods=['GET', 'POST'])
def update_faab(id, league_id):
    # Add analysis to db if the user is not me
    if current_user.id != 13:
        num_of_visits = Analysis.query.filter(Analysis.endpoint == "update_faab",
                                              Analysis.league == league_id).first().num_of_visits
        db.session.query(Analysis).filter(Analysis.endpoint == "update_faab", Analysis.league == league_id).update(
            {"num_of_visits": num_of_visits + 1})
        db.session.commit()

    form = UpdateFaab()
    current_waiver = Waiver_Info.query.get(id)
    faab = current_waiver.faab_submitted
    team_to_add = Football_Teams.query.filter_by(id=current_waiver.team_to_add_id).first().team
    team_to_drop = Football_Teams.query.filter_by(id=current_waiver.team_to_drop_id).first().team
    leagues = List_of_leagues_update1.query.filter_by(user_id=current_user.id)
    leagues_list = [(League.query.filter_by(id=item.league).first().league_name, item.league) for item in
                    leagues]
    if form.validate_on_submit():
        try:
            updated_faab = form.faab.data
            db.session.query(Waiver_Info).filter(Waiver_Info.id == id).update({"faab_submitted": updated_faab})
            db.session.commit()
            flash("Faab updated")
            return redirect(url_for('league_dashboard', league_id=league_id, leagues_list=leagues_list))
        except:
            db.session.rollback()
            flash("Error!")
            return redirect(url_for('league_dashboard', league_id=league_id, leagues_list=leagues_list))

    return render_template("update_faab.html", league_id=league_id, team_to_add=team_to_add, team_to_drop=team_to_drop,
                           form=form, faab=faab, leagues_list=leagues_list)


@app.route("/league_setup/league=<int:league_id>", methods=['GET', 'POST'])
@login_required
def league_setup(league_id):
    form = LeagueSetup()
    league_manager = League.query.filter_by(id=league_id).first().league_manager
    league_name = League.query.filter_by(id=league_id).first().league_name
    leagues = List_of_leagues_update1.query.filter_by(user_id=current_user.id)
    leagues_list = [(League.query.filter_by(id=item.league).first().league_name, item.league) for item in
                    leagues]

    if current_user.id == league_manager:

        # Setup all_teams to pass into the form
        all_teams = Football_Teams.query.order_by(Football_Teams.id)
        eligible_teams = [(team.id, team.team) for team in all_teams]
        print(eligible_teams)

        # Figure out which members still need to be updated and pass in Player option to the form
        league_members = League_members_update1.query.order_by(League_members_update1.league_id)
        league_member_names = [User.query.filter_by(id=member.member).first().name for member in league_members
                               if member.league_id == league_id]
        users_to_update_as_objects = Player_weekly_info.query.filter_by(league=league_id)
        users_to_update = [(user.user_id, User.query.filter_by(id=user.user_id).first().name)
                           for user in users_to_update_as_objects if user.team_1 is None]

        # Get updated members and pass their teams (and faab) in as dicts so user can see who has what teams
        updated_user_ids = [user.user_id for user in users_to_update_as_objects if user.team_1 is not None]
        for user in updated_user_ids:
            team1 = Football_Teams.query.filter_by(id=int(Player_weekly_info.query.filter_by(league=league_id, user_id=user).first().team_1)).first().team
            team2 = Football_Teams.query.filter_by(id=int(Player_weekly_info.query.filter_by(league=league_id, user_id=user).first().team_2)).first().team
            team3 = Football_Teams.query.filter_by(id=int(Player_weekly_info.query.filter_by(league=league_id, user_id=user).first().team_3)).first().team
            team4 = Football_Teams.query.filter_by(id=int(Player_weekly_info.query.filter_by(league=league_id, user_id=user).first().team_4)).first().team
            faab = Player_weekly_info.query.filter_by(league=league_id, user_id=user).first().faab
            updated_users_with_teams[User.query.filter_by(id=user).first().name] = [[team1, team2, team3, team4], faab]

        # Choices will be all teams
        form.user.choices = [(object.user_id, User.query.filter_by(id=object.user_id).first().name)
                             for object in users_to_update_as_objects]
        form.team1.choices = eligible_teams
        form.team2.choices = eligible_teams
        form.team3.choices = eligible_teams
        form.team4.choices = eligible_teams

        # Update Player_weekly_info table to go from the user having 'None' teams and 100 faab to 4 teams and user-entered faab
        if form.validate_on_submit():
            player_user_id = form.user.data
            faab = form.faab.data
            player_name = User.query.filter_by(id=player_user_id).first().name

            db.session.query(Player_weekly_info).filter(Player_weekly_info.user_id == player_user_id,
                                                        Player_weekly_info.league == league_id).update(
                {"faab": faab, "team_1": form.team1.data, "team_2": form.team2.data, "team_3": form.team3.data,
                 "team_4": form.team4.data})
            db.session.commit()
            flash(f"Teams for {player_name} have been updated!")

            # Get updated members and pass their teams (and faab) in as dicts so user can see who has what teams
            updated_user_ids = [user.user_id for user in users_to_update_as_objects if user.team_1 is not None]
            for user in updated_user_ids:
                team1 = Football_Teams.query.filter_by(id=int(
                    Player_weekly_info.query.filter_by(league=league_id, user_id=user).first().team_1)).first().team
                team2 = Football_Teams.query.filter_by(id=int(
                    Player_weekly_info.query.filter_by(league=league_id, user_id=user).first().team_2)).first().team
                team3 = Football_Teams.query.filter_by(id=int(
                    Player_weekly_info.query.filter_by(league=league_id, user_id=user).first().team_3)).first().team
                team4 = Football_Teams.query.filter_by(id=int(
                    Player_weekly_info.query.filter_by(league=league_id, user_id=user).first().team_4)).first().team
                faab = Player_weekly_info.query.filter_by(league=league_id, user_id=user).first().faab
                updated_users_with_teams[User.query.filter_by(id=user).first().name] = [[team1, team2, team3, team4],
                                                                                        faab]

        matchups_generated = League.query.filter_by(id=league_id).first().matchups_already_generated
        print(f'matchups_generated: {matchups_generated}')

    else:
        flash("You must be the league manager to perform this operation!")
        return redirect(url_for('league_dashboard', league_id=league_id, leagues_list=leagues_list))

    return render_template("league_setup.html", league_members=league_members, league_id=league_id,
                           league_member_names=league_member_names, league_manager=league_manager,
                           users_to_update=users_to_update, league_name=league_name, form=form,
                           eligible_teams=eligible_teams, updated_users_with_teams=updated_users_with_teams,
                           leagues_list=leagues_list, matchups_generated=matchups_generated)


@app.route("/schedule_draft/league=<int:league_id>", methods=['GET', 'POST'])
@login_required
def schedule_draft(league_id):
    # nothing below this line has been updated
    league_members = League_members_update1.query.order_by(League_members_update1.league_id)
    league_member_names = [User.query.filter_by(id=member.member).first().name for member in league_members
                           if member.league_id == league_id]
    if not League.query.filter_by(id=league_id).first().draft_complete:
        league_manager = League.query.filter_by(id=league_id).first().league_manager

    leagues = List_of_leagues_update1.query.filter_by(user_id=current_user.id)
    leagues_list = [(League.query.filter_by(id=item.league).first().league_name, item.league) for item in
                    leagues]
    return render_template("league_dashboard.html", league_members=league_members, league_id=league_id,
                           league_member_names=league_member_names, league_manager=league_manager, leagues_list=leagues_list)


@app.route("/generate_matchups/league=<int:league_id>", methods=['GET', 'POST'])
@login_required
def generate_matchups(league_id):
    # This function generates all the matchups for the league
    league_members = League_members_update1.query.order_by(League_members_update1.league_id)
    league_member_ids = [member.member for member in league_members]

    def round_robin_schedule(num_people):
        if num_people % 2 != 0:
            raise ValueError("Number of participants must be even.")

        participants = sorted(league_member_ids, key=lambda x: random.random())
        schedule = []

        for round in range(num_people - 1):
            round_matchups = []
            for i in range(num_people // 2):
                p1 = participants[i]
                p2 = participants[num_people - 1 - i]
                round_matchups.append((p1, p2))
            schedule.append(round_matchups)
            participants.insert(1, participants.pop())  # Rotate participants except the first one

        return schedule

    def extend_schedule(schedule, num_weeks):
        extended_schedule = []
        rounds_needed = (num_weeks + len(schedule) - 1) // len(schedule)
        for i in range(rounds_needed):
            for week in schedule:
                if len(extended_schedule) < num_weeks:
                    extended_schedule.append(week)
        return extended_schedule

    def print_schedule(schedule):
        for week_num, week in enumerate(schedule, 1):
            print(f"Week {week_num}:")
            for match in week:
                print(f"  Player {match[0]} vs Player {match[1]}")
            print()

    def commit_schedule(schedule, league_id):
        for week_num, week in enumerate(schedule, 1):
            for match in week:
                matchup = Matchup(week=week_num, league=league_id, user_id1=match[0], user_id2=match[1], user1_score=0,
                                  user2_score=0)
                db.session.add(matchup)
                db.session.commit()
        db.session.query(League).filter(League.id == league_id).update({"matchups_already_generated": True})
        db.session.commit()

    # Create a round-robin schedule for a number of participants based upon league size and extend to the number of weeks
    # in the season if a league's matchups have not already been generated
    num_participants = len(league_member_ids)
    base_schedule = round_robin_schedule(num_participants)
    full_schedule = extend_schedule(base_schedule, 16)
    print_schedule(full_schedule)
    commit_schedule(full_schedule, league_id=league_id)


    "The following is for the navbar at the top of the screen"
    leagues = List_of_leagues_update1.query.filter_by(user_id=current_user.id)
    leagues_list = [(League.query.filter_by(id=item.league).first().league_name, item.league) for item in
                    leagues]
    league_member_names = [User.query.filter_by(id=member.member).first().name for member in league_members
                           if member.league_id == league_id]
    if not League.query.filter_by(id=league_id).first().draft_complete:
        league_manager = League.query.filter_by(id=league_id).first().league_manager
    return render_template("league_dashboard.html", league_members=league_members, league_id=league_id,
                           league_member_names=league_member_names, league_manager=league_manager, leagues_list=leagues_list)


"""
This route will be the main link to see a person's dashboard. It will automatically show the standings for the current
week. It will have a link to display the weeks for someone to choose so they can see the standings from any given week
"""


@app.route("/UserDashboard", methods=['GET', 'POST'])
@login_required
def UserDashboard():
    # Add analysis to db if the user is not me
    if current_user.id != 13:
        num_of_visits = Analysis.query.filter(Analysis.endpoint == "userdashboard").first().num_of_visits
        db.session.query(Analysis).filter(Analysis.endpoint == "userdashboard").update(
            {"num_of_visits": num_of_visits + 1})
        db.session.commit()

    user_list_of_leagues = [league.league_id for league in
                            List_of_leagues_update1.query.filter_by(user_id=current_user.id)]
    user_list_of_league_members = {}
    league_managers_dict = {}
    counter = 0
    leagues = List_of_leagues_update1.query.filter_by(user_id=current_user.id)
    leagues_list = [(League.query.filter_by(id=item.league).first().league_name, item.league) for item in
                    leagues]

    for list_of_members in user_list_of_leagues:
        temporary_list1 = []
        for item in list_of_members.league_members:
            temporary_list1.append(User.query.filter_by(id=item.member).first().name)
        user_list_of_league_members[counter] = temporary_list1
        league_managers_dict[counter] = League.query.filter_by(id=item.league_id).first().league_manager
        counter += 1

    league_number = 1
    data = pandas.read_csv("Team_points.csv", encoding='latin-1')

    with open("Teams.txt", encoding='ISO-8859-1') as file:
        text = file.read()
        teams = text.split(",")

    "Determine current week and previous week to calculate standings and previous standings"
    week, postseason = my_functions.determine_week_number()
    if week == 1:
        previous_week = 1
    else:
        previous_week = week - 1

    """
	Converts csv data to dictionary and it loops through every team (both for the current week and the new week) to get
	everyone's total. It loops through every team and determines their score on the given week and saves it to a
	dictionary (current_week_points_dict and previous_week_points_dict). It will also get data for team standings here
	by generating a dictionary (team_score_dict) that has the point totals for every team that week
	"""

    points_dict = data.to_dict()
    current_week_points_dict = {}
    previous_week_points_dict = {}
    team_score_dict = {}

    # for team in teams:
    #     i = 0
    #     points = 0
    #     while i < week:
    #         points += points_dict[team][i]
    #         i += 1
    #
    #     i = 0
    #     previous_points = 0
    #     while i < previous_week:
    #         previous_points += points_dict[team][i]
    #         i += 1
    #
    #     current_week_points_dict[team] = points
    #     previous_week_points_dict[team] = previous_points
    #     team_score_dict[team] = points

    """
	The dictionaries generated previously are sorted by score and the places are determined for both the current week
	and the previous week. Everything is then returned to be rendered by the html doc. Point totals are only generated
	for the current week for the teams but not the people. Then a new dictionary is made that has multiple dictionaries
	for each team (rank, points, last result, player, and conference)
	"""
    current_week_score_dict = dict(
        sorted(my_functions.determine_scores(points_dict=current_week_points_dict, league_number=league_number).items(),
               key=lambda kv: kv[1], reverse=True))
    previous_week_score_dict = dict(
        sorted(
            my_functions.determine_scores(points_dict=previous_week_points_dict, league_number=league_number).items(),
            key=lambda kv: kv[1], reverse=True))
    team_score_dict_sorted = dict(sorted(team_score_dict.items(), key=lambda kv: kv[1], reverse=True))
    team_data_dict = {team: {"points": ""} for team in team_score_dict_sorted}

    counter = 1
    for team in team_data_dict:
        team_data_dict[team]["rank"] = counter
        counter += 1

    for team, points in team_score_dict_sorted.items():
        team_data_dict[team]["points"] = points

    places = {}
    counter = 1
    for key, value in current_week_score_dict.items():
        places[key] = counter
        counter += 1

    previous_places = {}
    counter = 1
    for key, value in previous_week_score_dict.items():
        previous_places[key] = counter
        counter += 1

    # for team in teams:
    #     team = team.replace("&", "%26")
    #     with open(f"Team_Results/{team}.txt", 'r', encoding='ISO-8859-1') as file:
    #         text = file.read()
    #         games_list = text.split(',')
    #         previous_game = games_list[-2]
    #         team_data_dict[team.replace("%26", "&")]["last_result"] = previous_game

    data = pandas.read_csv(f"Leagues/League{league_number}.csv", encoding='latin-1')
    player_teams_initial = data.to_dict()
    player_teams_final = my_functions.convert_dict_to_simple_dict(player_teams_initial)

    data = pandas.read_csv(f"This_Weeks_Games/League{league_number}.csv", encoding='latin-1')
    team_games = data.to_dict()
    upcoming_team_games = my_functions.convert_dict_to_simple_dict(team_games)

    """
	Variables used: week_num is the week number to be used by the html to calculate the standings.
	display_num is to be used to display the week that was generated by default as the most recent week
	score_dict is the dictionary passed to display the current scores.
	places is the dictionary passed to display the current standings of people in the league.
	previous_score_dict is used to generate the previous week's scores of people in the league.
	previous_places is used to generate the previous week's standings of people in the league.
	team_data_dict is used to pass: a team's score, a team's last result, and what conference that team is in.
	player_teams_final passes in what player owns the team (passes a blank result if unowned).
	"""
    return render_template("UserDashboard.html", week_num=week, display_num=week, score_dict=current_week_score_dict,
                           places=places, previous_score_dict=previous_week_score_dict, previous_places=previous_places,
                           player_teams_final=player_teams_final,
                           upcoming_team_games=upcoming_team_games, league_number=league_number,
                           user_leagues=user_list_of_leagues,
                           user_list_of_league_members=user_list_of_league_members,
                           league_managers_dict=league_managers_dict, leagues_list=leagues_list)



@app.route('/graphtest')
def graphtest():
    test_data = {
        'Month': ['Jan', 'Feb', 'Mar', 'Apr'],
        'Sales': [100, 200, 150, 300],
        'Expenses': [80, 150, 120, 200]
    }

    wins_dict = {
        'Clemson': {'conference': 'ACC', 'expected wins': {'2021': 11.5, '2022': 10.5, '2023': 10, '2024': 9.5, '2025': 9.5},
                    'actual wins': {'2021': 9, '2022': 10, '2023': 8, '2024': 9, '2025': 7}},
        'Alabama': {'conference': 'SEC', 'expected wins': {'2021': 11.5, '2022': 10.5, '2023': 10.5, '2024': 9.5, '2025': 9.5},
                    'actual wins': {'2021': 11, '2022': 10, '2023': 11, '2024': 9, '2025': 10}},
        'Ohio State': {'conference': 'BIG 10', 'expected wins': {'2021': 11, '2022': 10.5, '2023': 10.5, '2024': 10.5, '2025': 10.5},
                       'actual wins': {'2021': 10, '2022': 11, '2023': 11, '2024': 10, '2025': 12}},
        'Oklahoma': {'conference': 'SEC', 'expected wins': {'2021': 11, '2022': 9.5, '2023': 9.5, '2024': 7.5, '2025': 6.5},
                     'actual wins': {'2021': 10, '2022': 6, '2023': 10, '2024': 6, '2025': 10}},
        'Georgia': {'conference': 'SEC', 'expected wins': {'2021': 10.5, '2022': 10.5, '2023': 11.5, '2024': 10.5, '2025': 9.5},
                    'actual wins': {'2021': 12, '2022': 12, '2023': 12, '2024': 10, '2025': 11}},
        'North Carolina': {'conference': 'ACC', 'expected wins': {'2021': 10, '2022': 7.5, '2023': 8, '2024': 7.5, '2025': 7.5},
                           'actual wins': {'2021': 6, '2022': 9, '2023': 8, '2024': 6, '2025': 4}},
        'Cincinnati': {'conference': 'BIG 12', 'expected wins': {'2021': 10, '2022': 9, '2023': 5.5, '2024': 5, '2025': 6.5},
                       'actual wins': {'2021': 12, '2022': 9, '2023': 3, '2024': 5, '2025': 7}},
        'Miami': {'conference': 'ACC', 'expected wins': {'2021': 9.5, '2022': 8.5, '2023': 7.5, '2024': 9, '2025': 9.5},
                  'actual wins': {'2021': 7, '2022': 5, '2023': 7, '2024': 10, '2025': 10}},
        'Texas A&M': {'conference': 'SEC', 'expected wins': {'2021': 9.5, '2022': 8.5, '2023': 8, '2024': 8.5, '2025': 8.5},
                      'actual wins': {'2021': 8, '2022': 5, '2023': 7, '2024': 8, '2025': 11}},
        'Iowa State': {'conference': 'BIG 12', 'expected wins': {'2021': 9.5, '2022': 6.5, '2023': 5.5, '2024': 7.5, '2025': 7.5},
                       'actual wins': {'2021': 7, '2022': 4, '2023': 7, '2024': 10, '2025': 8}},
        'Wisconsin': {'conference': 'BIG 10', 'expected wins': {'2021': 9.5, '2022': 8.5, '2023': 8.5, '2024': 7, '2025': 5.5},
                      'actual wins': {'2021': 8, '2022': 6, '2023': 7, '2024': 5, '2025': 4}},
        'UCF': {'conference': 'BIG 12', 'expected wins': {'2021': 9.5, '2022': 8.5, '2023': 6.5, '2024': 7.5, '2025': 5.5},
                'actual wins': {'2021': 8, '2022': 9, '2023': 6, '2024': 4, '2025': 5}},
        'Washington': {'conference': 'BIG 10', 'expected wins': {'2021': 9, '2022': 7.5, '2023': 9.5, '2024': 6.5, '2025': 7.5},
                       'actual wins': {'2021': 4, '2022': 10, '2023': 12, '2024': 6, '2025': 8}},
        'Penn State': {'conference': 'BIG 10', 'expected wins': {'2021': 9, '2022': 8.5, '2023': 9.5, '2024': 10.5, '2025': 10.5},
                       'actual wins': {'2021': 7, '2022': 10, '2023': 10, '2024': 11, '2025': 6}},
        'Florida': {'conference': 'SEC', 'expected wins': {'2021': 9, '2022': 7, '2023': 5.5, '2024': 4.5, '2025': 7.5},
                    'actual wins': {'2021': 6, '2022': 6, '2023': 5, '2024': 7, '2025': 4}},
        'Notre Dame': {'conference': 'IND', 'expected wins': {'2021': 9, '2022': 8.5, '2023': 8.5, '2024': 10, '2025': 10.5},
                       'actual wins': {'2021': 11, '2022': 8, '2023': 9, '2024': 11, '2025': 10}},
        'Arizona State': {'conference': 'BIG 12', 'expected wins': {'2021': 9, '2022': 6.5, '2023': 5, '2024': 4.5, '2025': 8.5},
                          'actual wins': {'2021': 8, '2022': 3, '2023': 3, '2024': 10, '2025': 8}},
        'Oregon': {'conference': 'BIG 10', 'expected wins': {'2021': 9, '2022': 8.5, '2023': 9.5, '2024': 10.5, '2025': 10.5},
                   'actual wins': {'2021': 10, '2022': 9, '2023': 11, '2024': 12, '2025': 11}},
        'USC': {'conference': 'BIG 10', 'expected wins': {'2021': 8.5, '2022': 9.5, '2023': 10, '2024': 7, '2025': 7.5},
                'actual wins': {'2021': 4, '2022': 11, '2023': 7, '2024': 6, '2025': 9}},
        'Utah': {'conference': 'BIG 12', 'expected wins': {'2021': 8.5, '2022': 9, '2023': 8.5, '2024': 9.5, '2025': 7.5},
                 'actual wins': {'2021': 9, '2022': 9, '2023': 8, '2024': 5, '2025': 10}},
        'LSU': {'conference': 'SEC', 'expected wins': {'2021': 8.5, '2022': 7, '2023': 9.5, '2024': 9, '2025': 8.5},
                'actual wins': {'2021': 6, '2022': 9, '2023': 9, '2024': 8, '2025': 7}},
        'Iowa': {'conference': 'BIG 12', 'expected wins': {'2021': 8.5, '2022': 7.5, '2023': 8, '2024': 8, '2025': 7.5},
                 'actual wins': {'2021': 10, '2022': 7, '2023': 10, '2024': 8, '2025': 8}},
        'Texas': {'conference': 'SEC', 'expected wins': {'2021': 8, '2022': 8, '2023': 9.5, '2024': 10.5, '2025': 9.5},
                  'actual wins': {'2021': 5, '2022': 8, '2023': 11, '2024': 11, '2025': 9}},
        'Houston': {'conference': 'BIG 12', 'expected wins': {'2021': 8, '2022': 9, '2023': 4.5, '2024': 3.5, '2025': 6.5},
                    'actual wins': {'2021': 11, '2022': 7, '2023': 4, '2024': 4, '2025': 9}},
        'Ole Miss': {'conference': 'SEC', 'expected wins': {'2021': 7.5, '2022': 7.5, '2023': 7.5, '2024': 9.5, '2025': 8.5},
                     'actual wins': {'2021': 10, '2022': 8, '2023': 10, '2024': 9, '2025': 11}},
        'Indiana': {'conference': 'BIG 10', 'expected wins': {'2021': 7.5, '2022': 4, '2023': 3.5, '2024': 5.5, '2025': 8.5},
                    'actual wins': {'2021': 2, '2022': 4, '2023': 3, '2024': 11, '2025': 12}},
        'Oklahoma State': {'conference': 'BIG 12', 'expected wins': {'2021': 7.5, '2022': 8.5, '2023': 6.5, '2024': 8, '2025': 4.5},
                           'actual wins': {'2021': 11, '2022': 7, '2023': 9, '2024': 3, '2025': 1}},
        'TCU': {'conference': 'BIG 12', 'expected wins': {'2021': 7.5, '2022': 6.5, '2023': 7.5, '2024': 7.5, '2025': 6.5},
                'actual wins': {'2021': 5, '2022': 12, '2023': 5, '2024': 8, '2025': 8}},
        'Auburn': {'conference': 'SEC', 'expected wins': {'2021': 7, '2022': 6.5, '2023': 6.5, '2024': 7.5, '2025': 7.5},
                   'actual wins': {'2021': 6, '2022': 5, '2023': 6, '2024': 5, '2025': 5}},
        'Virginia Tech': {'conference': 'ACC', 'expected wins': {'2021': 7, '2022': 6.5, '2023': 5, '2024': 8.5, '2025': 6.5},
                          'actual wins': {'2021': 6, '2022': 3, '2023': 6, '2024': 6, '2025': 3}},
        'Boston College': {'conference': 'ACC', 'expected wins': {'2021': 7, '2022': 6.5, '2023': 5.5, '2024': 5, '2025': 5.5},
                           'actual wins': {'2021': 6, '2022': 3, '2023': 6, '2024': 7, '2025': 2}},
        'Kentucky': {'conference': 'SEC', 'expected wins': {'2021': 7, '2022': 7.5, '2023': 7, '2024': 6.5, '2025': 4.5},
                     'actual wins': {'2021': 9, '2022': 7, '2023': 7, '2024': 4, '2025': 5}},
        'Missouri': {'conference': 'SEC', 'expected wins': {'2021': 7, '2022': 5.5, '2023': 6.5, '2024': 9.5, '2025': 7.5},
                     'actual wins': {'2021': 6, '2022': 6, '2023': 10, '2024': 9, '2025': 8}},
        'UCLA': {'conference': 'BIG 10', 'expected wins': {'2021': 7, '2022': 8.5, '2023': 8.5, '2024': 5, '2025': 5.5},
                 'actual wins': {'2021': 8, '2022': 9, '2023': 7, '2024': 5, '2025': 3}},
        'Pittsburgh': {'conference': 'ACC', 'expected wins': {'2021': 7, '2022': 8.5, '2023': 6.5, '2024': 5.5, '2025': 6.5},
                       'actual wins': {'2021': 10, '2022': 8, '2023': 3, '2024': 7, '2025': 8}},
        'Wake Forest': {'conference': 'ACC', 'expected wins': {'2021': 6.5, '2022': 8.5, '2023': 6, '2024': 4.5, '2025': 4.5},
                        'actual wins': {'2021': 10, '2022': 7, '2023': 4, '2024': 4, '2025': 8}},
        'NC State': {'conference': 'ACC', 'expected wins': {'2021': 6.5, '2022': 6.5, '2023': 6.5, '2024': 8.5, '2025': 6.5},
                     'actual wins': {'2021': 9, '2022': 8, '2023': 9, '2024': 6, '2025': 7}},
        'West Virginia': {'conference': 'BIG 12', 'expected wins': {'2021': 6.5, '2022': 5.5, '2023': 4.5, '2024': 6.5, '2025': 5.5},
                          'actual wins': {'2021': 6, '2022': 5, '2023': 8, '2024': 6, '2025': 4}},
        'Louisville': {'conference': 'ACC', 'expected wins': {'2021': 6.5, '2022': 6.5, '2023': 8, '2024': 8.5, '2025': 8.5},
                       'actual wins': {'2021': 6, '2022': 7, '2023': 10, '2024': 8, '2025': 8}},
        'BYU': {'conference': 'BIG 12', 'expected wins': {'2021': 6.5, '2022': 8.5, '2023': 5.5, '2024': 4.5, '2025': 6.5},
                'actual wins': {'2021': 10, '2022': 7, '2023': 5, '2024': 10, '2025': 11}},
        'Northwestern': {'conference': 'BIG 10', 'expected wins': {'2021': 6.5, '2022': 4, '2023': 3, '2024': 4.5, '2025': 3.5},
                         'actual wins': {'2021': 3, '2022': 1, '2023': 7, '2024': 4, '2025': 6}},
        'SMU': {'conference': 'ACC', 'expected wins': {'2021': 6, '2022': 8.5, '2023': 8.5, '2024': 8.5, '2025': 8.5},
                'actual wins': {'2021': 8, '2022': 7, '2023': 10, '2024': 11, '2025': 8}},
        'Tennessee': {'conference': 'SEC', 'expected wins': {'2021': 6, '2022': 7.5, '2023': 9.5, '2024': 8.5, '2025': 8.5},
                      'actual wins': {'2021': 7, '2022': 10, '2023': 8, '2024': 10, '2025': 8}},
        'Nebraska': {'conference': 'BIG 10', 'expected wins': {'2021': 6, '2022': 7.5, '2023': 6, '2024': 7.5, '2025': 7.5},
                     'actual wins': {'2021': 3, '2022': 4, '2023': 5, '2024': 6, '2025': 7}},
        'Maryland': {'conference': 'ACC', 'expected wins': {'2021': 6, '2022': 6, '2023': 7, '2024': 6.5, '2025': 4.5},
                     'actual wins': {'2021': 6, '2022': 7, '2023': 7, '2024': 4, '2025': 4}},
        'California': {'conference': 'ACC', 'expected wins': {'2021': 6, '2022': 5.5, '2023': 5, '2024': 6, '2025': 5.5},
                       'actual wins': {'2021': 4, '2022': 4, '2023': 6, '2024': 6, '2025': 7}},
        'Virginia': {'conference': 'ACC', 'expected wins': {'2021': 6, '2022': 7.5, '2023': 3.5, '2024': 4.5, '2025': 6.5},
                     'actual wins': {'2021': 6, '2022': 3, '2023': 3, '2024': 5, '2025': 10}},
        'Mississippi State': {'conference': 'SEC', 'expected wins': {'2021': 6, '2022': 6.5, '2023': 6.5, '2024': 4, '2025': 3.5},
                              'actual wins': {'2021': 7, '2022': 8, '2023': 5, '2024': 2, '2025': 5}},
        'Florida State': {'conference': 'ACC', 'expected wins': {'2021': 5.5, '2022': 6.5, '2023': 10, '2024': 9.5, '2025': 6.5},
                          'actual wins': {'2021': 5, '2022': 9, '2023': 12, '2024': 2, '2025': 5}},
        'Kansas State': {'conference': 'BIG 12', 'expected wins': {'2021': 5.5, '2022': 6.5, '2023': 8.5, '2024': 9.5, '2025': 8.5},
                         'actual wins': {'2021': 7, '2022': 9, '2023': 8, '2024': 8, '2025': 6}},
        'Baylor': {'conference': 'BIG 12', 'expected wins': {'2021': 5.5, '2022': 7.5, '2023': 7, '2024': 5.5, '2025': 7.5},
                   'actual wins': {'2021': 10, '2022': 6, '2023': 3, '2024': 8, '2025': 5}},
        'Arkansas': {'conference': 'SEC', 'expected wins': {'2021': 5.5, '2022': 7.5, '2023': 7, '2024': 4.5, '2025': 5.5},
                     'actual wins': {'2021': 8, '2022': 6, '2023': 4, '2024': 6, '2025': 2}},
        'Georgia Tech': {'conference': 'ACC', 'expected wins': {'2021': 5, '2022': 3.5, '2023': 4.5, '2024': 5, '2025': 7.5},
                         'actual wins': {'2021': 3, '2022': 5, '2023': 6, '2024': 7, '2025': 9}},
        'Purdue': {'conference': 'BIG 10', 'expected wins': {'2021': 5, '2022': 7.5, '2023': 5.5, '2024': 4.5, '2025': 2.5},
                   'actual wins': {'2021': 8, '2022': 8, '2023': 4, '2024': 1, '2025': 2}},
        'Texas Tech': {'conference': 'BIG 12', 'expected wins': {'2021': 4.5, '2022': 5.5, '2023': 7.5, '2024': 7.5, '2025': 8.5},
                       'actual wins': {'2021': 6, '2022': 7, '2023': 6, '2024': 8, '2025': 11}},
        'Michigan State': {'conference': 'BIG 10', 'expected wins': {'2021': 4.5, '2022': 7.5, '2023': 5.5, '2024': 5, '2025': 5.5},
                           'actual wins': {'2021': 10, '2022': 5, '2023': 4, '2024': 5, '2025': 4}},
        'Colorado': {'conference': 'BIG 12', 'expected wins': {'2021': 4.5, '2022': 3.5, '2023': 3.5, '2024': 5.5, '2025': 6.5},
                     'actual wins': {'2021': 4, '2022': 1, '2023': 4, '2024': 9, '2025': 3}},
        'Rutgers': {'conference': 'BIG 10', 'expected wins': {'2021': 4, '2022': 4, '2023': 4.5, '2024': 4.5, '2025': 5.5},
                    'actual wins': {'2021': 5, '2022': 4, '2023': 6, '2024': 7, '2025': 5}},
        'Stanford': {'conference': 'ACC', 'expected wins': {'2021': 3.5, '2022': 4.5, '2023': 3, '2024': 3.5, '2025': 3.5},
                     'actual wins': {'2021': 3, '2022': 3, '2023': 3, '2024': 3, '2025': 4}},
        'South Carolina': {'conference': 'SEC', 'expected wins': {'2021': 3.5, '2022': 6, '2023': 6.5, '2024': 5.5, '2025': 7.5},
                           'actual wins': {'2021': 6, '2022': 8, '2023': 5, '2024': 9, '2025': 4}},
        'Illinois': {'conference': 'BIG 10', 'expected wins': {'2021': 3.5, '2022': 4.5, '2023': 6.5, '2024': 5.5, '2025': 7.5},
                     'actual wins': {'2021': 5, '2022': 8, '2023': 5, '2024': 9, '2025': 8}},
        'Duke': {'conference': 'ACC', 'expected wins': {'2021': 3.5, '2022': 3, '2023': 6.5, '2024': 5.5, '2025': 6.5},
                 'actual wins': {'2021': 3, '2022': 8, '2023': 7, '2024': 9, '2025': 7}},
        'Vanderbilt': {'conference': 'SEC', 'expected wins': {'2021': 3, '2022': 2.5, '2023': 3.5, '2024': 3, '2025': 5.5},
                       'actual wins': {'2021': 2, '2022': 5, '2023': 2, '2024': 6, '2025': 10}},
        'Syracuse': {'conference': 'ACC', 'expected wins': {'2021': 3, '2022': 5, '2023': 6.5, '2024': 7, '2025': 5.5},
                     'actual wins': {'2021': 5, '2022': 7, '2023': 6, '2024': 9, '2025': 3}},
        'Arizona': {'conference': 'BIG 12', 'expected wins': {'2021': 2.5, '2022': 2.5, '2023': 5, '2024': 8, '2025': 4.5},
                    'actual wins': {'2021': 1, '2022': 5, '2023': 9, '2024': 4, '2025': 9}},
        'Kansas': {'conference': 'BIG 12', 'expected wins': {'2021': 1.5, '2022': 2.5, '2023': 6.5, '2024': 8, '2025': 6.5},
                   'actual wins': {'2021': 2, '2022': 6, '2023': 8, '2024': 5, '2025': 5}},
        'Michigan': {'conference': 'BIG 10', 'expected wins': {'2021': 7.5, '2022': 9.5, '2023': 10.5, '2024': 9, '2025': 8.5},
                     'actual wins': {'2021': 11, '2022': 12, '2023': 12, '2024': 7, '2025': 9}},
        'Minnesota': {'conference': 'BIG 10', 'expected wins': {'2021': 7, '2022': 7.5, '2023': 7, '2024': 5, '2025': 7.5},
                      'actual wins': {'2021': 8, '2022': 8, '2023': 5, '2024': 7, '2025': 7}},
    }

    # Build initial chart with first team
    wins_dict = dict(sorted(wins_dict.items()))
    first_team = list(wins_dict.keys())[0]
    first_data = wins_dict[first_team]
    years = list(first_data['expected wins'].keys())
    wins = list(first_data['expected wins'].values())

    fig = px.line(
        x=years,
        y=wins,
        title=f'{first_team} Expected Wins by Year',
        labels={'x': 'Year', 'y': 'Expected Wins'}
    )
    fig.update_traces(name=first_team, showlegend=True)

    chart_json = pio.to_json(fig, validate=False, engine="json")

    # Pass all team data to the template for JS to use
    teams_json = json.dumps(wins_dict)

    return render_template('graphtest.html', chart_json=chart_json, teams_json=teams_json, team_names=list(wins_dict.keys()))


@app.route('/expected_vs_actual_graphs')
def expected_vs_actual_graphs():
    wins_dict = {
        'Clemson': {'conference': 'ACC', 'expected wins': {'2021': 11.5, '2022': 10.5, '2023': 10, '2024': 9.5, '2025': 9.5},
                    'actual wins': {'2021': 9, '2022': 10, '2023': 8, '2024': 9, '2025': 7}, 'primary color': '#F56600'},
        'Alabama': {'conference': 'SEC', 'expected wins': {'2021': 11.5, '2022': 10.5, '2023': 10.5, '2024': 9.5, '2025': 9.5},
                    'actual wins': {'2021': 11, '2022': 10, '2023': 11, '2024': 9, '2025': 10}, 'primary color': '#9E1B32'},
        'Ohio State': {'conference': 'BIG 10', 'expected wins': {'2021': 11, '2022': 10.5, '2023': 10.5, '2024': 10.5, '2025': 10.5},
                       'actual wins': {'2021': 10, '2022': 11, '2023': 11, '2024': 10, '2025': 12}, 'primary color': '#BB0000'},
        'Oklahoma': {'conference': 'SEC', 'expected wins': {'2021': 11, '2022': 9.5, '2023': 9.5, '2024': 7.5, '2025': 6.5},
                     'actual wins': {'2021': 10, '2022': 6, '2023': 10, '2024': 6, '2025': 10}, 'primary color': '#841617'},
        'Georgia': {'conference': 'SEC', 'expected wins': {'2021': 10.5, '2022': 10.5, '2023': 11.5, '2024': 10.5, '2025': 9.5},
                    'actual wins': {'2021': 12, '2022': 12, '2023': 12, '2024': 10, '2025': 11}, 'primary color': '#BA0C2F'},
        'North Carolina': {'conference': 'ACC', 'expected wins': {'2021': 10, '2022': 7.5, '2023': 8, '2024': 7.5, '2025': 7.5},
                           'actual wins': {'2021': 6, '2022': 9, '2023': 8, '2024': 6, '2025': 4}, 'primary color': '#4B9CD3'},
        'Cincinnati': {'conference': 'BIG 12', 'expected wins': {'2021': 10, '2022': 9, '2023': 5.5, '2024': 5, '2025': 6.5},
                       'actual wins': {'2021': 12, '2022': 9, '2023': 3, '2024': 5, '2025': 7}, 'primary color': '#E00122'},
        'Miami': {'conference': 'ACC', 'expected wins': {'2021': 9.5, '2022': 8.5, '2023': 7.5, '2024': 9, '2025': 9.5},
                  'actual wins': {'2021': 7, '2022': 5, '2023': 7, '2024': 10, '2025': 10}, 'primary color': '#F47321'},
        'Texas A&M': {'conference': 'SEC', 'expected wins': {'2021': 9.5, '2022': 8.5, '2023': 8, '2024': 8.5, '2025': 8.5},
                      'actual wins': {'2021': 8, '2022': 5, '2023': 7, '2024': 8, '2025': 11}, 'primary color': '#500000'},
        'Iowa State': {'conference': 'BIG 12', 'expected wins': {'2021': 9.5, '2022': 6.5, '2023': 5.5, '2024': 7.5, '2025': 7.5},
                       'actual wins': {'2021': 7, '2022': 4, '2023': 7, '2024': 10, '2025': 8}, 'primary color': '#C8102E'},
        'Wisconsin': {'conference': 'BIG 10', 'expected wins': {'2021': 9.5, '2022': 8.5, '2023': 8.5, '2024': 7, '2025': 5.5},
                      'actual wins': {'2021': 8, '2022': 6, '2023': 7, '2024': 5, '2025': 4}, 'primary color': '#C5050C'},
        'UCF': {'conference': 'BIG 12', 'expected wins': {'2021': 9.5, '2022': 8.5, '2023': 6.5, '2024': 7.5, '2025': 5.5},
                'actual wins': {'2021': 8, '2022': 9, '2023': 6, '2024': 4, '2025': 5}, 'primary color': '#FFC904'},
        'Washington': {'conference': 'BIG 10', 'expected wins': {'2021': 9, '2022': 7.5, '2023': 9.5, '2024': 6.5, '2025': 7.5},
                       'actual wins': {'2021': 4, '2022': 10, '2023': 12, '2024': 6, '2025': 8}, 'primary color': '#4B2E83'},
        'Penn State': {'conference': 'BIG 10', 'expected wins': {'2021': 9, '2022': 8.5, '2023': 9.5, '2024': 10.5, '2025': 10.5},
                       'actual wins': {'2021': 7, '2022': 10, '2023': 10, '2024': 11, '2025': 6}, 'primary color': '#041E42'},
        'Florida': {'conference': 'SEC', 'expected wins': {'2021': 9, '2022': 7, '2023': 5.5, '2024': 4.5, '2025': 7.5},
                    'actual wins': {'2021': 6, '2022': 6, '2023': 5, '2024': 7, '2025': 4}, 'primary color': '#0021A5'},
        'Notre Dame': {'conference': 'IND', 'expected wins': {'2021': 9, '2022': 8.5, '2023': 8.5, '2024': 10, '2025': 10.5},
                       'actual wins': {'2021': 11, '2022': 8, '2023': 9, '2024': 11, '2025': 10}, 'primary color': '#C99700'},
        'Arizona State': {'conference': 'BIG 12', 'expected wins': {'2021': 9, '2022': 6.5, '2023': 5, '2024': 4.5, '2025': 8.5},
                          'actual wins': {'2021': 8, '2022': 3, '2023': 3, '2024': 10, '2025': 8}, 'primary color': '#8C1D40'},
        'Oregon': {'conference': 'BIG 10', 'expected wins': {'2021': 9, '2022': 8.5, '2023': 9.5, '2024': 10.5, '2025': 10.5},
                   'actual wins': {'2021': 10, '2022': 9, '2023': 11, '2024': 12, '2025': 11}, 'primary color': '#154733'},
        'USC': {'conference': 'BIG 10', 'expected wins': {'2021': 8.5, '2022': 9.5, '2023': 10, '2024': 7, '2025': 7.5},
                'actual wins': {'2021': 4, '2022': 11, '2023': 7, '2024': 6, '2025': 9}, 'primary color': '#990000'},
        'Utah': {'conference': 'BIG 12', 'expected wins': {'2021': 8.5, '2022': 9, '2023': 8.5, '2024': 9.5, '2025': 7.5},
                 'actual wins': {'2021': 9, '2022': 9, '2023': 8, '2024': 5, '2025': 10}, 'primary color': '#CC0000'},
        'LSU': {'conference': 'SEC', 'expected wins': {'2021': 8.5, '2022': 7, '2023': 9.5, '2024': 9, '2025': 8.5},
                'actual wins': {'2021': 6, '2022': 9, '2023': 9, '2024': 8, '2025': 7}, 'primary color': '#461D7C'},
        'Iowa': {'conference': 'BIG 12', 'expected wins': {'2021': 8.5, '2022': 7.5, '2023': 8, '2024': 8, '2025': 7.5},
                 'actual wins': {'2021': 10, '2022': 7, '2023': 10, '2024': 8, '2025': 8}, 'primary color': '#FFCD00'},
        'Texas': {'conference': 'SEC', 'expected wins': {'2021': 8, '2022': 8, '2023': 9.5, '2024': 10.5, '2025': 9.5},
                  'actual wins': {'2021': 5, '2022': 8, '2023': 11, '2024': 11, '2025': 9}, 'primary color': '#BF5700'},
        'Houston': {'conference': 'BIG 12', 'expected wins': {'2021': 8, '2022': 9, '2023': 4.5, '2024': 3.5, '2025': 6.5},
                    'actual wins': {'2021': 11, '2022': 7, '2023': 4, '2024': 4, '2025': 9}, 'primary color': '#C8102E'},
        'Ole Miss': {'conference': 'SEC', 'expected wins': {'2021': 7.5, '2022': 7.5, '2023': 7.5, '2024': 9.5, '2025': 8.5},
                     'actual wins': {'2021': 10, '2022': 8, '2023': 10, '2024': 9, '2025': 11}, 'primary color': '#CE1126'},
        'Indiana': {'conference': 'BIG 10', 'expected wins': {'2021': 7.5, '2022': 4, '2023': 3.5, '2024': 5.5, '2025': 8.5},
                    'actual wins': {'2021': 2, '2022': 4, '2023': 3, '2024': 11, '2025': 12}, 'primary color': '#990000'},
        'Oklahoma State': {'conference': 'BIG 12', 'expected wins': {'2021': 7.5, '2022': 8.5, '2023': 6.5, '2024': 8, '2025': 4.5},
                           'actual wins': {'2021': 11, '2022': 7, '2023': 9, '2024': 3, '2025': 1}, 'primary color': '#FF6600'},
        'TCU': {'conference': 'BIG 12', 'expected wins': {'2021': 7.5, '2022': 6.5, '2023': 7.5, '2024': 7.5, '2025': 6.5},
                'actual wins': {'2021': 5, '2022': 12, '2023': 5, '2024': 8, '2025': 8}, 'primary color': '#4D1979'},
        'Auburn': {'conference': 'SEC', 'expected wins': {'2021': 7, '2022': 6.5, '2023': 6.5, '2024': 7.5, '2025': 7.5},
                   'actual wins': {'2021': 6, '2022': 5, '2023': 6, '2024': 5, '2025': 5}, 'primary color': '#0C2340'},
        'Virginia Tech': {'conference': 'ACC', 'expected wins': {'2021': 7, '2022': 6.5, '2023': 5, '2024': 8.5, '2025': 6.5},
                          'actual wins': {'2021': 6, '2022': 3, '2023': 6, '2024': 6, '2025': 3}, 'primary color': '#CF4420'},
        'Boston College': {'conference': 'ACC', 'expected wins': {'2021': 7, '2022': 6.5, '2023': 5.5, '2024': 5, '2025': 5.5},
                           'actual wins': {'2021': 6, '2022': 3, '2023': 6, '2024': 7, '2025': 2}, 'primary color': '#8B0000'},
        'Kentucky': {'conference': 'SEC', 'expected wins': {'2021': 7, '2022': 7.5, '2023': 7, '2024': 6.5, '2025': 4.5},
                     'actual wins': {'2021': 9, '2022': 7, '2023': 7, '2024': 4, '2025': 5}, 'primary color': '#0033A0'},
        'Missouri': {'conference': 'SEC', 'expected wins': {'2021': 7, '2022': 5.5, '2023': 6.5, '2024': 9.5, '2025': 7.5},
                     'actual wins': {'2021': 6, '2022': 6, '2023': 10, '2024': 9, '2025': 8}, 'primary color': '#F1B82D'},
        'UCLA': {'conference': 'BIG 10', 'expected wins': {'2021': 7, '2022': 8.5, '2023': 8.5, '2024': 5, '2025': 5.5},
                 'actual wins': {'2021': 8, '2022': 9, '2023': 7, '2024': 5, '2025': 3}, 'primary color': '#2D68C4'},
        'Pittsburgh': {'conference': 'ACC', 'expected wins': {'2021': 7, '2022': 8.5, '2023': 6.5, '2024': 5.5, '2025': 6.5},
                       'actual wins': {'2021': 10, '2022': 8, '2023': 3, '2024': 7, '2025': 8}, 'primary color': '#003594'},
        'Wake Forest': {'conference': 'ACC', 'expected wins': {'2021': 6.5, '2022': 8.5, '2023': 6, '2024': 4.5, '2025': 4.5},
                        'actual wins': {'2021': 10, '2022': 7, '2023': 4, '2024': 4, '2025': 8}, 'primary color': '#9E7E38'},
        'NC State': {'conference': 'ACC', 'expected wins': {'2021': 6.5, '2022': 6.5, '2023': 6.5, '2024': 8.5, '2025': 6.5},
                     'actual wins': {'2021': 9, '2022': 8, '2023': 9, '2024': 6, '2025': 7}, 'primary color': '#CC0000'},
        'West Virginia': {'conference': 'BIG 12', 'expected wins': {'2021': 6.5, '2022': 5.5, '2023': 4.5, '2024': 6.5, '2025': 5.5},
                          'actual wins': {'2021': 6, '2022': 5, '2023': 8, '2024': 6, '2025': 4}, 'primary color': '#002855'},
        'Louisville': {'conference': 'ACC', 'expected wins': {'2021': 6.5, '2022': 6.5, '2023': 8, '2024': 8.5, '2025': 8.5},
                       'actual wins': {'2021': 6, '2022': 7, '2023': 10, '2024': 8, '2025': 8}, 'primary color': '#AD0000'},
        'BYU': {'conference': 'BIG 12', 'expected wins': {'2021': 6.5, '2022': 8.5, '2023': 5.5, '2024': 4.5, '2025': 6.5},
                'actual wins': {'2021': 10, '2022': 7, '2023': 5, '2024': 10, '2025': 11}, 'primary color': '#002E5D'},
        'Northwestern': {'conference': 'BIG 10', 'expected wins': {'2021': 6.5, '2022': 4, '2023': 3, '2024': 4.5, '2025': 3.5},
                         'actual wins': {'2021': 3, '2022': 1, '2023': 7, '2024': 4, '2025': 6}, 'primary color': '#4E2A84'},
        'SMU': {'conference': 'ACC', 'expected wins': {'2021': 6, '2022': 8.5, '2023': 8.5, '2024': 8.5, '2025': 8.5},
                'actual wins': {'2021': 8, '2022': 7, '2023': 10, '2024': 11, '2025': 8}, 'primary color': '#0033A0'},
        'Tennessee': {'conference': 'SEC', 'expected wins': {'2021': 6, '2022': 7.5, '2023': 9.5, '2024': 8.5, '2025': 8.5},
                      'actual wins': {'2021': 7, '2022': 10, '2023': 8, '2024': 10, '2025': 8}, 'primary color': '#FF8200'},
        'Nebraska': {'conference': 'BIG 10', 'expected wins': {'2021': 6, '2022': 7.5, '2023': 6, '2024': 7.5, '2025': 7.5},
                     'actual wins': {'2021': 3, '2022': 4, '2023': 5, '2024': 6, '2025': 7}, 'primary color': '#E41C38'},
        'Maryland': {'conference': 'ACC', 'expected wins': {'2021': 6, '2022': 6, '2023': 7, '2024': 6.5, '2025': 4.5},
                     'actual wins': {'2021': 6, '2022': 7, '2023': 7, '2024': 4, '2025': 4}, 'primary color': '#E03A3E'},
        'California': {'conference': 'ACC', 'expected wins': {'2021': 6, '2022': 5.5, '2023': 5, '2024': 6, '2025': 5.5},
                       'actual wins': {'2021': 4, '2022': 4, '2023': 6, '2024': 6, '2025': 7}, 'primary color': '#003262'},
        'Virginia': {'conference': 'ACC', 'expected wins': {'2021': 6, '2022': 7.5, '2023': 3.5, '2024': 4.5, '2025': 6.5},
                     'actual wins': {'2021': 6, '2022': 3, '2023': 3, '2024': 5, '2025': 10}, 'primary color': '#232D4B'},
        'Mississippi State': {'conference': 'SEC', 'expected wins': {'2021': 6, '2022': 6.5, '2023': 6.5, '2024': 4, '2025': 3.5},
                              'actual wins': {'2021': 7, '2022': 8, '2023': 5, '2024': 2, '2025': 5}, 'primary color': '#660000'},
        'Florida State': {'conference': 'ACC', 'expected wins': {'2021': 5.5, '2022': 6.5, '2023': 10, '2024': 9.5, '2025': 6.5},
                          'actual wins': {'2021': 5, '2022': 9, '2023': 12, '2024': 2, '2025': 5}, 'primary color': '#782F40'},
        'Kansas State': {'conference': 'BIG 12', 'expected wins': {'2021': 5.5, '2022': 6.5, '2023': 8.5, '2024': 9.5, '2025': 8.5},
                         'actual wins': {'2021': 7, '2022': 9, '2023': 8, '2024': 8, '2025': 6}, 'primary color': '#512888'},
        'Baylor': {'conference': 'BIG 12', 'expected wins': {'2021': 5.5, '2022': 7.5, '2023': 7, '2024': 5.5, '2025': 7.5},
                   'actual wins': {'2021': 10, '2022': 6, '2023': 3, '2024': 8, '2025': 5}, 'primary color': '#003015'},
        'Arkansas': {'conference': 'SEC', 'expected wins': {'2021': 5.5, '2022': 7.5, '2023': 7, '2024': 4.5, '2025': 5.5},
                     'actual wins': {'2021': 8, '2022': 6, '2023': 4, '2024': 6, '2025': 2}, 'primary color': '#9D2235'},
        'Georgia Tech': {'conference': 'ACC', 'expected wins': {'2021': 5, '2022': 3.5, '2023': 4.5, '2024': 5, '2025': 7.5},
                         'actual wins': {'2021': 3, '2022': 5, '2023': 6, '2024': 7, '2025': 9}, 'primary color': '#B3A369'},
        'Purdue': {'conference': 'BIG 10', 'expected wins': {'2021': 5, '2022': 7.5, '2023': 5.5, '2024': 4.5, '2025': 2.5},
                   'actual wins': {'2021': 8, '2022': 8, '2023': 4, '2024': 1, '2025': 2}, 'primary color': '#CEB888'},
        'Texas Tech': {'conference': 'BIG 12', 'expected wins': {'2021': 4.5, '2022': 5.5, '2023': 7.5, '2024': 7.5, '2025': 8.5},
                       'actual wins': {'2021': 6, '2022': 7, '2023': 6, '2024': 8, '2025': 11}, 'primary color': '#CC0000'},
        'Michigan State': {'conference': 'BIG 10', 'expected wins': {'2021': 4.5, '2022': 7.5, '2023': 5.5, '2024': 5, '2025': 5.5},
                           'actual wins': {'2021': 10, '2022': 5, '2023': 4, '2024': 5, '2025': 4}, 'primary color': '#18453B'},
        'Colorado': {'conference': 'BIG 12', 'expected wins': {'2021': 4.5, '2022': 3.5, '2023': 3.5, '2024': 5.5, '2025': 6.5},
                     'actual wins': {'2021': 4, '2022': 1, '2023': 4, '2024': 9, '2025': 3}, 'primary color': '#CFB87C'},
        'Rutgers': {'conference': 'BIG 10', 'expected wins': {'2021': 4, '2022': 4, '2023': 4.5, '2024': 4.5, '2025': 5.5},
                    'actual wins': {'2021': 5, '2022': 4, '2023': 6, '2024': 7, '2025': 5}, 'primary color': '#CC0033'},
        'Stanford': {'conference': 'ACC', 'expected wins': {'2021': 3.5, '2022': 4.5, '2023': 3, '2024': 3.5, '2025': 3.5},
                     'actual wins': {'2021': 3, '2022': 3, '2023': 3, '2024': 3, '2025': 4}, 'primary color': '#8C1515'},
        'South Carolina': {'conference': 'SEC', 'expected wins': {'2021': 3.5, '2022': 6, '2023': 6.5, '2024': 5.5, '2025': 7.5},
                           'actual wins': {'2021': 6, '2022': 8, '2023': 5, '2024': 9, '2025': 4}, 'primary color': '#73000A'},
        'Illinois': {'conference': 'BIG 10', 'expected wins': {'2021': 3.5, '2022': 4.5, '2023': 6.5, '2024': 5.5, '2025': 7.5},
                     'actual wins': {'2021': 5, '2022': 8, '2023': 5, '2024': 9, '2025': 8}, 'primary color': '#E84A27'},
        'Duke': {'conference': 'ACC', 'expected wins': {'2021': 3.5, '2022': 3, '2023': 6.5, '2024': 5.5, '2025': 6.5},
                 'actual wins': {'2021': 3, '2022': 8, '2023': 7, '2024': 9, '2025': 7}, 'primary color': '#003087'},
        'Vanderbilt': {'conference': 'SEC', 'expected wins': {'2021': 3, '2022': 2.5, '2023': 3.5, '2024': 3, '2025': 5.5},
                       'actual wins': {'2021': 2, '2022': 5, '2023': 2, '2024': 6, '2025': 10}, 'primary color': '#866D4B'},
        'Syracuse': {'conference': 'ACC', 'expected wins': {'2021': 3, '2022': 5, '2023': 6.5, '2024': 7, '2025': 5.5},
                     'actual wins': {'2021': 5, '2022': 7, '2023': 6, '2024': 9, '2025': 3}, 'primary color': '#D44500'},
        'Arizona': {'conference': 'BIG 12', 'expected wins': {'2021': 2.5, '2022': 2.5, '2023': 5, '2024': 8, '2025': 4.5},
                    'actual wins': {'2021': 1, '2022': 5, '2023': 9, '2024': 4, '2025': 9}, 'primary color': '#AB0520'},
        'Kansas': {'conference': 'BIG 12', 'expected wins': {'2021': 1.5, '2022': 2.5, '2023': 6.5, '2024': 8, '2025': 6.5},
                   'actual wins': {'2021': 2, '2022': 6, '2023': 8, '2024': 5, '2025': 5}, 'primary color': '#0051A5'},
        'Michigan': {'conference': 'BIG 10', 'expected wins': {'2021': 7.5, '2022': 9.5, '2023': 10.5, '2024': 9, '2025': 8.5},
                     'actual wins': {'2021': 11, '2022': 12, '2023': 12, '2024': 7, '2025': 9}, 'primary color': '#00274C'},
        'Minnesota': {'conference': 'BIG 10', 'expected wins': {'2021': 7, '2022': 7.5, '2023': 7, '2024': 5, '2025': 7.5},
                      'actual wins': {'2021': 8, '2022': 8, '2023': 5, '2024': 7, '2025': 7}, 'primary color': '#7A0019'},
    }

    # Build initial chart with first team
    wins_dict = dict(sorted(wins_dict.items()))
    first_team = list(wins_dict.keys())[0]
    first_data = wins_dict[first_team]
    years = list(first_data['expected wins'].keys())
    wins = list(first_data['expected wins'].values())

    fig = px.line(
        x=years,
        y=wins,
        title=f'{first_team} Expected Wins by Year',
        labels={'x': 'Year', 'y': 'Expected Wins'}
    )
    fig.update_traces(name=first_team, showlegend=True)

    chart_json = pio.to_json(fig, validate=False, engine="json")

    # Pass all team data to the template for JS to use
    teams_json = json.dumps(wins_dict)

    return render_template('expected_vs_actual_graphs.html', chart_json=chart_json, teams_json=teams_json, team_names=list(wins_dict.keys()), wins_dict=wins_dict)


def end_nomination(nomination_id, room_id):
    """Called when the timer runs out — finalizes the sale."""
    nomination = DraftNomination.query.get(nomination_id)
    if nomination and nomination.status == 'active':
        nomination.status = 'sold'
        db.session.commit()

        winner = None
        if nomination.current_winner_id:
            # Deduct budget from winner
            participant = DraftParticipant.query.filter_by(draft_room_id=room_id, user_id=nomination.current_winner_id).first()
            if participant:
                participant.budget_remaining -= nomination.current_bid
                db.session.commit()
            winner = nomination.current_winner_id

        # Notify all users in the room
        socketio.emit('nomination_sold', {'nomination_id': nomination_id, 'team_id': nomination.nominated_team_id, 'winner_id': winner, 'winner_name': winner.username if winner else None,
                                           'final_price': nomination.current_bid}, room=str(room_id))


def start_timer(nomination_id, room_id, seconds=30):
    """Start or reset the countdown timer."""
    # Cancel existing timer if present
    if nomination_id in nomination_timers:
        nomination_timers[nomination_id].cancel()

    timer = threading.Timer(seconds, end_nomination, args=[nomination_id, room_id])
    timer.start()
    nomination_timers[nomination_id] = timer

    # Update the DB with the timer end time
    nomination = DraftNomination.query.get(nomination_id)
    nomination.timer_end = datetime.utcnow() + timedelta(seconds=seconds)
    db.session.commit()

    # Broadcast the new timer end to all clients
    socketio.emit('timer_update', {
        'nomination_id': nomination_id,
        'timer_end': nomination.timer_end.isoformat()
    }, room=str(room_id))


# --- HTTP Routes for draft ---
@draft_bp.route('/draft/<int:league_id>')
@login_required
def draft_room(league_id):
    # Get the existing draft room or create one if it doesn't exist
    room = DraftRoom.query.filter_by(league_id=league_id).first()

    if room is None:
        room = DraftRoom(league_id=league_id, status='waiting')
        db.session.add(room)
        db.session.commit()

    participant = DraftParticipant.query.filter_by(draft_room_id=room.id, user_id=current_user.id).first()
    if participant is None:
        participant = DraftParticipant(draft_room_id=room.id, user_id=current_user.id)
        db.session.add(participant)
        db.session.commit()

    active_nomination = DraftNomination.query.filter_by(draft_room_id=room.id, status='active').first()
    current_winner_name = User.query.filter_by(id=active_nomination.current_winner_id).first().name
    nominated_team_name = Football_Teams.query.filter_by(id=active_nomination.nominated_team_id).first().team

    participants = DraftParticipant.query.filter_by(draft_room_id=room.id).all()

    all_player_weekly_info_tables = Player_weekly_info.query.filter_by(league=league_id).all()
    teams_to_remove = []
    for table in all_player_weekly_info_tables:
        team_1_name = table.team_1
        team_2_name = table.team_2
        team_3_name = table.team_3
        team_4_name = table.team_4

        team_1 = Football_Teams.query.filter_by(team=team_1_name).first()
        if team_1 is not None:
            teams_to_remove.append(team_1.id)
        team_2 = Football_Teams.query.filter_by(team=team_2_name).first()
        if team_2 is not None:
            teams_to_remove.append(team_2.id)
        team_3 = Football_Teams.query.filter_by(team=team_3_name).first()
        if team_3 is not None:
            teams_to_remove.append(team_3.id)
        team_4 = Football_Teams.query.filter_by(team=team_4_name).first()
        if team_4 is not None:
            teams_to_remove.append(team_4.id)

    all_football_teams = Football_Teams.query.all()
    available_teams = [{"name": football_team.team, "id": football_team.id} for football_team in all_football_teams if football_team.id not in teams_to_remove]
    available_teams = sorted(available_teams, key=lambda team: team["name"].lower())
    print(f'{available_teams=}')
    print(f'{current_winner_name=}')
    print(f'{nominated_team_name=}')

    return render_template('draft/room.html', room=room, participant=participant, active_nomination=active_nomination, participants=participants, available_teams=available_teams,
                           current_winner_name=current_winner_name, nominated_team_name=nominated_team_name)

# --- SocketIO Events ---
@socketio.on('join_draft')
def on_join(data):
    room_id = data['league_id']
    user_id = current_user.id

    participant = DraftParticipant.query.filter_by(draft_room_id=room_id,user_id=user_id).first()

    if not participant:
        emit('error', {'message': 'You are not a participant in this draft.'})
        return

    join_room(str(room_id))
    participant.is_connected = True
    db.session.commit()

    emit('user_joined', {'user_id': user_id}, room=str(room_id))


@socketio.on('nominate_team')
def on_nominate(data):
    league_id = data['league_id']
    team_id = int(data['team_id'])
    starting_bid = data.get('starting_bid', 1)
    user_id = current_user.id
    print(f'{data=}')

    # Look up the draft room by league_id
    draft_room = DraftRoom.query.filter_by(league_id=league_id).first()
    if not draft_room:
        emit('error', {'message': 'Draft room not found.'})
        return

    room_id = draft_room.id

    # Validate no active nomination exists
    existing = DraftNomination.query.filter_by(draft_room_id=room_id, status='active').first()
    if existing:
        emit('error', {'message': 'A nomination is already in progress.'})
        return

    # Create new nomination
    nomination = DraftNomination(draft_room_id=room_id, nominated_team_id=team_id, nominated_by_user_id=user_id, current_bid=starting_bid, current_winner_id=user_id, status='active')
    db.session.add(nomination)
    db.session.commit()

    start_timer(nomination.id, room_id, seconds=30)

    emit('nomination_started', {'nomination_id': nomination.id, 'team_id': team_id, 'nominated_by': user_id, 'current_bid': starting_bid, 'current_winner': user_id, 'timer_end': nomination.timer_end.isoformat()
    }, room=str(room_id))


@socketio.on('place_bid')
def on_bid(data):
    room_id = data['room_id']
    nomination_id = data['nomination_id']
    bid_amount = int(data['amount'])
    user_id = current_user.id

    nomination = DraftNomination.query.get(nomination_id)
    participant = DraftParticipant.query.filter_by(draft_room_id=room_id, user_id=user_id).first()

    # --- Validation ---
    if not nomination or nomination.status != 'active':
        emit('error', {'message': 'No active nomination.'})
        return
    if bid_amount <= nomination.current_bid:
        emit('error', {'message': f'Bid must be greater than {nomination.current_bid}.'})
        return
    if bid_amount > participant.budget_remaining:
        emit('error', {'message': 'Insufficient budget.'})
        return
    if user_id == nomination.current_winner_id:
        emit('error', {'message': 'You are already the highest bidder.'})
        return

    # Record the bid
    bid = DraftBid(nomination_id=nomination_id, user_id=user_id, amount=bid_amount)
    db.session.add(bid)

    # Update nomination
    nomination.current_bid = bid_amount
    nomination.current_winner_id = user_id
    db.session.commit()

    # Reset timer on new bid
    start_timer(nomination_id, room_id, seconds=15)

    emit('bid_placed', {'nomination_id': nomination_id, 'user_id': user_id, 'amount': bid_amount, 'current_winner': user_id, 'username': current_user.username}, room=str(room_id))

@socketio.on('disconnect')
def on_disconnect():
    user_id = current_user.id
    if user_id:
        participant = DraftParticipant.query.filter_by(user_id=user_id).first()
        if participant:
            participant.is_connected = False
            db.session.commit()

"""
This route shows the dashboard from any given week that the person wants to see. It's the exact same thing as the main
dashboard link except for that it receives the number of the link the person clicked on and uses that as an integer
input to get different standings
"""

@app.route("/MasterDashboard", methods=['GET', 'POST'])
@login_required
def MasterDashboard():
    if current_user.id == 13:
        all_members = User.query.order_by(User.id)
        all_leagues = League.query.order_by(League.id)
        all_league_members = League_members_update1.query.order_by(League_members_update1.id)
        leagues = List_of_leagues_update1.query.filter_by(user_id=current_user.id)
        leagues_list = [(League.query.filter_by(id=item.league).first().league_name, item.league) for item in
                        leagues]
    else:
        flash("I'm not sure how you got here... just go back to your dasbhoard")
        all_members = None
        all_leagues = None
        all_league_members = None
    return render_template("MasterDashboard.html", all_members=all_members, all_leagues=all_leagues,
                           all_league_members=all_league_members, leagues_list=leagues_list)
	
app.register_blueprint(draft_bp)

if __name__ == "__main__":
    app.run(debug=True)
