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
def result_page(profile_url):
    steamid64 = None
    full_url = None
    avatar_url = None
    personaname = None
    profile_created = None
    location = None
    error = None

    if profile_url.isdigit():
        steamid64 = profile_url
        full_url = f"https://steamcommunity.com/profiles/{steamid64}/"
    elif "/" not in profile_url:
        try:
            rv = requests.get(
                "https://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/",
                params={"key": STEAM_API_KEY, "vanityurl": profile_url},
                timeout=5
            )
            rv.raise_for_status()
            resp = rv.json().get("response", {})
            if resp.get("success") == 1:
                steamid64 = resp.get("steamid")
                full_url = f"https://steamcommunity.com/profiles/{steamid64}/"
            else:
                error = "Vanity name not found"
        except:
            error = "Error contacting Steam API"
    else:
        candidate = profile_url if profile_url.startswith(("http://", "https://")) else "https://" + profile_url
        identifier = extract_identifier(candidate)
        if not identifier:
            error = "Invalid Steam community URL"
        else:
            if identifier.isdigit():
                steamid64 = identifier
            else:
                try:
                    rv = requests.get(
                        "https://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/",
                        params={"key": STEAM_API_KEY, "vanityurl": identifier},
                        timeout=5
                    )
                    rv.raise_for_status()
                    resp = rv.json().get("response", {})
                    if resp.get("success") == 1:
                        steamid64 = resp.get("steamid")
                    else:
                        error = "Vanity name not found"
                except:
                    error = "Error contacting Steam API"
            if steamid64:
                full_url = f"https://steamcommunity.com/profiles/{steamid64}/"

    if steamid64 and not error:
        try:
            ps = requests.get(
                "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/",
                params={"key": STEAM_API_KEY, "steamids": steamid64},
                timeout=5
            )
            ps.raise_for_status()
            players = ps.json().get("response", {}).get("players", [])
            if players:
                player = players[0]
                avatar_url = player.get("avatarfull")
                personaname = player.get("personaname")
                ts = player.get("timecreated")
                if ts:
                    profile_created = datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
                country = player.get("loccountrycode")
                if country:
                    location = country
        except:
            pass

    return render_template(
        "result.html",
        full_url=full_url,
        steamid64=steamid64,
        avatar_url=avatar_url,
        personaname=personaname,
        profile_created=profile_created,
        location=location,
        error=error,
        current_year=datetime.utcnow().year
    )


#Run the Flask application
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
