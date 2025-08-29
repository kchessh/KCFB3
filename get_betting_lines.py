import pandas
import requests
from flask import Flask, render_template, request, url_for, redirect, flash, send_from_directory
from flask_wtf import FlaskForm
from datetime import date, datetime, timedelta
import my_functions
from wtforms import StringField, SubmitField, PasswordField, BooleanField, ValidationError, EmailField, IntegerField, \
    SelectField
from wtforms.validators import DataRequired, EqualTo, Length, InputRequired
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import select, delete, update, inspect, create_engine, text
from sqlalchemy.orm import sessionmaker
from flask_migrate import Migrate
import cases

api_key = "e9ec5b959e22a45ecf9151165b6afaa4"
url = f"https://api.the-odds-api.com/v4/sports/?apiKey={api_key}"
url2 = f"https://api.the-odds-api.com/v4/sports/americanfootball_ncaaf/odds/?apiKey={api_key}&regions=us&markets=h2h"

response = requests.get(url2)
data = response.json()

print(data)
app = Flask(__name__)

app.config['SECRET_KEY'] = 'secret-key-goes-here'
# Heroku SQL
# app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://qylursxvbzavwz:87013a2c4de430e9e802f20f1215996ce267f4bdd5f7f9459881f6461187a718@ec2-3-93-160-246.compute-1.amazonaws.com:5432/dbg16caap1t7nk'
app.config[
    'SQLALCHEMY_DATABASE_URI'] = 'postgresql://urpkh4m7l378b:p0ca7da822b3823177e9879b78d7561c458d2185364439e2a6b51828147a8ee3c@cd5vlri6nnqe17.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/d1vrtkcrdmm43p'
engine = create_engine('postgresql://urpkh4m7l378b:p0ca7da822b3823177e9879b78d7561c458d2185364439e2a6b51828147a8ee3c@cd5vlri6nnqe17.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/d1vrtkcrdmm43p', echo=False)
Session = sessionmaker(bind=engine)
session = Session()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db, compare_type=True)
Bootstrap(app)

class Football_Teams(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team = db.Column(db.String(100), nullable=True)
    updated_this_week = db.Column(db.Boolean, default=False)
    playing_now = db.Column(db.Boolean, default=False)
    upcoming_opponent = db.Column(db.String(100), nullable=True)
    previous_opponent = db.Column(db.String(100), nullable=True, default="")
    date_and_time_of_game = db.Column(db.DateTime)
    current_score = db.Column(db.Integer, default=0)
    conference = db.Column(db.String(30), nullable=True)
    chance_to_win = db.Column(db.Float, default=0)
    ap_ranking = db.Column(db.Integer, default=None)
    opponent_ap_ranking = db.Column(db.Integer, default=None)
    opponent_p5 = db.Column(db.Boolean, default=False)
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

teams = {"Alabama Crimson Tide": 1, "Arizona Wildcats": 2, "Arizona State Sun Devils": 3, "Arkansas Razorbacks": 4, "Auburn Tigers": 5, "Baylor Bears": 6, "Boston College Eagles": 7, "BYU Cougars": 8,
         "California Golden Bears": 9, "Cincinnati Bearcats": 10, "Clemson Tigers": 11, "Colorado Buffaloes": 12, "Duke Blue Devils": 13, "Florida Gators": 14, "Florida State Seminoles": 15,
         "Georgia Bulldogs": 16, "Georgia Tech Yellow Jackets": 17, "Houston Cougars": 18, "Illinois Fighting Illini": 19, "Indiana Hoosiers": 20, "Iowa Hawkeyes": 21, "Iowa State Cyclones": 22,
         "Kansas Jayhawks": 23, "Kansas State Wildcats": 24, "Kentucky Wildcats": 25, "Louisville Cardinals": 26, "LSU Tigers": 27, "Maryland Terrapins": 28, "Miami Hurricanes": 29, "Michigan Wolverines": 30,
         "Michigan State Spartans": 31, "Minnesota Golden Gophers": 32, "Mississippi State Bulldogs": 66, "Missouri Tigers": 34, "NC State Wolfpack": 35, "Nebraska Cornhuskers": 36,
         "North Carolina Tar Heels": 37, "Northwestern Wildcats": 38, "Notre Dame Fighting Irish": 39, "Ohio State Buckeyes": 40, "Oklahoma Sooners": 41, "Oklahoma State Cowboys": 42, "Ole Miss Rebels": 43,
         "Oregon Ducks": 44, "Oregon State Beavers": 45, "Penn State Nittany Lions": 46, "Pittsburgh Panthers": 47, "Purdue Boilermakers": 48, "Rutgers Scarlet Knights": 49, "South Carolina Gamecocks": 50,
         "Stanford Cardinal": 51, "Syracuse Orange": 52, "TCU Horned Frogs": 53, "Tennessee Volunteers": 54, "Texas Longhorns": 55, "Texas A&M Aggies": 56, "Texas Tech Red Raiders": 57, "UCF Knights": 58,
         "UCLA Bruins": 59, "USC Trojans": 60, "Utah Utes": 61, "Vanderbilt Commodores": 62, "Virginia Cavaliers": 63, "Virginia Tech Hokies": 64, "Wake Forest Demon Deacons": 65, "Washington Huskies": 66,
         "Washington State Cougars": 67, "West Virginia Mountaineers": 68, "Wisconsin Badgers": 69, "SMU Mustangs": 70}

teams_db = {"Alabama Crimson Tide": 61, "Arizona Wildcats": 44, "Arizona State Sun Devils": 45, "Arkansas Razorbacks": 62, "Auburn Tigers": 63, "Baylor Bears": 32, "Boston College Eagles": 1, "BYU Cougars": 40,
         "California Golden Bears": 46, "Cincinnati Bearcats": 42, "Clemson Tigers": 2, "Colorado Buffaloes": 47, "Duke Blue Devils": 3, "Florida Gators": 54, "Florida State Seminoles": 4,
         "Georgia Bulldogs": 55, "Georgia Tech Yellow Jackets": 5, "Houston Cougars": 43, "Illinois Fighting Illini": 23, "Indiana Hoosiers": 16, "Iowa Hawkeyes": 24, "Iowa State Cyclones": 33,
         "Kansas Jayhawks": 34, "Kansas State Wildcats": 35, "Kentucky Wildcats": 56, "Louisville Cardinals": 6, "LSU Tigers": 64, "Maryland Terrapins": 17, "Miami Hurricanes": 7, "Michigan Wolverines": 18,
         "Michigan State Spartans": 19, "Minnesota Golden Gophers": 25, "Mississippi State Bulldogs": 66, "Missouri Tigers": 57, "NC State Wolfpack": 9, "Nebraska Cornhuskers": 26,
         "North Carolina Tar Heels": 8, "Northwestern Wildcats": 27, "Notre Dame Fighting Irish": 15, "Ohio State Buckeyes": 20, "Oklahoma Sooners": 68, "Oklahoma State Cowboys": 36, "Ole Miss Rebels": 65,
         "Oregon Ducks": 48, "Oregon State Beavers": 49, "Penn State Nittany Lions": 21, "Pittsburgh Panthers": 10, "Purdue Boilermakers": 28, "Rutgers Scarlet Knights": 22, "South Carolina Gamecocks": 58,
         "Stanford Cardinal": 50, "Syracuse Orange": 11, "TCU Horned Frogs": 37, "Tennessee Volunteers": 59, "Texas Longhorns": 69, "Texas A&M Aggies": 67, "Texas Tech Red Raiders": 38, "UCF Knights": 41,
         "UCLA Bruins": 31, "USC Trojans": 30, "Utah Utes": 51, "Vanderbilt Commodores": 60, "Virginia Cavaliers": 12, "Virginia Tech Hokies": 13, "Wake Forest Demon Deacons": 14, "Washington Huskies": 52,
         "Washington State Cougars": 53, "West Virginia Mountaineers": 39, "Wisconsin Badgers": 29, "SMU Mustangs": 70}

last_date = date(2025, 9, 3)
team_probabilities = []
for matchup in data:
    home_team = matchup['home_team']
    away_team = matchup['away_team']
    all_moneylines = matchup['bookmakers']
    home_team_odds = []
    away_team_odds = []
    gametime = matchup["commence_time"]
    print(f'{gametime=}')
    month = int(gametime[5: 7])
    day = int(gametime[8: 10])
    year = int(gametime[0: 4])
    game_date = date(year, month, day)
    if game_date <= last_date:
        for moneyline in all_moneylines:
            first_team_name = moneyline['markets'][0]['outcomes'][0]['name']
            second_team_name = moneyline['markets'][0]['outcomes'][1]['name']
            if first_team_name == home_team:
                home_team_odds.append(moneyline['markets'][0]['outcomes'][0]['price'])
                away_team_odds.append(moneyline['markets'][0]['outcomes'][1]['price'])
            elif first_team_name == away_team:
                away_team_odds.append(moneyline['markets'][0]['outcomes'][0]['price'])
                home_team_odds.append(moneyline['markets'][0]['outcomes'][1]['price'])
        try:
            home_moneyline_average = sum(home_team_odds) / len(home_team_odds)
            away_moneyline_average = sum(away_team_odds) / len(away_team_odds)
            home_win_probability_initial = 1 / home_moneyline_average
            away_win_probability_initial = 1 / away_moneyline_average
            total_win_probability = home_win_probability_initial + away_win_probability_initial
            home_win_probability = home_win_probability_initial / total_win_probability
            away_win_probability = away_win_probability_initial / total_win_probability
            # ZeroDivisionError occurs when there are no lines set for a matchup, so most of the time it will be a P5
            # matchup with a very bad opponent where Vegas won't want people to bet on it
        except ZeroDivisionError:
            home_win_probability = 0.99
            away_win_probability = 0.01

        # KeyError occurs when trying to find a team in the dict that isn't there (non P5 team)
        try:
            home_team_index = teams[home_team]
        except KeyError:
            home_team_index = 999
        try:
            away_team_index = teams[away_team]
        except KeyError:
            away_team_index = 999

        if home_team_index + away_team_index < 1200:
            team_probabilities.append((home_team_index, home_team, home_win_probability, away_team_index, away_team, away_win_probability))
            try:
                session.query(Football_Teams).filter(Football_Teams.id == teams_db[home_team]).update({"chance_to_win": round(home_win_probability, 3)})
            except KeyError:
                pass
            try:
                session.query(Football_Teams).filter(Football_Teams.id == teams_db[away_team]).update({"chance_to_win": round(away_win_probability, 3)})
            except KeyError:
                pass

        print(f"{home_team} (home): {home_win_probability}, {away_team} (away): {away_win_probability}, date: {game_date}")
    session.commit()

all_teams = session.query(Football_Teams)
for every_team in all_teams:
    print(f'{every_team.team} has a {every_team.chance_to_win}')
    if every_team.chance_to_win == 0.0 or every_team.chance_to_win == 1.0:
        print(f'updating odds to 0.99')
        session.query(Football_Teams).filter(Football_Teams.id == every_team.id).update({"chance_to_win": 0.99})
session.commit()

write_data = pandas.DataFrame(team_probabilities)
write_data.to_csv(f"implied_probabilities.csv", mode='w', header=False)