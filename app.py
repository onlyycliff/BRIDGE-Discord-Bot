from flask import Flask, render_template, request, jsonify
from bridge_bot.bot import send_poll, start_bot, bot
import threading
import asyncio

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/submit', methods=["POST"])
def submit():
    data = request.get_json()
    question = data["question"]
    option1 = data["option1"]
    option2 = data["option2"]
    
    bot.loop.create_task(send_poll(question, option1, option2))
    print(data)
    # Process the submitted data
    return jsonify({"message": "Data received"})

def run_bot():
    start_bot()

















if __name__ == '__main__':
    threading.Thread(target=run_bot).start()
    app.run(debug=True)
    