from flask import Flask

app = Flask(__name__)

@app.route('/', methods=['GET'])
def say_hi():
    return "hi"

@app.route('/api/hi', methods=['GET'])
def api_hi():
    return {"message": "hi"}

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
