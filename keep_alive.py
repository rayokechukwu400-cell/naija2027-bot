from flask import Flask
from threading import Thread

app = Flask(__name__)


@app.route("/")
def home():
    return "🇳🇬 naija2027election_bot is running!", 200


@app.route("/health")
def health():
    return {"status": "ok", "bot": "naija2027election_bot"}, 200


def run():
    app.run(host="0.0.0.0", port=8080, debug=False)


def keep_alive():
    t = Thread(target=run, daemon=True)
    t.start()
    print("🌐 Keep-alive web server started on port 8080.")
