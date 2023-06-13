import eventlet
import socketio

sio = socketio.Server(cors_allowed_origins="http://localhost:3000")
app = socketio.WSGIApp(sio, static_files={
    '/': {'content_type': 'text/html', 'filename': 'index.html'}
})

@sio.event
def connect(sid, environ):
    print('connect ', sid)

@sio.on('message')
def my_message(sid, data):
    print('message ', data)

@sio.on('node_data')
def my_message(sid, data):
    sio.emit("node_call", data)


    print('node_data ', data)

@sio.event
def disconnect(sid):
    print('disconnect ', sid)

if __name__ == '__main__':
    eventlet.wsgi.server(eventlet.listen(('', 5000)), app)
