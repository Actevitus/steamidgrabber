import os
import re
import logging
import requests
from datetime import datetime
from flask import Flask, render_template
from dotenv import load_dotenv

#Load the environment variables and handle potential errors
load_dotenv()
STEAM_API_KEY = os.getenv("STEAM_API_KEY")
if not STEAM_API_KEY:
    raise RuntimeError("Missing STEAM_API_KEY in environment or .env file")

logging.basicConfig(level=logging.DEBUG)
app = Flask(__name__)

#Function to extract the identifier from the Steam community URL
def extract_identifier(url: str) -> str | None:
    m = re.search(r"steamcommunity\.com/(?:id|profiles)/([^/]+)", url, re.IGNORECASE)
    return m.group(1) if m else None

#Main route to render the index page
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", current_year=datetime.utcnow().year)

@app.route("/<path:profile_url>")

#Route to handle the result page and fetch Steam profile information
def result_page(profile_url):
    full_url = profile_url if profile_url.startswith(("http://", "https://")) else "https://" + profile_url
    identifier = extract_identifier(full_url)
    steamid64 = None
    avatar_url = None
    personaname = None
    profile_created = None
    location = None
    error = None

# Check if the URL is valid
    if not identifier:
        error = "Invalid Steam community URL"
    else:
        #Check if the identifier is a valid Steam ID
        if identifier.isdigit():
            steamid64 = identifier
        else:
            try:
                #Attempt to resolve the vanity URL to a Steam ID
                rv = requests.get(
                    "https://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/",
                    params={"key": STEAM_API_KEY, "vanityurl": identifier},
                    timeout=5
                )
                #Check for a successful response
                rv.raise_for_status()
                data = rv.json().get("response", {})
                if data.get("success") == 1:
                    steamid64 = data.get("steamid")
                else:
                    error = "Vanity name not found"
            except Exception as e:
                logging.debug(f"Error resolving vanity URL: {e}", exc_info=True)
                error = "Error contacting Steam API"

    if steamid64 and not error:
        try:
            #Fetch player summary information using the Steam ID
            ps = requests.get(
                "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/",
                params={"key": STEAM_API_KEY, "steamids": steamid64},
                timeout=5
            )
            #Check for a successful response
            ps.raise_for_status()
            players = ps.json().get("response", {}).get("players", [])
            #Extract player information from the response
            if players:
                player = players[0]
                avatar_url = player.get("avatarfull")
                personaname = player.get("personaname")
                time_created_ts = player.get("timecreated")
                if time_created_ts:
                    profile_created = datetime.utcfromtimestamp(time_created_ts).strftime("%Y-%m-%d")
                loc_country = player.get("loccountrycode")
                if loc_country:
                    location = loc_country
        except Exception as e:
            logging.debug(f"Error fetching player summary: {e}", exc_info=True)
            # ignore additional info failures

    #Render the result page and pass the fetched data to the template
    return render_template(
        "result.html",
        full_url=full_url,
        steamid64=steamid64,
        avatar_url=avatar_url,
        personaname=personaname,
        profile_created=profile_created,
        location=location,
        error=error,
    )

#Run the Flask application
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
