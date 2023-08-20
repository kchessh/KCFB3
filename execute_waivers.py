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
import cases

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

reset = False
if reset:
    cases.case2()
# all_teams = session.query(Football_Teams).all()
# for team in all_teams:
#     print(f"{team.team},{team.id}")

# all_info = session.query(Player_weekly_info).filter(Player_weekly_info.league == 48).all()
# for info in all_info:
#     print(f"{info.id}, {info.user_id}. team_1:{info.team_1} team_2:{info.team_2} team_3:{info.team_3} team_4:{info.team_4}")

else:
    all_leagues = session.query(League).all()
    for league in all_leagues:
        all_waivers = session.query(Waiver_Info).filter(Waiver_Info.league == league.id).all()

        # Add all waivers to the history of waivers table so people can see all their historical waivers that either
        # were or were not processed
        for waiver in all_waivers:
            waiver_to_add_to_history = HistoryOfWaivers(id=waiver.id, user_id=waiver.user_id, league=waiver.league,
                team_to_add_id=waiver.team_to_add_id, team_to_drop_id=waiver.team_to_drop_id,
                faab_submitted=waiver.faab_submitted, priority=waiver.priority)

        if len(all_waivers) > 0:
            print(all_waivers)
            waiver_list = []
            waiver_list_sorted = []
            teams_assigned = []
            faabs_dict = {person.user_id: person.faab for person in session.query(Player_weekly_info).filter(Player_weekly_info.league == league.id).all()}
            print(f"faabs_dict: {faabs_dict}")
            completed_waiver_list = []
            for waiver in all_waivers:
                # Create waiver list to iterate through for assigning teams to the highest bidder
                waiver_list.append([waiver.user_id, waiver.team_to_add_id, waiver.team_to_drop_id, waiver.faab_submitted, waiver.id])
                waiver_list_sorted = sorted(waiver_list, key=lambda waiver: waiver[3], reverse=True)
            while len(waiver_list_sorted) > 0:
                # Get the highest bid data. User's priorities are determined by amount of faab bid (i.e. if a user bid 10 on team1 and 12 on team2, it will try to give them team2 before team 1
                print(f"waiver_list_sorted: {waiver_list_sorted}")
                highest_bid = waiver_list_sorted[0]
                print(f"waiver_id: {highest_bid[4]}")

                # Figure out if the highest bid has no matching bids. If there are matching bids, award a team to the person with the lowest score. Else, do a RNG to determine who gets the team
                go_on = True
                match_counter = 1
                while go_on:
                    if highest_bid[3] == waiver_list_sorted[match_counter][3]:
                        match_counter += 1
                        highest_bidder_league_points = session.query(Player_weekly_info).filter(Player_weekly_info.league == league.id).filter(Player_weekly_info.user_id == highest_bidder)
                        other_bidder_league_points = session.query(Player_weekly_info).filter(Player_weekly_info.league == league.id).filter(Player_weekly_info.user_id == waiver_list_sorted[match_counter][0])
                        if highest_bidder_league_points > other_bidder_league_points:
                            highest_bid = waiver_list_sorted[match_counter]
                    else:
                        go_on = False

                highest_bidder = highest_bid[0]
                team_to_add_id = highest_bid[1]
                team_to_drop_id = highest_bid[2]
                faab_submitted = highest_bid[3]

                # Calling this before the first waiver is even executed to ensure someone wasn't somehow able to submit a waiver with more faab than they have available
                for waiver in reversed(waiver_list_sorted):
                    # Delete waivers for everyone who lost the bid for the awarded team
                    if waiver[1] == team_to_add_id:
                        print(f"{waiver} deleted due to someone trying to add a team that was already awarded")
                        waiver_list_sorted.remove(waiver)
                        waiver_to_delete = session.query(Waiver_Info).filter(Waiver_Info.id == waiver[4]).first()
                        session.delete(waiver_to_delete)

                    # Delete waivers where the faab submitted exceeds faab remaining after awarding team
                    elif waiver[3] > faabs_dict[highest_bidder]:
                        print(f"{waiver} deleted due to the user who won the most recent team not having enough faab to win another team")
                        waiver_list_sorted.remove(waiver)
                        waiver_to_delete = session.query(Waiver_Info).filter(Waiver_Info.id == waiver[4]).first()
                        session.delete(waiver_to_delete)

                    elif waiver[0] == highest_bidder and waiver[2] == team_to_drop_id:
                        print(f"{waiver} deleted due to the user who won the most recent team trying to drop the team they just dropped")
                        waiver_list_sorted.remove(waiver)
                        waiver_to_delete = session.query(Waiver_Info).filter(Waiver_Info.id == waiver[4]).first()
                        session.delete(waiver_to_delete)

                # Db is setup with 4 teams, each having their own column. We need to figure out which of the user's 4 teams are being dropped so the correct team can be dropped
                # for the correct team to be added (i.e. if someone wants to drop team A for team B, we need to figure out if team A is in the team_1, team_2, team_3, or team_4 column
                winner_teams = session.query(Player_weekly_info).filter(Player_weekly_info.user_id == highest_bidder, Player_weekly_info.league == league.id).first()
                winner_teams_dict = {int(winner_teams.team_1): "team_1", int(winner_teams.team_2): "team_2", int(winner_teams.team_3): "team_3", int(winner_teams.team_4): "team_4"}

                current_faab = faabs_dict[highest_bidder]
                # Update the new Player_weekly_info table with the new team replacing the old team and the submitted faab subtracted from the original faab
                # KeyError should be due to waiver being deleted due to someone somehow placing a bid with more faab than they had available
                if current_faab - faab_submitted >= 0:
                    try:
                        session.query(Player_weekly_info).filter(Player_weekly_info.user_id == highest_bidder, Player_weekly_info.league == league.id).update({str(winner_teams_dict[team_to_drop_id]): team_to_add_id, "faab": current_faab - faab_submitted})
                        executed_waiver = Executed_Waivers_update1(user_id=highest_bidder, league=league.id, added_team=team_to_add_id, dropped_team=team_to_drop_id, faab_used=faab_submitted)
                        session.add(executed_waiver)
                        faabs_dict[highest_bidder] -= faab_submitted
                        print(f"new faabs_dict: {faabs_dict}")
                        completed_waiver_list.append(highest_bid)
                    except KeyError:
                        pass

            print(waiver_list_sorted)
            print(completed_waiver_list)
    session.commit()

player_11 = session.query(Player_weekly_info).filter(Player_weekly_info.user_id == 11, Player_weekly_info.league == 48).first()
player_13 = session.query(Player_weekly_info).filter(Player_weekly_info.user_id == 13, Player_weekly_info.league == 48).first()
player_7 = session.query(Player_weekly_info).filter(Player_weekly_info.user_id == 7, Player_weekly_info.league == 48).first()
print(f"player_11: {player_11.team_1}, {player_11.team_2}, {player_11.team_3}, {player_11.team_4}, {player_11.faab}")
print(f"player_13: {player_13.team_1}, {player_13.team_2}, {player_13.team_3}, {player_13.team_4}, {player_13.faab}")
print(f"player_7: {player_7.team_1}, {player_7.team_2}, {player_7.team_3}, {player_7.team_4}, {player_7.faab}")

executed_waivers = session.query(Executed_Waivers_update1).all()
for waiver in executed_waivers:
    print(f"user_id: {waiver.user_id}, league: {waiver.league}, added_team: {waiver.added_team}, "
          f"dropped_team: {waiver.dropped_team}, faab_used: {waiver.faab_used}, time_and_date_added: {waiver.date_and_time_added}")