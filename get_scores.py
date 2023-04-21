from flask import Flask, render_template, request, url_for, redirect, flash, send_from_directory
from flask_wtf import FlaskForm
import pandas
from datetime import date, datetime, timedelta
import my_functions
from wtforms import StringField, SubmitField, PasswordField, BooleanField, ValidationError, EmailField, IntegerField, \
    SelectField
from wtforms.validators import DataRequired, EqualTo, Length, InputRequired
from flask_bootstrap import Bootstrap
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from sqlalchemy import select, delete, update, inspect, create_engine, text
from sqlalchemy.orm import sessionmaker
from flask_migrate import Migrate
import time
# from main import User, League, League_members_update1, List_of_leagues_update1, Player_weekly_info, Football_Teams

test = True
app = Flask(__name__)

app.config['SECRET_KEY'] = 'secret-key-goes-here'
# Heroku SQL
# app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://qylursxvbzavwz:87013a2c4de430e9e802f20f1215996ce267f4bdd5f7f9459881f6461187a718@ec2-3-93-160-246.compute-1.amazonaws.com:5432/dbg16caap1t7nk'
app.config[
    'SQLALCHEMY_DATABASE_URI'] = 'postgresql://jecfvnqncxqxup:af1dd7dc452cacbea264d7aaee8f0c0e3800c97f40524130f22fe27a0f530260@ec2-44-215-22-37.compute-1.amazonaws.com:5432/das2i8qcpbctqg'
engine = create_engine('postgresql://jecfvnqncxqxup:af1dd7dc452cacbea264d7aaee8f0c0e3800c97f40524130f22fe27a0f530260@ec2-44-215-22-37.compute-1.amazonaws.com:5432/das2i8qcpbctqg', echo=False)
Session = sessionmaker(bind=engine)
session = Session()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db, compare_type=True)
Bootstrap(app)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), nullable=False, unique=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(1000), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow())
    league_manager = db.relationship('League', backref='manager', cascade="all, delete-orphan")
    leagues = db.relationship('List_of_leagues_update1', backref='member', cascade="all, delete-orphan")
    player_teams = db.relationship('Player_weekly_info', backref='player_teams', cascade="all, delete-orphan")


class League(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    league_name = db.Column(db.String(100), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow())
    league_manager = db.Column(db.Integer, db.ForeignKey('user.id'))
    league_id_for_list_of_leagues = db.relationship('List_of_leagues_update1', backref='league_id',
                                                    cascade="all, delete-orphan")
    league_members = db.relationship('League_members_update1', backref='members', cascade="all, delete-orphan")
    players_teams = db.relationship('Player_weekly_info', backref='players_teams', cascade="all, delete-orphan")
    league_password = db.Column(db.String(100))
    draft_complete = db.Column(db.Boolean, default=False)
    draft_date = db.Column(db.DateTime, nullable=True)


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

"""
1s represent a win, 0s represent a loss or no game played)
"""

year = 2023
week, postseason = my_functions.determine_week_number()
today = date.today()
now = datetime.now()

if today.weekday() == 6:
    teams_to_update_for_upcoming_games = session.query(Football_Teams).all()
    time_delta = 0
    for result in teams_to_update_for_upcoming_games:
        print(result.team)
        team_to_query = result.team.replace("&", "%26")
        game = my_functions.get_game_data(year=year, week=week, team=team_to_query)
        number_of_games = len(game)
        home_team = game[0]['home_team']
        away_team = game[0]['away_team']
        game_time = game[0]['start_date']
        print(game_time)
        print(type(game_time))
        if team_to_query == home_team:
            upcoming_opponent = away_team
        else:
            upcoming_opponent = home_team
        session.query(Football_Teams).filter_by(team=team_to_query).update({"upcoming_opponent": upcoming_opponent,
            "date_and_time_of_game": game_time})
        time.sleep(2)

    session.commit()

cutoff_for_querying_games = datetime.now()
# teams_to_update = session.query(Football_Teams).filter_by(updated_this_week=False or None).all()
teams_to_update = session.query(Football_Teams).all()
print(len(teams_to_update))
print(teams_to_update)
for result in teams_to_update:
    print(result.team)
    if cutoff_for_querying_games < now:
        print(cutoff_for_querying_games)
        print(now)
        team_to_query = result.team.replace("&", "%26")
        game = my_functions.get_game_data(year=year, week=week, team=team_to_query)
        print(game)
        try:
            home_team = game[0]['home_team']
            away_team = game[0]['away_team']
            home_score = game[0]['home_points']
            away_score = game[0]['away_points']
            if home_score > away_score:
                winning_team = home_team.replace("%26", "&")
                losing_team = away_team.replace("%26", "&")
            elif away_score > home_score:
                winning_team = away_team.replace("%26", "&")
                losing_team = home_team.replace("%26", "&")

            session.query(Football_Teams).filter(Football_Teams.team == home_team).update({"current_score": home_score})
            session.query(Football_Teams).filter(Football_Teams.team == away_team).update({"current_score": away_score})

            # Update the week's score and updated_this_week variables for both teams if the game is over
            if game[0]['completed'] == True:
                session.query(Football_Teams).filter(Football_Teams.team == winning_team).update(
                    {f"week{week}_score": 1, "updated_this_week": True, "playing_now": False})
                session.query(Football_Teams).filter(Football_Teams.team == losing_team).update(
                    {f"week{week}_score": 0, "updated_this_week": True, "playing_now": False})

        except IndexError:
            # If IndexError, then the team doesn't have a game so assign it 0 and mark it as updated. It needs to be
            # Saturday before updating so someone can still drop this team and add another one
            if today.weekday() == 5:
                session.query(Football_Teams).filter(Football_Teams.team == team_to_query.replace("%26", "&")).update(
                    {f"week{week}_score": 0, "updated_this_week": True})

    time.sleep(2)
session.commit()

new_results = session.query(Football_Teams).all()
for result in new_results:
    print(result.week2_score)

scores_2022 = {"Clemson": 11, "Florida State": 10, "Syracuse": 7, "Louisville": 8, "NC State": 8, "Wake Forest": 8,
               "Boston College": 3, "North Carolina": 9, "Pittsburgh": 9, "Duke": 9, "Georgia Tech": 5, "Miami": 5,
               "Virginia": 3, "Virginia Tech": 3, "TCU": 12, "Kansas State": 10, "Texas": 8, "Texas Tech": 9,
               "Oklahoma State": 7, "Baylor": 6, "Oklahoma": 6, "Kansas": 6, "West Virginia": 5, "Iowa State": 4,
               "Michigan": 13, "Ohio State": 11, "Penn State": 11, "Maryland": 8, "Michigan State": 5, "Indiana": 4,
               "Rutgers": 4, "Purdue": 8, "Illinois": 8, "Iowa": 8, "Minnesota": 9, "Wisconsin": 7, "Nebraska": 4,
               "Northwestern": 1, "Notre Dame": 9, "BYU": 8, "UCF": 9, "Cincinnati": 9, "Houston": 8, "USC": 11,
               "Washington": 11, "Oregon": 10, "Utah": 10, "Oregon State": 10, "UCLA": 9, "Washington State": 7,
               "Arizona": 5, "California": 4, "Arizona State": 3, "Stanford": 3, "Colorado": 1, "Georgia": 13,
               "Tennessee": 11, "South Carolina": 8, "Kentucky": 7, "Florida": 6, "Missouri": 6, "Vanderbilt": 5,
               "LSU": 10,
               "Alabama": 11, "Mississippi State": 9, "Ole Miss": 8, "Arkansas": 7, "Auburn": 5, "Texas A&M": 5}

conferences_2023 = {"Clemson": "ACC", "Florida State": "ACC", "Syracuse": "ACC", "Louisville": "ACC",
                        "NC State": "ACC", "Wake Forest": "ACC",
                        "Boston College": "ACC", "North Carolina": "ACC", "Pittsburgh": "ACC", "Duke": "ACC",
                        "Georgia Tech": "ACC", "Miami": "ACC",
                        "Virginia": "ACC", "Virginia Tech": "ACC", "TCU": "Big 12", "Kansas State": "Big 12",
                        "Texas": "Big 12", "Texas Tech": "Big 12",
                        "Oklahoma State": "Big 12", "Baylor": "Big 12", "Oklahoma": "Big 12", "Kansas": "Big 12",
                        "West Virginia": "Big 12", "Iowa State": "Big 12",
                        "Michigan": "Big 10", "Ohio State": "Big 10", "Penn State": "Big 10", "Maryland": "Big 10",
                        "Michigan State": "Big 10", "Indiana": "Big 10",
                        "Rutgers": "Big 10", "Purdue": "Big 10", "Illinois": "Big 10", "Iowa": "Big 10",
                        "Minnesota": "Big 10", "Wisconsin": "Big 10", "Nebraska": "Big 10",
                        "Northwestern": "Big 10", "Notre Dame": "Independent", "BYU": "Big 12", "UCF": "Big 12",
                        "Cincinnati": "Big 12", "Houston": "Big 12", "USC": "PAC 12",
                        "Washington": "PAC 12", "Oregon": "PAC 12", "Utah": "PAC 12", "Oregon State": "PAC 12",
                        "UCLA": "PAC 12", "Washington State": "PAC 12",
                        "Arizona": "PAC 12", "California": "PAC 12", "Arizona State": "PAC 12", "Stanford": "PAC 12",
                        "Colorado": "PAC 12", "Georgia": "SEC",
                        "Tennessee": "SEC", "South Carolina": "SEC", "Kentucky": "SEC", "Florida": "SEC",
                        "Missouri": "SEC", "Vanderbilt": "SEC",
                        "LSU": "SEC", "Alabama": "SEC", "Mississippi State": "SEC", "Ole Miss": "SEC",
                        "Arkansas": "SEC", "Auburn": "SEC", "Texas A&M": "SEC"}

    # for every_team in all_teams:
    #     print(every_team.id)
    #     db.session.query(Football_Teams).filter(Football_Teams.id == every_team.id).update(
    #         {"conference": conferences_2023[every_team.team]})
    #     print(f"{every_team.team} is in {every_team.conference}")
    # db.session.commit()



