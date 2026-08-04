import json.decoder
from datetime import date, datetime
import pandas
import requests
import os, os.path
import time
import random

# 8/4/26: limited copy of my_functions
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