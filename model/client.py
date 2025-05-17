import zmq

def client_send_image(image_path, server_addr="tcp://localhost:5555"):
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect(server_addr)

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    socket.send(image_bytes)
    message = socket.recv()
    print("Prediction from server:", message.decode())

if __name__ == "__main__":
    # Change "dog.webp" to your test image filename here
    client_send_image("dog.webp", "tcp://localhost:5555")
