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
import random
import math
# from main import User, League, League_members_update1, List_of_leagues_update1, Player_weekly_info, Football_Teams

scores_test = False
app = Flask(__name__)

app.config['SECRET_KEY'] = 'secret-key-goes-here'
# Heroku SQL
# app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://qylursxvbzavwz:87013a2c4de430e9e802f20f1215996ce267f4bdd5f7f9459881f6461187a718@ec2-3-93-160-246.compute-1.amazonaws.com:5432/dbg16caap1t7nk'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://rtkehelbfufmyx:727fe1bde6ea928e69cc13c697362850d38f84b02328c7a6bc91ec86774401ba@ec2-34-206-79-150.compute-1.amazonaws.com:5432/db8dqi5aldvff'
engine = create_engine('postgresql://rtkehelbfufmyx:727fe1bde6ea928e69cc13c697362850d38f84b02328c7a6bc91ec86774401ba@ec2-34-206-79-150.compute-1.amazonaws.com:5432/db8dqi5aldvff', echo=False)
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


class Matchup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    week = db.Column(db.Integer, default=1)
    league = db.Column(db.Integer, db.ForeignKey('league.id'))
    user_id1 = db.Column(db.Integer, db.ForeignKey('user.id'))
    user_id2 = db.Column(db.Integer, db.ForeignKey('user.id'))
    user1_score = db.Column(db.Integer, default=0)
    user2_score = db.Column(db.Integer, default=0)


"""
1s represent a win, 0s represent a loss or no game played
"""

year = 2024
week, postseason = my_functions.determine_week_number()
# week = 2
postseason = False
print(f"week: {week}")
today = date.today()
now = datetime.now()
print(now)
week_01_cutoff = datetime(2024, 8, 30)

# time_delta is the value used to determine how far in the future to query games
# time_correction is to go from central time to gmt
time_correction = 5
time_delta = timedelta(hours=0 + time_correction)
time_correction_delta = timedelta(hours=5)


def get_upcoming_games():
    # Get the rankings for all the teams
    rankings_response = my_functions.get_rankings(year=2024, week=week)
    rankings_response_reduced = rankings_response[0]['polls'][1]['ranks']
    i = 0
    school_dict = {}
    while i < len(rankings_response_reduced):
        school = rankings_response_reduced[i]['school']
        school_dict[school] = i + 1
        i += 1
    print(school_dict)

    # Get all of the games
    all_teams = session.query(Football_Teams).all()
    all_teams_list = [item.team for item in all_teams]
    exclusion_list = ["Oregon State", "Washington State"]
    for item in all_teams:
        print(item.team)
        team_to_query = item.team.replace("&", "%26")
        game = my_functions.get_game_data(year=year, week=week, team=team_to_query)
        team_to_query = team_to_query.replace("%26", "&")
        number_of_games = len(game)
        try:
            ap_ranking = school_dict[item.team]
        except KeyError:
            ap_ranking = None
        if number_of_games > 1 and datetime.now() > datetime.combine(date(2024, 8, 28), datetime.min.time()):
            home_team = game[1]['home_team']
            away_team = game[1]['away_team']
            game_time = game[1]['start_date']
            print(game_time)
            if team_to_query == home_team:
                upcoming_opponent = away_team
                if upcoming_opponent in all_teams_list and upcoming_opponent not in exclusion_list:
                    opponent_p5 = True
                else:
                    opponent_p5 = False
                try:
                    upcoming_opponent_ap_ranking = school_dict[away_team]
                    print(f'upcoming opponent info11: {upcoming_opponent_ap_ranking} {upcoming_opponent}')
                except KeyError:
                    upcoming_opponent_ap_ranking = None
                    print(f'upcoming opponent info21: {upcoming_opponent_ap_ranking} {upcoming_opponent}')
            else:
                upcoming_opponent = home_team
                if upcoming_opponent in all_teams_list and upcoming_opponent not in exclusion_list:
                    opponent_p5 = True
                else:
                    opponent_p5 = False
                try:
                    upcoming_opponent_ap_ranking = school_dict[home_team]
                    print(f'upcoming opponent info31: {upcoming_opponent_ap_ranking} {upcoming_opponent}')
                except KeyError:
                    upcoming_opponent_ap_ranking = None
                    print(f'upcoming opponent info41: {upcoming_opponent_ap_ranking} {upcoming_opponent}')
        else:
            try:
                home_team = game[0]['home_team']
                away_team = game[0]['away_team']
                game_time = game[0]['start_date']
                print(game_time)
                if team_to_query == home_team:
                    upcoming_opponent = away_team
                    if upcoming_opponent in all_teams_list and upcoming_opponent not in exclusion_list:
                        opponent_p5 = True
                    else:
                        opponent_p5 = False
                    try:
                        upcoming_opponent_ap_ranking = school_dict[away_team]
                        print(f'upcoming opponent info1: {upcoming_opponent_ap_ranking} {upcoming_opponent}')
                    except KeyError:
                        upcoming_opponent_ap_ranking = None
                        print(f'upcoming opponent info2: {upcoming_opponent_ap_ranking} {upcoming_opponent}')
                else:
                    upcoming_opponent = home_team
                    if upcoming_opponent in all_teams_list and upcoming_opponent not in exclusion_list:
                        opponent_p5 = True
                    else:
                        opponent_p5 = False
                    try:
                        upcoming_opponent_ap_ranking = school_dict[home_team]
                        print(f'upcoming opponent info3: {upcoming_opponent_ap_ranking} {upcoming_opponent}')
                    except KeyError:
                        upcoming_opponent_ap_ranking = None
                        print(f'upcoming opponent info4: {upcoming_opponent_ap_ranking} {upcoming_opponent}')
            # IndexError occurs when a team is on a Bye since the returned result is None
            except IndexError:
                upcoming_opponent = "BYE"
                game_time = datetime.utcnow() + timedelta(days=10)

        session.query(Football_Teams).filter_by(team=team_to_query).update({"upcoming_opponent": upcoming_opponent,
            "date_and_time_of_game": game_time, "updated_this_week": False, "ap_ranking": ap_ranking, "opponent_ap_ranking": upcoming_opponent_ap_ranking,
            "opponent_p5": opponent_p5})
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
                            print('entered 1')
                            home_team = game[1]['home_team']
                            away_team = game[1]['away_team']
                            home_score = game[1]['home_points']
                            away_score = game[1]['away_points']
                            game_completed = game[1]['completed']
                        else:
                            print('entered 2')
                            home_team = game[0]['home_team']
                            away_team = game[0]['away_team']
                            home_score = game[0]['home_points']
                            away_score = game[0]['away_points']
                            game_completed = game[0]['completed']
                    else:
                        print('entered 3')
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
                                points_to_add = 1
                                if session.query(Football_Teams).filter(Football_Teams.team == item.team).first().opponent_ap_ranking is not None:
                                    points_to_add += 0.25
                                try:
                                    opponent = session.query(Football_Teams).filter(Football_Teams.team == losing_team).first().team
                                    if losing_team != "Oregon State" and losing_team != "Washington State":
                                        points_to_add += 0.25
                                except AttributeError:
                                    pass

                                print(f"{item.team} won. New score +{points_to_add}")
                                new_score = session.query(Football_Teams).filter(Football_Teams.team == winning_team).first().current_score + points_to_add
                                session.query(Football_Teams).filter(Football_Teams.team == winning_team).update(
                                    {f"week{week}_score": points_to_add, "updated_this_week": True, "playing_now": False, "current_score": new_score,
                                     "previous_opponent": losing_team, "previous_result": "W", "chance_to_win": 1.00})
                                try:
                                    write_data_dict = {"Week": [week], "Team": [item.team], "Points": [points_to_add]}
                                    write_data = pandas.DataFrame(write_data_dict)
                                    write_data.to_csv(f"Results.csv", mode='a', header=False)
                                except FileNotFoundError:
                                    print('FILE NOT FOUND')
                                    pass
                            elif item.team == losing_team:
                                print(f"{item.team} lost. No new score")
                                session.query(Football_Teams).filter(Football_Teams.team == losing_team).update(
                                    {f"week{week}_score": 0, "updated_this_week": True, "playing_now": False, "previous_opponent": winning_team, "previous_result": "L", "chance_to_win": 0.00})
                                try:
                                    write_data_dict = {"Week": [week], "Team": [item.team], "Points": [0]}
                                    write_data = pandas.DataFrame(write_data_dict)
                                    write_data.to_csv(f"Results.csv", mode='a', header=False)
                                except FileNotFoundError:
                                    print('FILE NOT FOUND')
                                    pass
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
                                    this_weeks_score = session.query(Player_weekly_info).filter(
                                        Player_weekly_info.id == info.id).first().this_weeks_score
                                    try:
                                        old_win_total = session.query(Player_weekly_info).filter(
                                            Player_weekly_info.id == info.id).first().total_wins
                                    except AttributeError:
                                        person = session.query(User).filter(User.id == info.user_id).first().name
                                        print(f'AttributeError entered. User {person}')
                                        old_win_total = 0
                                    new_player_score = this_weeks_score + points_to_add
                                    new_player_win_total = old_win_total + 1
                                    session.query(Player_weekly_info).filter(Player_weekly_info.id == info.id).update(
                                        {"this_weeks_score": new_player_score, "total_wins": new_player_win_total})
                                    print(f"{user_name} +1 win from team_1, +{points_to_add} from the win")
                                    print(f"winning_team: {winning_team}")
                                    print(f"losing_team: {losing_team}")
                                    print(f"team_1: {team_1}")
                                    print(f"league: {league}")
                                    print(" ")
                                elif team_2 == winning_team and team_2 == item.team:
                                    this_weeks_score = session.query(Player_weekly_info).filter(
                                        Player_weekly_info.id == info.id).first().this_weeks_score
                                    try:
                                        old_win_total = session.query(Player_weekly_info).filter(Player_weekly_info.id == info.id).first().total_wins
                                    except AttributeError:
                                        old_win_total = 0
                                    new_player_score = this_weeks_score + points_to_add
                                    new_player_win_total = old_win_total + 1
                                    session.query(Player_weekly_info).filter(Player_weekly_info.id == info.id).update(
                                        {"this_weeks_score": new_player_score, "total_wins": new_player_win_total})
                                    print(f"{user_name} +{points_to_add} from team_2")
                                    print(f"winning_team: {winning_team}")
                                    print(f"losing_team: {losing_team}")
                                    print(f"team_2: {team_2}")
                                    print(f"league: {league}")
                                    print(f'info.id: {info.id}')
                                    print(" ")
                                elif team_3 == winning_team and team_3 == item.team:
                                    this_weeks_score = session.query(Player_weekly_info).filter(
                                        Player_weekly_info.id == info.id).first().this_weeks_score
                                    try:
                                        old_win_total = session.query(Player_weekly_info).filter(
                                            Player_weekly_info.id == info.id).first().total_wins
                                    except AttributeError:
                                        old_win_total = 0
                                    new_player_score = this_weeks_score + points_to_add
                                    new_player_win_total = old_win_total + 1
                                    session.query(Player_weekly_info).filter(Player_weekly_info.id == info.id).update(
                                        {"this_weeks_score": new_player_score, "total_wins": new_player_win_total})
                                    print(f"{user_name} +1 from team_3")
                                    print(f"winning_team: {winning_team}")
                                    print(f"losing_team: {losing_team}")
                                    print(f"team_3: {team_3}")
                                    print(f"league: {league}")
                                    print(" ")
                                elif team_4 == winning_team and team_4 == item.team:
                                    this_weeks_score = session.query(Player_weekly_info).filter(
                                        Player_weekly_info.id == info.id).first().this_weeks_score
                                    try:
                                        old_win_total = session.query(Player_weekly_info).filter(
                                            Player_weekly_info.id == info.id).first().total_wins
                                    except AttributeError:
                                        old_win_total = 0
                                    new_player_score = this_weeks_score + points_to_add
                                    new_player_win_total = old_win_total + 1
                                    session.query(Player_weekly_info).filter(Player_weekly_info.id == info.id).update(
                                        {"this_weeks_score": new_player_score, "total_wins": new_player_win_total})
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
conferences_2024 = {"Clemson": "ACC", "Florida State": "ACC", "Syracuse": "ACC", "Louisville": "ACC",
                        "NC State": "ACC", "Wake Forest": "ACC",
                        "Boston College": "ACC", "North Carolina": "ACC", "Pittsburgh": "ACC", "Duke": "ACC",
                        "Georgia Tech": "ACC", "Miami": "ACC",
                        "Virginia": "ACC", "Virginia Tech": "ACC", "TCU": "Big 12", "Kansas State": "Big 12",
                        "Texas": "SEC", "Texas Tech": "Big 12",
                        "Oklahoma State": "Big 12", "Baylor": "Big 12", "Oklahoma": "SEC", "Kansas": "Big 12",
                        "West Virginia": "Big 12", "Iowa State": "Big 12",
                        "Michigan": "Big 10", "Ohio State": "Big 10", "Penn State": "Big 10", "Maryland": "Big 10",
                        "Michigan State": "Big 10", "Indiana": "Big 10",
                        "Rutgers": "Big 10", "Purdue": "Big 10", "Illinois": "Big 10", "Iowa": "Big 10",
                    "Minnesota": "Big 10", "Wisconsin": "Big 10", "Nebraska": "Big 10",
                    "Northwestern": "Big 10", "Notre Dame": "Independent", "BYU": "Big 12", "UCF": "Big 12",
                    "Cincinnati": "Big 12", "Houston": "Big 12", "USC": "Big 10",
                    "Washington": "Big 10", "Oregon": "Big 10", "Utah": "Big 12", "Oregon State": "PAC 12",
                    "UCLA": "Big 10", "Washington State": "PAC 12",
                    "Arizona": "Big 12", "California": "ACC", "Arizona State": "Big 12", "Stanford": "ACC",
                    "Colorado": "Big 12", "Georgia": "SEC",
                    "Tennessee": "SEC", "South Carolina": "SEC", "Kentucky": "SEC", "Florida": "SEC",
                    "Missouri": "SEC", "Vanderbilt": "SEC",
                    "LSU": "SEC", "Alabama": "SEC", "Mississippi State": "SEC", "Ole Miss": "SEC",
                    "Arkansas": "SEC", "Auburn": "SEC", "Texas A&M": "SEC", "SMU": "ACC"}

# for every_team in all_teams:
#     print(every_team.id)
#     db.session.query(Football_Teams).filter(Football_Teams.id == every_team.id).update(
#         {"conference": conferences_2023[every_team.team]})
#     print(f"{every_team.team} is in {every_team.conference}")
# session.commit()

run_programs = False
if run_programs:
    # week = 3
    upcoming_test = False
    upcoming_exclude = False
    scores_exclude = False
    print(today.weekday())
    # This should be <= 1 to work properly (normally on Mondays) but should be == 1 for week 2 since teams play on Monday on week 1
    if upcoming_test or today.weekday() <= 2 and week != 2 and not upcoming_exclude:
        print('getting upcoming games1')
        get_upcoming_games()
    elif upcoming_test or today.weekday() <= 1 and week == 2 and not upcoming_exclude:
        print('getting upcoming games2')
        get_upcoming_games()

    #Update this to >= 3
    i = 0
    if today.weekday() >= 3 and not scores_exclude:
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
get_waiver_info = True
edit_user_info = False
add_waiver_info = False
reset_waivers = False
reset_win_probabilities = False
reset_previous_results = False
reset_all_teams_scores = False
reset_all_users_scores = False
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
        print(f'in league {waiver.league}, {session.query(User).filter(User.id == waiver.user_id).first().name}, {session.query(Football_Teams).filter(Football_Teams.id == waiver.team_to_add_id).first().team}, {waiver.faab_submitted}')

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

# Reset win probabilities for all teams
if reset_win_probabilities:
    all_teams = session.query(Football_Teams).order_by(Football_Teams.id)
    for every_team in all_teams:
        print(f"team_name: {every_team.team}")
        print(f"team_id: {every_team.id}")
        print(f"team_conference: {every_team.conference}")
        session.query(Football_Teams).filter(Football_Teams.id == every_team.id).update(
            {"chance_to_win": 0})
    session.commit()

# Reset the previous win results for all teams
if reset_previous_results:
    all_teams = session.query(Football_Teams).order_by(Football_Teams.id)
    for every_team in all_teams:
        print(f"team_name: {every_team.team}")
        print(f"team_id: {every_team.id}")
        session.query(Football_Teams).filter(Football_Teams.id == every_team.id).update(
            {"previous_opponent": "", "previous_result": ""})
    session.commit()

if reset_all_teams_scores:
    all_teams = session.query(Football_Teams).order_by(Football_Teams.id)
    for every_team in all_teams:
        print(f"team_name: {every_team.team}")
        print(f"team_id: {every_team.id}")
        session.query(Football_Teams).filter(Football_Teams.id == every_team.id).update(
            {"updated_this_week": False, "current_score": 0, "week0_score": 0})
    session.commit()

if reset_all_users_scores:
    all_weekly_infos = session.query(Player_weekly_info).order_by(Player_weekly_info.id)
    for weekly_info in all_weekly_infos:
        print(f"user_id: {weekly_info.user_id}")
        week = 1
        try:
            print(weekly_info.id)
            print(weekly_info.this_weeks_score)
            var = session.query(Player_weekly_info).filter(Player_weekly_info.id == weekly_info.id).first()
            print(var)
            session.query(Player_weekly_info).filter(Player_weekly_info.id == weekly_info.id).update({"this_weeks_score": 0})
        except AttributeError:
            pass
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


# # Get all team ids
# team_to_update_id = session.query(Football_Teams).filter_by(team="Washington").update({"conference": "Big 10"})
# session.commit()
# all_teams = session.query(Football_Teams).order_by(Football_Teams.id)
# for every_team in all_teams:
#     print(f"team_name: {every_team.team}")
#     print(f"team_id: {every_team.id}")
#     print(f"team_conference: {every_team.conference}")

# # Reset everyones teams
# all_users = session.query(Player_weekly_info).all()
# for user in all_users:
#     # session.query(Player_weekly_info).filter(Player_weekly_info.id == user.id).update({"team_1": None})
#     # session.query(Player_weekly_info).filter(Player_weekly_info.id == user.id).update({"team_2": None})
#     # session.query(Player_weekly_info).filter(Player_weekly_info.id == user.id).update({"team_3": None})
#     # session.query(Player_weekly_info).filter(Player_weekly_info.id == user.id).update({"team_4": None})
#     var = session.query(Player_weekly_info).filter(Player_weekly_info.id == user.id).first()
#     print(var.team_1)
# session.commit()

# league_id = 48
# # league_members = League_members_update1.query.order_by(League_members_update1.league_id)
# league_members = session.query(League_members_update1).filter(League_members_update1.league_id == league_id)
# league_member_ids = [member.member for member in league_members]

def round_robin_schedule(num_people):
    participants = sorted(league_member_ids, key=lambda x: random.random())
    schedule = []
    if num_people % 2 != 0:
        participants.append("Bye")  # Add a "Bye" week
        num_people += 1

    for round in range(num_people - 1):
        round_matchups = []
        for i in range(num_people // 2):
            p1 = participants[i]
            p2 = participants[num_people - 1 - i]
            if "Bye" in (p1, p2):
                bye_team = p1 if p1 != "Bye" else p2
                round_matchups.append((bye_team, "Bye"))
            else:
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
            matchup = Matchup(week=week_num, league=league_id, user_id1=match[0], user_id2=match[1], user1_score=0, user2_score=0)
            session.add(matchup)
            session.commit()

# # Create a round-robin schedule for a number of participants based upon league size and extend to the number of weeks
# # in the season
# num_participants = len(league_member_ids)
# base_schedule = round_robin_schedule(num_participants)
# full_schedule = extend_schedule(base_schedule, 16)
# print_schedule(full_schedule)
# commit_schedule(full_schedule, league_id=league_id)

# all_matchups = session.query(Matchup).all()
# for matchup in all_matchups:
#     print(f'Week {matchup.week}: Player {matchup.user_id1} vs Player {matchup.user_id2}')


# team_to_add =Football_Teams(id=70, team="SMU", updated_this_week=False, playing_now=False, upcoming_opponent=None, previous_opponent=None,
#                             previous_result=None, date_and_time_of_game=None, current_score=0, conference="ACC", chance_to_win=0,
#                             ap_ranking=None, opponent_ap_ranking=None, opponent_p5=None, week0_score=0, week1_score=0,
#                             week2_score=0, week3_score=0, week4_score=0, week5_score=0, week6_score=0, week7_score=0, week8_score=0,
#                             week9_score=0, week10_score=0, week11_score=0, week12_score=0, week13_score=0, week14_score=0, week15_score=0)
# session.add(team_to_add)
# session.commit()

# # Reset all teams points and weekly scores to 0 to start the season
# all_teams = session.query(Football_Teams).order_by(Football_Teams.id)
# for every_team in all_teams:
#     print(f"team_name: {every_team.team}")
#     print(f"team_conference: {every_team.conference}")
#     session.query(Football_Teams).filter(Football_Teams.id == every_team.id).update(
#         {"current_score": 0, "week0_score": 0, "week1_score": 0, "week2_score": 0, "week3_score": 0, "week4_score": 0,
#          "week5_score": 0, "week6_score": 0, "week7_score": 0, "week8_score": 0, "week9_score": 0, "week10_score": 0,
#          "week11_score": 0, "week12_score": 0, "week13_score": 0, "week14_score": 0, "week15_score": 0})
# session.commit()

# # Put someone into a league
# league_id = 57
# member_id = 31
# league = session.query(League).filter_by(id=league_id).first()
# league_member = League_members_update1(league_id=league_id, member=member_id)
# member_name = session.query(User).filter_by(id=member_id).first().name
# league_name = session.query(League).filter_by(id=league_id).first().league_name
# print(f'{member_name} added to {league_name}')
# # make sure someone isn't added if they're already in the league
#
# session.add(league_member)
# session.commit()
# league_to_add = List_of_leagues_update1(user_id=member_id, league=league_id)
# session.add(league_to_add)
# session.commit()
# initial_player_setup = Player_weekly_info(user_id=member_id, league=league_id)
# session.add(initial_player_setup)
# session.commit()

# all_player_weekly_info = session.query(Player_weekly_info).order_by(Player_weekly_info.id)
# for info in all_player_weekly_info:
#     user = session.query(User).filter(User.id == info.user_id).first()
#     user_name = user.name
#     user_id = info.id
#     league = info.league
#     wins = info.total_wins
#     print(f'{user_name} and {user_id} in league {league} has {wins} wins')

# session.query(Player_weekly_info).filter(Player_weekly_info.id == 85).update({"total_wins": 4})
# session.commit()
