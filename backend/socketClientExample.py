import socketio
from flask import Flask, jsonify, request

sio = socketio.Client()

@sio.event
def connect():
    print('connection established')

@sio.event
def my_message(data):
    print('message received with ', data)
    sio.emit('node_data', data)

@sio.event
def disconnect():
    print('disconnected from server')

sio.connect('http://localhost:5000')
app = Flask(__name__)
@app.route('/add', methods=['POST'])
def getdata():
    values = request.get_json()
    data = values.get('data')
    my_message(data)
    return jsonify(), 200

if __name__ == '__main__':
    app.run('0.0.0.0', '9999')
sio.wait()
