from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/submit', methods=["POST"])
def submit():
    data = request.get_json()
    print(data)
    # Process the submitted data
    return jsonify({"message": "Data received"})



















if __name__ == '__main__':
    app.run(debug=True)
    