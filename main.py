from flask import Flask, render_template, request, url_for, redirect, flash, send_from_directory
from flask_wtf import FlaskForm
import pandas
import datetime
from datetime import date
import my_functions
from wtforms import StringField, SubmitField, PasswordField, BooleanField, ValidationError, EmailField, IntegerField, \
    SelectField
from wtforms.validators import DataRequired, EqualTo, Length, InputRequired
from flask_bootstrap import Bootstrap
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.test import create_environ
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from sqlalchemy import select, delete, update, inspect
from flask_migrate import Migrate
import time

test = True
app = Flask(__name__)

app.config['SECRET_KEY'] = 'secret-key-goes-here'
# Old SQLite DB
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
# New
# app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://username:password@localhost/db_name'
# if test:
#     import no_push
#     app.config['SQLALCHEMY_DATABASE_URI'] = no_push.my_sql_config
# Heroku SQL
# app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://qylursxvbzavwz:87013a2c4de430e9e802f20f1215996ce267f4bdd5f7f9459881f6461187a718@ec2-3-93-160-246.compute-1.amazonaws.com:5432/dbg16caap1t7nk'
app.config[
    'SQLALCHEMY_DATABASE_URI'] = 'postgresql://jecfvnqncxqxup:af1dd7dc452cacbea264d7aaee8f0c0e3800c97f40524130f22fe27a0f530260@ec2-44-215-22-37.compute-1.amazonaws.com:5432/das2i8qcpbctqg'
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
    date_added = db.Column(db.DateTime, default=datetime.datetime.utcnow())
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
    date_created = db.Column(db.DateTime, default=datetime.datetime.utcnow())
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
    previous_weeks_score = db.Column(db.Integer, default=0)
    this_weeks_score = db.Column(db.Integer, default=0)
    team_1 = db.Column(db.String(100), nullable=True, default=None)
    team_2 = db.Column(db.String(100), nullable=True, default=None)
    team_3 = db.Column(db.String(100), nullable=True, default=None)
    team_4 = db.Column(db.String(100), nullable=True, default=None)


class Football_Teams(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team = db.Column(db.String(100), nullable=True)
    updated_this_week = db.Column(db.Boolean, default=False)
    playing_now = db.Column(db.Boolean, default=False)
    upcoming_opponent = db.Column(db.String(100), nullable=True)
    previous_opponent = db.Column(db.String(100), nullable=True, default="")
    previous_result = db.Column(db.String(1), nullable=True, default="")
    date_and_time_of_game = db.Column(db.DateTime)
    current_score = db.Column(db.Integer, default=0)
    conference = db.Column(db.String(30), nullable=True)
    week0_score = db.Column(db.Integer)
    week1_score = db.Column(db.Integer)
    week2_score = db.Column(db.Integer)
    week3_score = db.Column(db.Integer)
    week4_score = db.Column(db.Integer)
    week5_score = db.Column(db.Integer)
    week6_score = db.Column(db.Integer)
    week7_score = db.Column(db.Integer)
    week8_score = db.Column(db.Integer)
    week9_score = db.Column(db.Integer)
    week10_score = db.Column(db.Integer)
    week11_score = db.Column(db.Integer)
    week12_score = db.Column(db.Integer)
    week13_score = db.Column(db.Integer)
    week14_score = db.Column(db.Integer)
    week15_score = db.Column(db.Integer)
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
    date_and_time_added = db.Column(db.DateTime, default=datetime.datetime.utcnow())


class HistoryOfWaivers(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    league = db.Column(db.Integer, db.ForeignKey('league.id'))
    team_to_add_id = db.Column(db.Integer, nullable=False)
    team_to_drop_id = db.Column(db.Integer, nullable=False)
    faab_submitted = db.Column(db.Integer, nullable=False)
    priority = db.Column(db.Integer, nullable=False)


class Analysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    num_of_visits = db.Column(db.Integer)
    league = db.Column(db.Integer, nullable=True)
    endpoint = db.Column(db.String(100))


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
    if current_user.id != 13:
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
    try:
        league_scores_with_names = sorted([(User.query.filter_by(id=member.user_id).first().name, member.this_weeks_score,
                                    member.previous_weeks_score, Football_Teams.query.filter_by(id=member.team_1).first().team,
                                    Football_Teams.query.filter_by(id=member.team_2).first().team,
                                    Football_Teams.query.filter_by(id=member.team_3).first().team,
                                    Football_Teams.query.filter_by(id=member.team_4).first().team,
                                    Player_weekly_info.query.filter_by(user_id=member.user_id).filter_by(league=league_id).first().faab)
                                    for member in league_members_weekly_info], key=lambda kv: kv[1], reverse=True)
        print(league_scores_with_names)
    except AttributeError:
        league_scores_with_names = []

    league_member_ids = [User.query.filter_by(id=member.member).first().id for member in league_members
                           if member.league_id == league_id]
    week, postseason = my_functions.determine_week_number()

    # Gets all teams that the user can't pickup due to being owned by the user or another user
    ineligible_teams = []
    try:
        for member in league_member_ids:
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
    time_correction_delta = datetime.timedelta(hours=5)
    all_teams = Football_Teams.query.order_by(Football_Teams.id)
    eligible_teams_dict = {}
    user_teams_dict = {}
    for team in all_teams:
        if team.team not in ineligible_teams:
            if team.date_and_time_of_game is not None:
                eligible_teams_dict[team.team] = [team.current_score, team.conference, team.upcoming_opponent, team.previous_opponent,
                                       team.previous_result, datetime.datetime.strftime(team.date_and_time_of_game - time_correction_delta, "%a %I:%M%p")]
            else:
                eligible_teams_dict[team.team] = [team.current_score, team.conference, team.upcoming_opponent, team.previous_opponent,
                                                  team.previous_result, "no game"]
        if team.team in user_teams:
            if team.date_and_time_of_game is not None:
                user_teams_dict[team.team] = [team.current_score, team.conference, team.upcoming_opponent, team.previous_opponent,
                               team.previous_result, datetime.datetime.strftime(team.date_and_time_of_game - time_correction_delta, "%a %I:%M%p")]
            else:
                user_teams_dict[team.team] = [team.current_score, team.conference, team.upcoming_opponent, team.previous_opponent,
                                              team.previous_result, "no game"]
    # eligible_teams_dict = {team.team: [team.current_score, team.conference, team.upcoming_opponent, team.previous_opponent,
    #                                    team.previous_result, datetime.datetime.strftime(team.date_and_time_of_game - time_correction_delta, "%a %I:%M%p")] for team in all_teams if team.team not in ineligible_teams}
    # user_teams_dict = {team.team: [team.current_score, team.conference, team.upcoming_opponent, team.previous_opponent,
    #                                team.previous_result, datetime.datetime.strftime(team.date_and_time_of_game - time_correction_delta, "%a %I:%M%p")] for team in all_teams if team.team in user_teams}
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
    your_waiver_history_list = [(waiver.id, Football_Teams.query.filter_by(id=waiver.team_to_add_id).first().team, Football_Teams.query.filter_by(id=waiver.team_to_drop_id).first().team, waiver.faab_submitted, waiver.priority) for waiver in your_waiver_history]

    # Determines if it's time for playoffs. If it is, allow the top 4 people to preference which playoff representative they want
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
        ineligible_teams.append(Football_Teams.query.filter_by(
            id=int(Player_weekly_info.query.filter_by(league=league_id, user_id=member).first().team_1)).first().team)
        ineligible_teams.append(Football_Teams.query.filter_by(
            id=int(Player_weekly_info.query.filter_by(league=league_id, user_id=member).first().team_2)).first().team)
        ineligible_teams.append(Football_Teams.query.filter_by(
            id=int(Player_weekly_info.query.filter_by(league=league_id, user_id=member).first().team_3)).first().team)
        ineligible_teams.append(Football_Teams.query.filter_by(
                id=int(Player_weekly_info.query.filter_by(league=league_id, user_id=member).first().team_4)).first().team)

    # Displays the user's current teams that they can choose to drop from
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
    eligible_teams_dict = {team.team: [team.current_score, team.conference, team.id, team.date_and_time_of_game - datetime.timedelta(hours=5)] for team in all_teams if
                           team.team not in ineligible_teams}
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

    leagues = List_of_leagues_update1.query.filter_by(user_id=current_user.id)
    leagues_list = [(League.query.filter_by(id=item.league).first().league_name, item.league) for item in
                    leagues]
    now = datetime.datetime.now()

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
    now = datetime.datetime.now()
    if team_to_add.date_and_time_of_game > datetime.datetime.utcnow():
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
        user_teams_dict = {team.team: [team.current_score, team.conference, team.id] for team in all_teams if
                           team.team in user_teams}
        try:
            user_teams_dict_sorted = dict(sorted(user_teams_dict.items(), key=lambda kv: kv[1], reverse=True))
        except TypeError:
            user_teams_dict_sorted = user_teams_dict

        current_user_teams = list(user_teams_dict_sorted.keys())
        league_name = League.query.filter_by(id=league_id).first().league_name

        leagues = List_of_leagues_update1.query.filter_by(user_id=current_user.id)
        leagues_list = [(League.query.filter_by(id=item.league).first().league_name, item.league) for item in
                        leagues]

        return render_template("drop_team.html", league_members=league_members, league_id=league_id,
                               current_user_teams=current_user_teams, user_teams_dict_sorted=user_teams_dict_sorted,
                               league_name=league_name, team_to_add_list=team_to_add_list, leagues_list=leagues_list)
    else:
        flash("Page reloaded due to trying to add a team that is now on waivers")
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
            ineligible_teams.append(Football_Teams.query.filter_by(
                id=int(
                    Player_weekly_info.query.filter_by(league=league_id, user_id=member).first().team_1)).first().team)
            ineligible_teams.append(Football_Teams.query.filter_by(
                id=int(
                    Player_weekly_info.query.filter_by(league=league_id, user_id=member).first().team_2)).first().team)
            ineligible_teams.append(Football_Teams.query.filter_by(
                id=int(
                    Player_weekly_info.query.filter_by(league=league_id, user_id=member).first().team_3)).first().team)
            ineligible_teams.append(Football_Teams.query.filter_by(
                id=int(
                    Player_weekly_info.query.filter_by(league=league_id, user_id=member).first().team_4)).first().team)

        # Displays the user's current teams that they can choose to drop from
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
        eligible_teams_dict = {team.team: [team.current_score, team.conference, team.id, team.date_and_time_of_game] for
                               team in all_teams if
                               team.team not in ineligible_teams}
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

        leagues = List_of_leagues_update1.query.filter_by(user_id=current_user.id)
        leagues_list = [(League.query.filter_by(id=item.league).first().league_name, item.league) for item in
                        leagues]
        now = datetime.datetime.now()

        return render_template("add_team.html", league_members=league_members, league_id=league_id,
                               eligible_teams=eligible_teams, current_user_teams=current_user_teams,
                               eligible_teams_dict_sorted=eligible_teams_dict_sorted,
                               user_teams_dict_sorted=user_teams_dict_sorted, league_name=league_name,
                               leagues_list=leagues_list,
                               already_updated=already_updated, now=now)

@app.route("/confirm_drop/league=<int:league_id>/drop_team=<int:dropteam_id>/add_team=<int:addteam_id>", methods=['GET', 'POST'])
@login_required
def confirm_drop(league_id, dropteam_id, addteam_id):
    if addteam_id.date_and_time_of_game < datetime.datetime.utcnow() + datetime.timedelta(hours=5):
        already_updated = League.query.filter_by(id=league_id).first().waivers_already_executed
        if already_updated:
            form = AlreadyUpdatedDropComplete()
        else:
            form = DropComplete()
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

            if not already_updated:
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
                                                           dropped_team=team_to_drop, faab_used=0, date_and_time_added=datetime.datetime.now())
                db.session.add(executed_waiver)
                db.session.commit()
                return redirect(url_for('league_dashboard', league_id=league_id, leagues_list=leagues_list))

        elif already_updated:
            return render_template("confirm_drop.html", form=form, league_id=league_id, league_name=league_name,
                                   team_to_add_list=team_to_add_list, team_to_drop_list=team_to_drop_list,
                                   available_faab=user_faab, leagues_list=leagues_list, already_updated=already_updated)

        else:
            flash("You don't have enough Faab to make that waiver request. Please update the faab!")
            return render_template("confirm_drop.html", form=form, league_id=league_id, league_name=league_name,
                                   team_to_add_list=team_to_add_list, team_to_drop_list=team_to_drop_list,
                                   available_faab=user_faab, leagues_list=leagues_list, already_updated=already_updated)

        return render_template("confirm_drop.html", form=form, league_id=league_id, league_name=league_name,
                               team_to_add_list=team_to_add_list, team_to_drop_list=team_to_drop_list,
                               available_faab=user_faab, leagues_list=leagues_list, already_updated=already_updated)
    else:
        flash("Page reloaded due to trying to add a team that is now on waivers")
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
            ineligible_teams.append(Football_Teams.query.filter_by(
                id=int(
                    Player_weekly_info.query.filter_by(league=league_id, user_id=member).first().team_1)).first().team)
            ineligible_teams.append(Football_Teams.query.filter_by(
                id=int(
                    Player_weekly_info.query.filter_by(league=league_id, user_id=member).first().team_2)).first().team)
            ineligible_teams.append(Football_Teams.query.filter_by(
                id=int(
                    Player_weekly_info.query.filter_by(league=league_id, user_id=member).first().team_3)).first().team)
            ineligible_teams.append(Football_Teams.query.filter_by(
                id=int(
                    Player_weekly_info.query.filter_by(league=league_id, user_id=member).first().team_4)).first().team)

        # Displays the user's current teams that they can choose to drop from
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
        eligible_teams_dict = {team.team: [team.current_score, team.conference, team.id, team.date_and_time_of_game] for
                               team in all_teams if
                               team.team not in ineligible_teams}
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

        leagues = List_of_leagues_update1.query.filter_by(user_id=current_user.id)
        leagues_list = [(League.query.filter_by(id=item.league).first().league_name, item.league) for item in
                        leagues]
        now = datetime.datetime.now()

        return render_template("add_team.html", league_members=league_members, league_id=league_id,
                               eligible_teams=eligible_teams, current_user_teams=current_user_teams,
                               eligible_teams_dict_sorted=eligible_teams_dict_sorted,
                               user_teams_dict_sorted=user_teams_dict_sorted, league_name=league_name,
                               leagues_list=leagues_list,
                               already_updated=already_updated, now=now)

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

    else:
        flash("You must be the league manager to perform this operation!")
        return redirect(url_for('league_dashboard', league_id=league_id, leagues_list=leagues_list))

    return render_template("league_setup.html", league_members=league_members, league_id=league_id,
                           league_member_names=league_member_names, league_manager=league_manager,
                           users_to_update=users_to_update, league_name=league_name, form=form,
                           eligible_teams=eligible_teams, updated_users_with_teams=updated_users_with_teams,
                           leagues_list=leagues_list)


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

    for team in teams:
        i = 0
        points = 0
        while i < week:
            points += points_dict[team][i]
            i += 1

        i = 0
        previous_points = 0
        while i < previous_week:
            previous_points += points_dict[team][i]
            i += 1

        current_week_points_dict[team] = points
        previous_week_points_dict[team] = previous_points
        team_score_dict[team] = points

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

    for team in teams:
        team = team.replace("&", "%26")
        with open(f"Team_Results/{team}.txt", 'r', encoding='ISO-8859-1') as file:
            text = file.read()
            games_list = text.split(',')
            previous_game = games_list[-2]
            team_data_dict[team.replace("%26", "&")]["last_result"] = previous_game

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
                           team_data_dict=team_data_dict, player_teams_final=player_teams_final,
                           upcoming_team_games=upcoming_team_games, league_number=league_number,
                           user_leagues=user_list_of_leagues,
                           user_list_of_league_members=user_list_of_league_members,
                           league_managers_dict=league_managers_dict, leagues_list=leagues_list)


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

if __name__ == "__main__":
    app.run(debug=True)
