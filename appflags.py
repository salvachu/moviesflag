from flask import Flask, render_template, jsonify
import requests
import json

app = Flask(__name__)

def get_worldcup_teams():
    url = "https://worldcupjson.net/teams"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print("Failed to retrieve World Cup teams data.")
        return None

def get_country_flag(alpha_code):
    if alpha_code=='eng' or alpha_code=='wal':
        alpha_code = 'GBR'
    url = f"https://restcountries.com/v3.1/alpha/{alpha_code}"
    response = requests.get(url)
    if response.status_code == 200:
        country_data = response.json()
        if country_data:
            return country_data[0].get("flags", {}).get("svg", None)
    print(f"Failed to retrieve flag for country code: {alpha_code}")
    return None

def merge_data_with_flags(worldcup_teams):
    merged_data = []

    for group in worldcup_teams["groups"]:
        print(group)
        for team in group["teams"]:
            country_code = team.get("country", "").lower()
            flag = get_country_flag(country_code)
        
            team_data_with_flag = {
                 "name": team.get("name"),
                 "country_code": team.get("country"),
                 "group": team.get("group_letter"),
                 "flag": flag
            }
            merged_data.append(team_data_with_flag)

    return merged_data

def main():
    # Get the World Cup teams data
    worldcup_teams = get_worldcup_teams()
    if worldcup_teams is None:
        return

    # Merge World Cup data with country flags
    merged_data = merge_data_with_flags(worldcup_teams)
    
    # Output the combined data as JSON
    with open("worldcup_teams_with_flags.json", "w") as file:
        json.dump(merged_data, file, indent=4)
    
    print("Data saved to worldcup_teams_with_flags.json")

@app.route("/")
def index():
    # Fetch combined data
    worldcup_teams = get_worldcup_teams()
    teams_with_flags = merge_data_with_flags(worldcup_teams)
    print(teams_with_flags)
    return render_template("index.html", teams=teams_with_flags)

@app.route("/api/teams")
def api_teams():
    worldcup_teams = get_worldcup_teams()
    teams_with_flags = merge_data_with_flags(worldcup_teams)
    return jsonify(teams_with_flags)

if __name__ == "__main__":
    app.run(debug=True)

