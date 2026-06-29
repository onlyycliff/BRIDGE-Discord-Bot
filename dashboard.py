from flask import Flask, render_template, request, jsonify
from bridge_bot.bot import send_poll, start_bot, bot
import threading
import asyncio

dashboard = Flask(__name__)

@dashboard.route('/')
def home():
    return render_template('index.html')

@dashboard.route('/submit', methods=["POST"])
def submit():
    data = request.get_json()
    question = data["question"]
    option1 = data["option1"]
    option2 = data["option2"]
    
    future = asyncio.run_coroutine_threadsafe(send_poll(question, option1, option2))
    
    try:
        future.result(timeout=10)
    except Exception as e:
        return jsonify(f"Error occurred: {e}")
    
    print(data)
    # Process the submitted data
    return jsonify({"message": "Poll has been succesfully sent"})

def run_bot():
    start_bot()

















if __name__ == '__main__':
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    dashboard.run(debug=False)
    