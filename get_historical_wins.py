import requests
import pandas as pd
import time

API_KEY = "YuVJiwtjTbmZ+XUvpjipRfpdytZRSr7o29yj5saaXfntEvvVekIkOCcC+nYhPTAH"  # Get free key at collegefootballdata.com

TEAMS = [
    "Clemson", "Alabama", "Ohio State", "Oklahoma", "Georgia",
    "North Carolina", "Cincinnati", "Miami", "Texas A&M", "Iowa State",
    "Wisconsin", "UCF", "Washington", "Penn State", "Florida",
    "Notre Dame", "Arizona State", "Oregon", "USC", "Utah",
    "LSU", "Iowa", "Texas", "Houston", "Ole Miss",
    "Indiana", "Oklahoma State", "TCU", "Auburn", "Virginia Tech",
    "Boston College", "Kentucky", "Missouri", "UCLA", "Pittsburgh",
    "Wake Forest", "NC State", "West Virginia", "Louisville", "BYU",
    "Northwestern", "SMU", "Tennessee", "Nebraska", "Maryland",
    "California", "Virginia", "Mississippi State", "Florida State", "Kansas State",
    "Baylor", "Arkansas", "Georgia Tech", "Purdue", "Texas Tech",
    "Michigan State", "Colorado", "Rutgers", "Stanford", "South Carolina",
    "Illinois", "Duke", "Vanderbilt", "Syracuse", "Arizona",
    "Kansas", "Michigan", "Minnesota"
]

YEARS = [2021, 2022, 2023, 2024, 2025]

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Accept": "application/json"
}

def get_regular_season_wins(team, year):
    url = "https://api.collegefootballdata.com/games"
    params = {
        "year": year,
        "team": team,
        "season_type": "regular"
    }

    try:
        response = requests.get(url, headers=HEADERS, params=params)
        response.raise_for_status()
        games = response.json()

        wins = 0
        for game in games:
            print(f'{game}')
            # Determine if the team was home or away and if they won
            if game["homeTeam"] == team and game["homePoints"] is not None and game["awayPoints"] is not None and game['seasonType'] == 'regular':
                if game["homePoints"] > game["awayPoints"]:
                    if game["season"] == 2021 and game["week"] < 14:
                        wins += 1
                    elif game["season"] == 2022 and game["week"] < 14:
                        wins += 1
                    elif game["season"] == 2023 and game["week"] < 14:
                        wins += 1
                    elif game["season"] == 2024 and game["week"] < 15:
                        wins += 1
                    elif game["season"] == 2025 and game["week"] < 15:
                        wins += 1
            elif game["awayTeam"] == team and game["homePoints"] is not None and game["awayPoints"] is not None and game['seasonType'] == 'regular':
                if game["awayPoints"] > game["homePoints"]:
                    if game["season"] == 2021 and game["week"] < 14:
                        wins += 1
                    elif game["season"] == 2022 and game["week"] < 14:
                        wins += 1
                    elif game["season"] == 2023 and game["week"] < 14:
                        wins += 1
                    elif game["season"] == 2024 and game["week"] < 15:
                        wins += 1
                    elif game["season"] == 2025 and game["week"] < 15:
                        wins += 1

        return wins

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data for {team} in {year}: {e}")
        return None

def main():
    results = []

    for team in TEAMS:
        print(f"Fetching data for {team}...")
        team_data = {"team": team}

        for year in YEARS:
            wins = get_regular_season_wins(team, year)
            team_data[str(year)] = wins
            time.sleep(0.2)  # Small delay to avoid overwhelming the API

        results.append(team_data)
        print(f"  {team}: {[team_data[str(y)] for y in YEARS]}")

    # Save to CSV
    df = pd.DataFrame(results)
    df.set_index("team", inplace=True)
    df.to_csv("team_wins.csv")
    print("\nData saved to team_wins.csv")

    return df

if __name__ == "__main__":
    df = main()
    print("\nFinal Results:")
    print(df)
