import cv2
from threading import Thread
import queue
from time import sleep, time
import socket
import numpy as np
import time

socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
socket.connect(("localhost", 8080))

prev = time.time()

images = queue.Queue()

def receive():
    while True:
        data = b""
        size_data = int.from_bytes(socket.recv(4), "big")
        print(f"\r{int(size_data/1000)}KB", end="")

        while len(data) < size_data:
            data += socket.recv(size_data)
        images.put(data)

a = Thread(target=receive)
a.daemon = True
a.start()

while True:
    img = images.get()

    mt = np.frombuffer(img, dtype="uint8")

    img = cv2.imdecode(mt, cv2.IMREAD_COLOR)

    cv2.imshow("Image", img)
    cv2.waitKey(1)