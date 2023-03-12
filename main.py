from flask import Flask, render_template, request, url_for, redirect, flash, send_from_directory
from flask_wtf import FlaskForm
import pandas
import datetime
import my_functions
from wtforms import StringField, SubmitField, PasswordField, BooleanField, ValidationError, EmailField
from wtforms.validators import DataRequired, EqualTo, Length, InputRequired
from flask_bootstrap import Bootstrap
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
import pymysql
from flask_migrate import Migrate
pymysql.install_as_MySQLdb()

test = True
app = Flask(__name__)

app.config['SECRET_KEY'] = 'secret-key-goes-here'
# Old SQLite DB
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
# New
# app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://username:password@localhost/db_name'
if test:
    import no_push
    app.config['SQLALCHEMY_DATABASE_URI'] = no_push.my_sql_config
# Heroku SQL
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://qylursxvbzavwz:87013a2c4de430e9e802f20f1215996ce267f4bdd5f7f9459881f6461187a718@ec2-3-93-160-246.compute-1.amazonaws.com:5432/dbg16caap1t7nk'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)
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

class UserForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    username = StringField("Username", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired()])
    password_hash = PasswordField("Password", validators=[DataRequired(), EqualTo('password_hash2', message='Passwords must match')])
    password_hash2 = PasswordField("Confirm Password", validators=[DataRequired()])
    submit = SubmitField("Submit")

class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Submit")

with app.app_context():
    db.create_all()

"""
This loop replaces all teams that have an '&' in their name to '%26' because the API won't find it if an '&' is passed
in. Teams_dict is then made to pass into the save_to_spreadsheet function. A dictionary is made so it can be saved to a
csv with a list of 0s and 1s (1s representing a win, 0s representing a loss or no game played)
"""

new_teams = []
with open("Teams.txt", encoding='ISO-8859-1') as file:
    text = file.read()
    teams = text.split(",")
    for team in teams:
        new_team = team.replace("&", "%26")
        new_teams.append(new_team)

teams_dict = {team: [] for team in teams}


if get_upcoming_games:
    my_functions.upcoming_games_master(teams_dict=teams_dict, year=year)
data = pandas.read_csv("This_weeks_games.csv", encoding='latin-1')
team_games = data.to_dict()
final_team_games = my_functions.convert_dict_to_simple_dict(team_games)

if get_data:
    my_functions.save_data(league_number=1, new_teams=new_teams, year=year, teams_dict=teams_dict)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/login", methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            if check_password_hash(user.password_hash, form.password.data):
                login_user(user)
                flash("Login Successful!")
                return render_template('success.html')
                # return render_template('Dashboard.html/league=1')
                # return redirect(url_for('dashboard'))
            else:
                flash("That login combination is incorrect")
                return render_template("denied.html")
        else:
            flash("That user doesn't exist!")
            print(f'{form.email.data} user doesnt exist')
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

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None:
            salted_and_hashed_pw = generate_password_hash(form.password_hash.data, method="pbkdf2:sha256", salt_length=8)
            user = User(name=form.name.data, email=form.email.data, password_hash=salted_and_hashed_pw,
                        username=form.username.data)
            db.session.add(user)
            db.session.commit()
        name = form.name.data
        form.name.data = ''
        form.email.data = ''
        form.password_hash.data = ''
        form.username.data = ''
        flash("User Added Successfully!")
    our_users = User.query.order_by(User.date_added)
    return render_template("add_user.html", form=form, name=name, our_users=our_users)

@app.route('/update/<int:id>', methods=['GET', 'POST'])
def update(id):
    form = UserForm()
    name_to_update = User.query.get(id)
    if request.method == "POST":
        name_to_update.name = request.form['name']
        name_to_update.email = request.form['email']
        name_to_update.password_hash = request.form['password']
        name_to_update.username = request.form['username']
        try:
            db.session.commit()
            flash("User Updated Successfully!")
            return render_template("update.html", form=form, name_to_update=name_to_update)
        except:
            db.session.commit()
            flash("Error!")
            return render_template("update.html", form=form, name_to_update=name_to_update)
    else:
        flash("Error!")
        return render_template("update.html", form=form, name_to_update=name_to_update, id=id)

@app.route('/delete/<int:id>', methods=['GET', 'POST'])
def delete(id):
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

# Invalid URL
@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404

# Server Error
@app.errorhandler(500)
def page_not_found(e):
    return render_template("500.html"), 500

"""
This route will be the main link to see a person's dashboard. It will automatically show the standings for the current
week. It will have a link to display the weeks for someone to choose so they can see the standings from any given week
"""


@app.route("/Dashboard/league=<league_number>")
# @login_required
def dashboard(league_number):
    data = pandas.read_csv("Team_points.csv", encoding='latin-1')

    with open("Teams.txt", encoding='ISO-8859-1') as file:
        text = file.read()
        teams = text.split(",")

    "Determine current week and previous week to calculate standings and previous standings"
    week = my_functions.determine_week_number()
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
	for the current weak for the teams but not the people. Then a new dictionary is made that has multiple dictionaries
	for each team (rank, points, last result, player, and conference)
	"""
    current_week_score_dict = dict(
        sorted(my_functions.determine_scores(points_dict=current_week_points_dict, league_number=league_number).items(),
               key=lambda kv: kv[1], reverse=True))
    previous_week_score_dict = dict(
        sorted(my_functions.determine_scores(points_dict=previous_week_points_dict, league_number=league_number).items(),
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
    return render_template("Dashboard.html", week_num=week, display_num=week, score_dict=current_week_score_dict,
                           places=places, previous_score_dict=previous_week_score_dict, previous_places=previous_places,
                           team_data_dict=team_data_dict, player_teams_final=player_teams_final,
                           upcoming_team_games=upcoming_team_games, league_number=league_number)


"""
This route shows the dashboard from any given week that the person wants to see. It's the exact same thing as the main
dashboard link except for that it receives the number of the link the person clicked on and uses that as an integer
input to get different standings
"""


@app.route("/Dashboard/league=<league_number>&week=<number_from_website>")
def get_standings(league_number, number_from_website):
    team_data = pandas.read_csv("Team_points.csv", encoding='latin-1')

    with open("Teams.txt", encoding='ISO-8859-1') as file:
        text = file.read()
        teams = text.split(",")

    "Determine current week and previous week to calculate standings and previous standings"
    week = my_functions.determine_week_number()
    week_number = int(number_from_website)
    if week_number == 1:
        previous_week = 1
    else:
        previous_week = week_number - 1

    """
	Converts csv data to dictionary and loops through every team (both for the current week and the new week) to get
	everyone's total. It loops through every team and determines their score on the given week and saves it to a
	dictionary (current_week_points_dict and previous_week_points_dict). It will also get data for team standings here
	by generating a dictionary (team_score_dict) that has the point totals for every team that week
	"""
    points_dict = team_data.to_dict()
    current_week_points_dict = {}
    previous_week_points_dict = {}
    team_score_dict = {}

    for team in teams:
        i = 0
        points = 0
        while i < week_number:
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
	for the current weak for the teams but not the people. Then a new dictionary is made that has multiple dictionaries
	for each team (rank, points, last result, player, and conference)
	"""
    current_week_score_dict = dict(
        sorted(my_functions.determine_scores(points_dict=current_week_points_dict, league_number=league_number).items(),
               key=lambda kv: kv[1], reverse=True))
    previous_week_score_dict = dict(
        sorted(my_functions.determine_scores(points_dict=previous_week_points_dict, league_number=league_number).items(),
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
    del player_teams_initial["Unnamed: 0"]
    player_teams_final = {}
    for person in player_teams_initial:
        list = []
        for i in range(0, 4):
            team = player_teams_initial[person][i]
            list.append(team)
        player_teams_final[person] = list

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
	previous_game_dict is used to show the team's last game (and result).
	team_data_dict is used to pass: a team's score, a team's last result, and what conference that team is in.
	player_teams_final passes in what player owns the team (passes a blank result if unowned).
	"""
    return render_template("Dashboard.html", week_num=week, display_num=week_number, score_dict=current_week_score_dict,
                           places=places, previous_score_dict=previous_week_score_dict, previous_places=previous_places,
                           team_data_dict=team_data_dict, player_teams_final=player_teams_final,
                           upcoming_team_games=upcoming_team_games, league_number=league_number)


if __name__ == "__main__":
    app.run(debug=True)
