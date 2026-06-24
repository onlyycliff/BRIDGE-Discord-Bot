from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/')
def hello():
    return "Hello, World!"

@app.route('/submit', methods=["POST"])
def submit():
    data = request.get_json()
    print(data)
    # Process the submitted data
    return jsonify({"message": "Data received"})



















if __name__ == '__main__':
    app.run(debug=True)
    