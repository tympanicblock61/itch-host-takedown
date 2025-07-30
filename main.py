import json
import os

import requests
from flask import Flask, render_template_string, redirect

from ItchIo import ItchIOClient
from customdns import monkey_patch_dns

SAVE_FILE = "progress.json"

def save_progress(page, taken_down):
    with open(SAVE_FILE, "w") as f:
        json.dump({"page": page, "taken_down": taken_down}, f, indent=4)

def load_progress():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r") as f:
            data = json.load(f)
            return data.get("page", 1), data.get("taken_down", [])
    return 1, []

def get_taken_down(itch: ItchIOClient):
    pages = 2
    page, taken_down = load_progress()

    try:
        while page < pages:
            print(f"📡 Fetching page {page}...")
            data = requests.get(f"https://loop-io.dev/api/games?page={page}").json()

            if pages == 2:
                pages = (data.get("totalGames", 0) + 49) // 50

            for game in data.get("games", []):
                url = game.get("itch_url")
                game_id = itch.get_game_id(url)

                if game_id is None:
                    print(f"⚠️ Could not get ID: {url}")
                    continue

                if itch.is_game_taken_down(game_id):
                    print(f"❌ Taken down: {game['title']}")
                    if game not in taken_down:
                        game["id"] = game_id
                        taken_down.append(game)
                else:
                    print(f"✅ {game.get('title')} is not taken down")

            page += 1
            save_progress(page, taken_down)

    except KeyboardInterrupt:
        print("🛑 Interrupted. Saving progress...")
        save_progress(page, taken_down)

    except Exception as e:
        print(f"❌ Error: {e}")
        save_progress(page, taken_down)

monkey_patch_dns()

API_KEY = input("Enter your Itch.io API key: ").strip()
itch = ItchIOClient(API_KEY)
get_taken_down(itch)
taken_down = load_progress()[1]
app = Flask(__name__)

@app.route('/')
def index():
    return render_template_string('''
        <h1>📁 Taken Down Games</h1>
        <ul>
        {% for game in games %}
            <li><a href="{{ url_for('game_page', game_id=game['id']) }}">{{ game['title'] }}</a></li>
        {% endfor %}
        </ul>
    ''', games=taken_down)

@app.route('/game/<int:game_id>')
def game_page(game_id):
    game = next((g for g in taken_down if g["id"] == game_id), None)
    if not game:
        return "Game not found", 404

    if not itch.is_game_taken_down(game_id):
        return "Game is not taken down", 404

    downloads = itch.get_game_downloads(game_id)

    return render_template_string('''
        <h2>{{ game["title"] }}</h2>
        <img src="{{ game["cover_image"] }}" alt="cover" style="width:300px;"><br>
        <p><a href="{{ game["itch_url"] }}">Itch.io</a></p>
        {% if game["patreon_url"] %}
            <p><a href="{{ game["patreon_url"] }}">Patreon</a></p>
        {% endif %}
        <p>❤️ Likes: {{ game["likes_count"] }}</p>
        <h3>Downloads</h3>
        {% if downloads %}
            <ul>
            {% for d in downloads %}
                <li>
                    {{ d["name"] }} ({{ d["filename"] }})
                    <form method="post" action="{{ url_for('download_file', game_id=game['id'], file_id=d['id']) }}">
                        <button type="submit">⬇️ Download</button>
                    </form>
                </li>
            {% endfor %}
            </ul>
        {% else %}
            <p>❌ Completely deleted by itch</p>
        {% endif %}
        <a href="/">⬅️ Back</a>
    ''', game=game, downloads=downloads)

@app.post('/game/<int:game_id>/download/<int:file_id>')
def download_file(game_id, file_id):
    downloads = itch.get_game_downloads(game_id)
    d = next((f for f in downloads if f["id"] == file_id), None)
    if not d:
        return "Download not found", 404

    return redirect(itch.get_download_url(file_id))

if __name__ == '__main__':
    print("🌐 Hosting on http://0.0.0.0:5000/")
    app.run(host="0.0.0.0", port=5000)
