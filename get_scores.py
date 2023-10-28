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

scores_test = False
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
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_account = db.Column(db.Boolean, default=False)
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


class Executed_Waivers_update1(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    league = db.Column(db.Integer, db.ForeignKey('league.id'))
    added_team = db.Column(db.Integer, nullable=False)
    dropped_team = db.Column(db.Integer, nullable=False)
    faab_used = db.Column(db.Integer, nullable=False)
    date_and_time_added = db.Column(db.DateTime, default=datetime.utcnow())


class Waiver_Info(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    league = db.Column(db.Integer, db.ForeignKey('league.id'))
    team_to_add_id = db.Column(db.Integer, nullable=False)
    team_to_drop_id = db.Column(db.Integer, nullable=False)
    faab_submitted = db.Column(db.Integer, nullable=False)
    priority = db.Column(db.Integer, nullable=False)


"""
1s represent a win, 0s represent a loss or no game played
"""

year = 2023
week, postseason = my_functions.determine_week_number()
# week = 5
print(f"week: {week}")
today = date.today()
now = datetime.now()
print(now)
week_01_cutoff = datetime(2023, 8, 30)

# time_delta is the value used to determine how far in the future to query games
# time_correction is to go from central time to gmt
time_correction = 5
time_delta = timedelta(hours=0 + time_correction)
time_correction_delta = timedelta(hours=5)

def get_upcoming_games():
    all_teams = session.query(Football_Teams).all()
    for item in all_teams:
        print(item.team)
        team_to_query = item.team.replace("&", "%26")
        game = my_functions.get_game_data(year=year, week=week, team=team_to_query)
        team_to_query = team_to_query.replace("%26", "&")
        number_of_games = len(game)
        if number_of_games > 1 and datetime.now() > datetime.combine(date(2023, 8, 28), datetime.min.time()):
            home_team = game[1]['home_team']
            away_team = game[1]['away_team']
            game_time = game[1]['start_date']
            print(game_time)
            if team_to_query == home_team:
                upcoming_opponent = away_team
            else:
                upcoming_opponent = home_team
        else:
            try:
                home_team = game[0]['home_team']
                away_team = game[0]['away_team']
                game_time = game[0]['start_date']
                print(game_time)
                if team_to_query == home_team:
                    upcoming_opponent = away_team
                else:
                    upcoming_opponent = home_team
            # IndexError occurs when a team is on a Bye since the returned result is None
            except IndexError:
                upcoming_opponent = "BYE"
                game_time = datetime.utcnow() + timedelta(days=10)

        session.query(Football_Teams).filter_by(team=team_to_query).update({"upcoming_opponent": upcoming_opponent,
            "date_and_time_of_game": game_time, "updated_this_week": False})
        time.sleep(2)

        session.commit()


def get_scores():

    for item in teams_to_update:
        print(item.team)
        try:
            if cutoff_for_querying_games > item.date_and_time_of_game or scores_test is True:
                team_to_query = item.team.replace("&", "%26")
                game = my_functions.get_game_data(year=year, week=week, team=team_to_query)
                print(game)

                # Get scores of all games that are currently going on if they should be currently playing or playing soon
                try:
                    if week == 1 and datetime.now() > week_01_cutoff:
                        if len(game) > 1:
                            home_team = game[1]['home_team']
                            away_team = game[1]['away_team']
                            home_score = game[1]['home_points']
                            away_score = game[1]['away_points']
                            game_completed = game[1]['completed']
                        else:
                            home_team = game[0]['home_team']
                            away_team = game[0]['away_team']
                            home_score = game[0]['home_points']
                            away_score = game[0]['away_points']
                            game_completed = game[0]['completed']
                    else:
                        home_team = game[0]['home_team']
                        away_team = game[0]['away_team']
                        home_score = game[0]['home_points']
                        away_score = game[0]['away_points']
                        game_completed = game[0]['completed']
                    try:
                        print(f"home_score: {home_score}")
                        print(f"away_score: {away_score}")
                        if home_score > away_score:
                            winning_team = home_team.replace("%26", "&")
                            print(f"winning_team: {winning_team}")
                            losing_team = away_team.replace("%26", "&")
                        elif away_score > home_score:
                            winning_team = away_team.replace("%26", "&")
                            print(f"winning_team: {winning_team}")
                            losing_team = home_team.replace("%26", "&")
                        session.query(Football_Teams).filter(Football_Teams.team == home_team).update(
                            {"playing_now": True})
                        session.query(Football_Teams).filter(Football_Teams.team == away_team).update(
                            {"playing_now": True})

                    # TypeError is due to there not being a score yet, so operand is not supported for NoneType
                    except TypeError:
                        pass

                    # Update the week's score and updated_this_week variables for both teams if the game is over if team
                    # hasn't been updated (it'll update twice if an eligibile team is playing another eligible team
                    if game_completed == True:
                        if session.query(Football_Teams).filter(Football_Teams.team == item.team).first().updated_this_week == False:
                            if item.team == winning_team:
                                print(f"{item.team} won. New score +1")
                                new_score = session.query(Football_Teams).filter(Football_Teams.team == winning_team).first().current_score + 1
                                session.query(Football_Teams).filter(Football_Teams.team == winning_team).update(
                                    {f"week{week}_score": 1, "updated_this_week": True, "playing_now": False, "current_score": new_score, "previous_opponent": losing_team, "previous_result": "W"})
                            elif item.team == losing_team:
                                print(f"{item.team} lost. No new score")
                                session.query(Football_Teams).filter(Football_Teams.team == losing_team).update(
                                    {f"week{week}_score": 0, "updated_this_week": True, "playing_now": False, "previous_opponent": winning_team, "previous_result": "L"})
                            else:
                                print("weird else entered")

                            # Add to the log that the team was updated
                            with open(f"log.txt", mode="a") as file:
                                text = f"Week {week}: {item.team} updated \n"
                                file.write(text)

                            # Add a point to every person's score by figuring out if they have the team by querying every team they have
                            # and adding 1 after that if they do
                            all_player_weekly_info = session.query(Player_weekly_info).order_by(Player_weekly_info.id)
                            for info in all_player_weekly_info:
                                user = session.query(User).filter(User.id == info.user_id).first()
                                user_name = user.name
                                league = session.query(League).filter(League.id == info.league).first()
                                team_1 = " "
                                team_2 = " "
                                team_3 = " "
                                team_4 = " "
                                try:
                                    team_2 = session.query(Football_Teams).filter(info.team_2 == Football_Teams.id).first().team
                                    team_3 = session.query(Football_Teams).filter(info.team_3 == Football_Teams.id).first().team
                                    team_4 = session.query(Football_Teams).filter(info.team_4 == Football_Teams.id).first().team
                                    team_1 = session.query(Football_Teams).filter(info.team_1 == Football_Teams.id).first().team
                                # AttributeError will occur for every league that doesn't have teams assigned
                                except AttributeError:
                                    pass
                                if team_1 == winning_team and team_1 == item.team:
                                    new_player_score = session.query(Player_weekly_info).filter(
                                        Player_weekly_info.id == info.id).first().this_weeks_score + 1
                                    session.query(Player_weekly_info).filter(Player_weekly_info.id == info.id).update(
                                        {"this_weeks_score": new_player_score})
                                    print(f"{user_name} +1 from team_1")
                                    print(f"winning_team: {winning_team}")
                                    print(f"losing_team: {losing_team}")
                                    print(f"team_1: {team_1}")
                                    print(f"league: {league}")
                                    print(" ")
                                elif team_2 == winning_team and team_2 == item.team:
                                    new_player_score = session.query(Player_weekly_info).filter(
                                        Player_weekly_info.id == info.id).first().this_weeks_score + 1
                                    session.query(Player_weekly_info).filter(Player_weekly_info.id == info.id).update(
                                        {"this_weeks_score": new_player_score})
                                    print(f"{user_name} +1 from team_2")
                                    print(f"winning_team: {winning_team}")
                                    print(f"losing_team: {losing_team}")
                                    print(f"team_2: {team_2}")
                                    print(f"league: {league}")
                                    print(" ")
                                elif team_3 == winning_team and team_3 == item.team:
                                    new_player_score = session.query(Player_weekly_info).filter(
                                        Player_weekly_info.id == info.id).first().this_weeks_score + 1
                                    session.query(Player_weekly_info).filter(Player_weekly_info.id == info.id).update(
                                        {"this_weeks_score": new_player_score})
                                    print(f"{user_name} +1 from team_3")
                                    print(f"winning_team: {winning_team}")
                                    print(f"losing_team: {losing_team}")
                                    print(f"team_3: {team_3}")
                                    print(f"league: {league}")
                                    print(" ")
                                elif team_4 == winning_team and team_4 == item.team:
                                    new_player_score = session.query(Player_weekly_info).filter(
                                        Player_weekly_info.id == info.id).first().this_weeks_score + 1
                                    session.query(Player_weekly_info).filter(Player_weekly_info.id == info.id).update(
                                        {"this_weeks_score": new_player_score})
                                    print(f"{user_name} +1 from team_4")
                                    print(f"winning_team: {winning_team}")
                                    print(f"losing_team: {losing_team}")
                                    print(f"team_4: {team_4}")
                                    print(f"league: {league}")
                                    print(" ")

                except IndexError:
                    # If IndexError, then the team doesn't have a game so assign it 0 and mark it as updated. It needs to be
                    # Saturday before updating so someone can still drop this team and add another one
                    if today.weekday() == 5:
                        session.query(Football_Teams).filter(Football_Teams.team == team_to_query.replace("%26", "&")).update(
                            {f"week{week}_score": 0, "updated_this_week": True})

                        # Add to the log that the team was updated
                        with open(f"log.txt", mode="a") as file:
                            text = f"Week {week}: {item.team} updated \n"
                            file.write(text)
                    else:
                        pass
        #TypeError occurs when a team is on bye and datetime is being compared to NoneType
        except TypeError:
            session.query(Football_Teams).filter(Football_Teams.team == item.team).update(
                {"updated_this_week": True, "previous_result": None, "previous_opponent": "BYE", f"week{week}_score": 0})
        time.sleep(2)
    session.commit()

# scores_2022 = {"Clemson": 11, "Florida State": 10, "Syracuse": 7, "Louisville": 8, "NC State": 8, "Wake Forest": 8,
#                "Boston College": 3, "North Carolina": 9, "Pittsburgh": 9, "Duke": 9, "Georgia Tech": 5, "Miami": 5,
#                "Virginia": 3, "Virginia Tech": 3, "TCU": 12, "Kansas State": 10, "Texas": 8, "Texas Tech": 9,
#                "Oklahoma State": 7, "Baylor": 6, "Oklahoma": 6, "Kansas": 6, "West Virginia": 5, "Iowa State": 4,
#                "Michigan": 13, "Ohio State": 11, "Penn State": 11, "Maryland": 8, "Michigan State": 5, "Indiana": 4,
#                "Rutgers": 4, "Purdue": 8, "Illinois": 8, "Iowa": 8, "Minnesota": 9, "Wisconsin": 7, "Nebraska": 4,
#                "Northwestern": 1, "Notre Dame": 9, "BYU": 8, "UCF": 9, "Cincinnati": 9, "Houston": 8, "USC": 11,
#                "Washington": 11, "Oregon": 10, "Utah": 10, "Oregon State": 10, "UCLA": 9, "Washington State": 7,
#                "Arizona": 5, "California": 4, "Arizona State": 3, "Stanford": 3, "Colorado": 1, "Georgia": 13,
#                "Tennessee": 11, "South Carolina": 8, "Kentucky": 7, "Florida": 6, "Missouri": 6, "Vanderbilt": 5,
#                "LSU": 10,
#                "Alabama": 11, "Mississippi State": 9, "Ole Miss": 8, "Arkansas": 7, "Auburn": 5, "Texas A&M": 5}
#
# conferences_2023 = {"Clemson": "ACC", "Florida State": "ACC", "Syracuse": "ACC", "Louisville": "ACC",
#                         "NC State": "ACC", "Wake Forest": "ACC",
#                         "Boston College": "ACC", "North Carolina": "ACC", "Pittsburgh": "ACC", "Duke": "ACC",
#                         "Georgia Tech": "ACC", "Miami": "ACC",
#                         "Virginia": "ACC", "Virginia Tech": "ACC", "TCU": "Big 12", "Kansas State": "Big 12",
#                         "Texas": "Big 12", "Texas Tech": "Big 12",
#                         "Oklahoma State": "Big 12", "Baylor": "Big 12", "Oklahoma": "Big 12", "Kansas": "Big 12",
#                         "West Virginia": "Big 12", "Iowa State": "Big 12",
#                         "Michigan": "Big 10", "Ohio State": "Big 10", "Penn State": "Big 10", "Maryland": "Big 10",
#                         "Michigan State": "Big 10", "Indiana": "Big 10",
#                         "Rutgers": "Big 10", "Purdue": "Big 10", "Illinois": "Big 10", "Iowa": "Big 10",
#                         "Minnesota": "Big 10", "Wisconsin": "Big 10", "Nebraska": "Big 10",
#                         "Northwestern": "Big 10", "Notre Dame": "Independent", "BYU": "Big 12", "UCF": "Big 12",
#                         "Cincinnati": "Big 12", "Houston": "Big 12", "USC": "PAC 12",
#                         "Washington": "PAC 12", "Oregon": "PAC 12", "Utah": "PAC 12", "Oregon State": "PAC 12",
#                         "UCLA": "PAC 12", "Washington State": "PAC 12",
#                         "Arizona": "PAC 12", "California": "PAC 12", "Arizona State": "PAC 12", "Stanford": "PAC 12",
#                         "Colorado": "PAC 12", "Georgia": "SEC",
#                         "Tennessee": "SEC", "South Carolina": "SEC", "Kentucky": "SEC", "Florida": "SEC",
#                         "Missouri": "SEC", "Vanderbilt": "SEC",
#                         "LSU": "SEC", "Alabama": "SEC", "Mississippi State": "SEC", "Ole Miss": "SEC",
#                         "Arkansas": "SEC", "Auburn": "SEC", "Texas A&M": "SEC"}

# for every_team in all_teams:
#     print(every_team.id)
#     db.session.query(Football_Teams).filter(Football_Teams.id == every_team.id).update(
#         {"conference": conferences_2023[every_team.team]})
#     print(f"{every_team.team} is in {every_team.conference}")
# session.commit()

run_programs = True
if run_programs:

    #This should be <= 1 to work properly (normally on Mondays) but should be == 1 for week 2 since teams play on Monday on week 1
    if today.weekday() <= 2 and week != 2:
        print('getting upcoming games')
        get_upcoming_games()
    elif today.weekday() == 1 and week == 2:
        print('getting upcoming games')
        get_upcoming_games()

    #Update this to >= 3
    i = 0
    if today.weekday() >= 3:
        while i < 30:
            print(f"i: {i}")
            cutoff_for_querying_games = datetime.now() + time_delta
            teams_to_update = session.query(Football_Teams).filter_by(updated_this_week=False).all()
            if len(teams_to_update) > 0:
                get_scores()
                print(" ")
                print(" ")
                time.sleep(600)
            i += 1

# ----------------- SANDBOX -------------------
get_waiver_info = False
edit_user_info = False
add_waiver_info = False
reset_waivers = False
# # Reset Football team/teams's score(s)
# teams = ["Iowa State", "Virginia"]
# for team in teams:
#     session.query(Football_Teams).filter_by(team=team).update({"current_score": 0,
#                 "week1_score": 0, "updated_this_week": False})
# session.commit()

# # Query a team's info
# team = "USC"
# print(session.query(Football_Teams).filter(Football_Teams.team == team).first().updated_this_week)
# print(session.query(Football_Teams).filter(Football_Teams.team == team).first().week0_score)
# print(session.query(Football_Teams).filter(Football_Teams.team == team).first().current_score)

# Edit someone's score/info
if edit_user_info:
    user_id = 40
    league = 53
    session.query(Player_weekly_info).filter(Player_weekly_info.user_id == user_id).filter(Player_weekly_info.league == league).update({"this_weeks_score": 4})
    session.commit()

# Get waiver info
if get_waiver_info:
    all_waivers = session.query(Waiver_Info).all()
    print(len(all_waivers))
    for waiver in all_waivers:
        print(waiver.league)

# Add waiver info for someone
if add_waiver_info:
    user_id = 42
    league = 53
    team_to_add_id = 47
    team_to_drop_id = 59
    faab_submitted = 0
    priority = 1
    waiver = Waiver_Info(user_id=user_id, league=league, team_to_add_id=team_to_add_id, team_to_drop_id=team_to_drop_id, faab_submitted=faab_submitted, priority=priority)
    session.add(waiver)
    session.commit()

# Turn the leagues back to waivers only
if reset_waivers:
    all_leagues = session.query(League).all()
    for the_league in all_leagues:
        session.query(League).filter(League.id == the_league.id).update({"waivers_already_executed": False})
        session.commit()

# # Set previous_result for every team already played
# team = "Utah"
# session.query(Football_Teams).filter_by(team=team).update({"previous_result": "W"})
# session.commit()

# # Get weekly scores
# new_results = session.query(Football_Teams).all()
# for item in new_results:
#     print(item.team)
#     print(item.date_and_time_of_game)

# # Reset password
# user_id = 43
# user = session.query(User).filter_by(id=user_id).update({"locked_account": False})
# session.commit()
#
# # Get all team ids
# all_teams = session.query(Football_Teams).order_by(Football_Teams.id)
# for every_team in all_teams:
#     print(f"team_name: {every_team.team}")
#     print(f"team_id: {every_team.id}")