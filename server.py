import cv2
from threading import Thread
import queue
from time import sleep, time
import socket
import numpy as np

socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
socket.bind(("127.0.0.1", 8080))
socket.listen(5)

video_format = "hls"
server_url = "http://localhost:8080"

last_timestamp = 0

stream = cv2.VideoCapture(0, cv2.CAP_DSHOW)
width = int(stream.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(stream.get(cv2.CAP_PROP_FRAME_HEIGHT))

#clients: list[socket] = []
last_added = time()
frames = queue.Queue(100)
data = []
running = True
clients_connected = 0
clients = []
frames_pending = 0

def sendFrame(array, l):
    for idx, client in enumerate(clients):
        try:
            client.sendall(l.to_bytes(4, 'big'))
            client.sendall(array)
        except:
            clients.remove(client)

def handleFrames(queue: queue.Queue):
    face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
    upper_cascade = cv2.CascadeClassifier('haarcascade_upperbody.xml')

    while running:
        timestamp, frame = queue.get()

        if time() - timestamp > 1:
            continue

        if not frame is None:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            bodies = upper_cascade.detectMultiScale(gray, 1.8, 2)
            
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)

            for (x, y, w, h) in bodies:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2)

            image = frame
            array = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 30])[1].tobytes()
            l = len(array)
            Thread(target=sendFrame, args=[array, l]).start()




def captureVideo(frames: queue.Queue, stream):
    global last_added, frames_pending

    print("Capturing")
    while running:
        ret, frame = stream.read()
        frames_pending += 1
        frames.put((time(), frame))
        sleep(1/30)


capture = Thread(target=captureVideo, args=[frames, stream])
capture.daemon = True

handler = Thread(target=handleFrames, args=[frames])
handler.daemon = True

handler.start()
capture.start()

def receive():
    global clients_connected
    (clientsocket, address) = socket.accept()
    clients_connected += 1
    clients.append(clientsocket)

recv = Thread(target=receive)
recv.daemon = True
recv.start()

try:
    while True:
        sleep(1)
except KeyboardInterrupt:
    print("Interrupt!")
    running = False
    stream.release()
    socket.close()
    exit()
