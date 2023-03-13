import os
import subprocess
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
fps = 20
width = int(stream.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(stream.get(cv2.CAP_PROP_FRAME_HEIGHT))

print(f"Video: {width}x{height}")

out = cv2.VideoWriter('appsrc ! videoconvert' + \
    ' ! x265enc speed-preset=ultrafast bitrate=900 key-int-max=10' + \
    ' ! rtspclientsink location=rtsp://192.168.1.197:8554/stream',
    cv2.CAP_GSTREAMER, 0, fps, (width, height), True)
if not out.isOpened():
    raise Exception("can't open video writer")

# ffmpeg_process = open_ffmpeg_stream_process()

#clients: list[socket] = []
last_added = time()
frames = queue.Queue()
data = []
running = True
clients_connected = 0
clients = []
frames_pending = 0

def open_ffmpeg_stream_process():
    print(f"{width}x{height}")
    args = (
        "ffmpeg -re -stream_loop -1 -f rawvideo -pix_fmt "
        f"bgr24 -s {width}x{height} -i pipe:0 -pix_fmt bgr24 "
        "-fflags nobuffer -rtsp_transport udp "
        "-avioflags direct "
        "-flags low_delay -strict experimental "
        "-f rtsp rtsp://192.168.1.197:8554/stream"
    ).split()
    return subprocess.Popen(args, stdin=subprocess.PIPE)


def handleFrames(queue: queue.Queue):
    face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

    while running:
        timestamp, frame = queue.get()

        if time() - timestamp > 2:
            print("Out of sync!")
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)

        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)

        image = frame
        #array = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 30])[1].tobytes()
        #ffmpeg_process.stdin.write(image.astype(np.uint8).tobytes())
        out.write(image)




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
