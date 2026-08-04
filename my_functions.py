import json.decoder
from datetime import date, datetime
import pandas
import requests
import os, os.path
import time
import random

"""
Functions for the KCFB website
"""


"""
This function is used to determine which week number it is in the season. It returns the week number and postseason as 
False. After conference championships, it will return week 1 and postseason as True. The API puts all playoff games
into week 1 of the postseason
"""

def determine_week_number():
    week_cutoffs = [date(2025, 9, 1), date(2025, 9, 8), date(2025, 9, 15), date(2025, 9, 22), date(2025, 9, 29),
                    date(2025, 10, 6), date(2025, 10, 13), date(2025, 10, 20), date(2025, 10, 27), date(2025, 11, 3),
                    date(2025, 11, 10), date(2025, 11, 17), date(2025, 11, 24), date(2025, 12, 1), date(2025, 12, 9)]
    today = date.today()
    week = ""
    postseason = False

    for item in week_cutoffs:
        if today < item:
            week = week_cutoffs.index(item) + 1
            if week == 0:
                week = 1
            break

    if week == "":
        if date(2026, 1, 1) < date.today():
            week = 2
        else:
            week = 1
        postseason = True

    return week, postseason


"""
This function will read the people and their respective teams from any given league (saved as a csv) and will return a
dictionary with the person and their total score. This can be used for any given week and only needs to have a
dictionary passed in that has the win total (or points) for every respective school. That dictionary is then read and
is used to determine the total for every person in the league
"""

def determine_scores(points_dict, league_number):
    data = pandas.read_csv(f"Leagues/League{league_number}.csv", encoding='latin-1')
    player_teams = data.to_dict()
    score_dict = {}
    for person in player_teams:
        this_week_score = 0
        for i in range(0, 4):
            team = player_teams[person][i]
            try:
                this_week_score += points_dict[team]
            except KeyError:
                pass
        score_dict[person] = this_week_score
    del score_dict['Unnamed: 0']

    return score_dict


"""
This function requests the college football API to get the game data. It will take any given year (int), week (int), and
team (str)
"""

def get_game_data(year, week, team, postseason):
    if postseason:
        url = f"https://api.collegefootballdata.com/games?year={year}&week={week}&seasonType=postseason&team={team}"
    else:
        # url = f"https://api.collegefootballdata.com/games?year={year}&week={week}&seasonType=regular&team={team}"
        url = f"https://api.collegefootballdata.com/games?year={year}&week={week}&team={team}"

    headers = {
        'accept': 'application/json',
        'Authorization': 'Bearer YuVJiwtjTbmZ+XUvpjipRfpdytZRSr7o29yj5saaXfntEvvVekIkOCcC+nYhPTAH',
    }

    response = requests.get(url, headers=headers)
    try:
        data = response.json()
    except json.decoder.JSONDecodeError:
        print('JSON decode error. maybe it was a timeout. sleeping for 20 secs and trying again')
        time.sleep(20)
        response = requests.get(url, headers=headers)
        data = response.json()
    return data

"""
This function will delete the initial key that Panda makes with the row numbers (Unnamed). It also simplifies it so
that the key (person) will only have a list as the value rather than a list of dictionaries
"""


def convert_dict_to_simple_dict(dict):
    if dict["Unnamed: 0"]:
        del dict["Unnamed: 0"]
    dict_final = {}
    for item in dict:
        list = []
        for i in range(0, 4):
            try:
                team = dict[item][i]
                list.append(team)
            except KeyError:
                break
        dict_final[item] = list
    return dict_final



def upcoming_games_master(teams_dict, year):
    test = True
    games = {}
    weekDays = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
    if test:
        week = 14
        day_of_week = 1
    else:
        var = datetime.now()
        day_of_week = datetime.weekday(var)
        week = determine_week_number() + 1

    if day_of_week == 1:
        for team in teams_dict:
            print(team)
            game = get_game_data(year, week, team.replace("&", "%26"))
            i = 0

            try:
                if game[i]["home_team"] == team:
                    start_date = game[i]["start_date"].split("T")[0].split("-")
                    start_day_as_input = [int(item) for item in start_date]
                    date = datetime.date(start_day_as_input[0], start_day_as_input[1], start_day_as_input[2])
                    start_day_as_output = datetime.weekday(date)
                    start_day = weekDays[start_day_as_output]
                    games[team] = {"opponent": game[i]["away_team"], "start_day": start_day}
                else:
                    home_team = game[i]["home_team"]
                    start_date = game[i]["start_date"].split("T")[0].split("-")
                    start_day_as_input = [int(item) for item in start_date]
                    date = datetime.date(start_day_as_input[0], start_day_as_input[1], start_day_as_input[2])
                    start_day_as_output = datetime.weekday(date)
                    start_day = weekDays[start_day_as_output]
                    games[home_team] = {"opponent": team, "start_day": start_day}
            except KeyError:
                pass
            except IndexError:
                pass
            i += 1

        write_data = pandas.DataFrame(games, index=["opponent", "start_day", "sort_points"])
        write_data.to_csv(f"This_weeks_games.csv")

        number_of_leagues = len([name for name in os.listdir('Leagues')])
        league = 1

        while league <= number_of_leagues:
            data = pandas.read_csv(f"Leagues/League{league}.csv", encoding='latin-1')
            league_games = games
            players_teams_initial = data.to_dict()
            players_teams = convert_dict_to_simple_dict(players_teams_initial)
            for team in league_games:
                # print(f"opponent: {league_games[team]['opponent']}")
                sort_points = 0
                for player in players_teams:
                    if team in players_teams[player]:
                        sort_points += 1
                    if league_games[team]["opponent"] in players_teams[player]:
                        sort_points += 1
                    if sort_points == 2:
                        break
                league_games[team]["sort_points"] = sort_points

            league_games = dict(sorted(league_games.items(), key=lambda kv: kv[1]["sort_points"], reverse=True))
            write_data = pandas.DataFrame(league_games, index=["opponent", "start_day", "sort_points"])
            write_data.to_csv(f"This_Weeks_Games/League{league}.csv")
            league += 1

def get_rankings(year, week, postseason):
    # If it's the postseason, API still needs to be queried like regular season. Last reg season AP poll was week 15
    if postseason:
        week = 15
    url = f"https://api.collegefootballdata.com/rankings?year={year}&week={week}&seasonType=regular"

    headers = {
        'accept': 'application/json',
        'Authorization': 'Bearer YuVJiwtjTbmZ+XUvpjipRfpdytZRSr7o29yj5saaXfntEvvVekIkOCcC+nYhPTAH',
    }

    response = requests.get(url, headers=headers)
    data = response.json()
    # print(f'{data=}')
    # print(data[0]['polls'][2])
    # print(data[0]['polls'][3])
    # print(data[0]['polls'][4])
    return data


"""
This function saves a csv with a dictionary where the key is the team and the value is a list of 0s and 1s to represent
that team's score. It's done this way so that the user can select what week they want to see the scores for. This csv
will be used in the future to allow every league to use a master spreadsheet where the team's wins will be summed up
This function also saves the previous results for every team to a txt file. Each team has their own txt file
"""


def save_data(league_number, new_teams, year, teams_dict):
    data = pandas.read_csv(f"Leagues/League{league_number}.csv", encoding='latin-1')
    initial_dict = data.to_dict()
    week = 14
    for team in new_teams:
        print(team)
        time.sleep(0.5)
        week_data = get_game_data(year, week, team)
        i = 0
        score = 0
        while i < len(week_data):
            game = week_data[i]
            print(game)

            home_team = game["home_team"]
            home_score = game["home_points"]
            away_team = game["away_team"]
            away_score = game["away_points"]

            try:
                if home_score > away_score:
                    winner = home_team
                    loser = away_team
                else:
                    winner = away_team
                    loser = home_team

                if winner == team.replace("%26", "&"):
                    score += 1
                    try:
                        with open(f"Team_Results/{team}.txt", 'r', encoding='ISO-8859-1') as file:
                            text = file.read()
                            results = text.split(",")
                    except FileNotFoundError:
                        results = []
                    with open(f"Team_Results/{team}.txt", 'a+', encoding='ISO-8859-1') as file:
                        if len(results) == 0:
                            file.write(f"W {loser.replace('%26', '&')},")
                        else:
                            most_recent_result = results[-2]
                            if most_recent_result != f"W {loser.replace('%26', '&')}":
                                file.write(f"W {loser.replace('%26', '&')},")
                else:
                    try:
                        with open(f"Team_Results/{team}.txt", 'r', encoding='ISO-8859-1') as file:
                            text = file.read()
                            results = text.split(",")
                    except FileNotFoundError:
                        results = []
                    with open(f"Team_Results/{team}.txt", 'a+', encoding='ISO-8859-1') as file:
                        if len(results) == 0:
                            file.write(f"L {winner.replace('%26', '&')},")
                        else:
                            most_recent_result = results[-2]
                            if most_recent_result != f"L {winner.replace('%26', '&')}":
                                file.write(f"L {winner.replace('%26', '&')},")

            except TypeError:
                pass

            i += 1
        teams_dict[team.replace("%26", "&")].append(score)

def get_password_list():
    words = pandas.read_csv("List of words.csv", header=None)
    words_dict = words.to_dict()
    passwords = []
    counter = 0
    all_words = []
    words_dict_refined = words_dict[0]
    while counter < len(words_dict_refined):
        all_words.append(words_dict_refined[counter])
        counter += 1

    i = 0
    while i < 20:
        word = random.choice(words_dict_refined)
        numbers = random.randint(10000, 99999)
        prefix_or_suffix = random.randint(0, 1)
        if prefix_or_suffix == 0:
            password = f"{numbers}{word}"
        else:
            password = f"{word}{numbers}"
        passwords.append(password)
        i += 1
    return passwords

def return_calendar_day(input_date):
    dict = {0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday", 4: "Friday", 5: "Saturday", 6: "Sunday"}
    day_of_week = input_date.weekday()
    calendar_day = dict[day_of_week]
    return calendar_day