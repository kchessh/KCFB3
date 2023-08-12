from bs4 import BeautifulSoup
import requests
import json
import pprint
import re
import pandas as pd

response = requests.get(f"https://www.sportsbettingdime.com/college-football/win-totals-best-odds/")

text = response.text
soup = BeautifulSoup(text, "html.parser")

'teams_raw uses the class "table-responsive" to get the data'
teams_raw = str(soup.select(selector=".table-responsive"))
print(teams_raw)

teams = re.findall('(?:<td>)([\w\s\&\;-]*)(?:<\/td>)', teams_raw)
wins = re.findall('(?:<td>)([0-9]+\.[0-9]*)(?:<\/td>)', teams_raw)

dict = dict(zip(teams, wins))
print(dict)

with open("Teams.txt", encoding='ISO-8859-1') as file:
    text = file.read()
    eligible_teams = text.split(",")
    new_dict = {team: win for (team, win) in dict.items() if team in eligible_teams}

print(new_dict)
write_data = pd.DataFrame(new_dict, index=['wins', 'wins'])
write_data.to_csv("Expected_wins.csv")