import threading
import socket
import time
import rsa


host = '127.0.0.1'
port = 9999

public_key, private_key = rsa.newkeys(1024)

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((host, port))
server.listen()
server.settimeout(1.0)

clients = []
client_threads = []
nicknames = []
nickname_to_key = {}

running = True


def broadcast(msg):
    for client in clients:
        client.send(msg)


def broadcast_encrypted(msg):
    decrypted_msg = rsa.decrypt(msg, private_key).decode('utf-8')
    for client in clients:
        nickname = nicknames[clients.index(client)]
        encrypted_msg = rsa.encrypt(decrypted_msg.encode('utf-8'), nickname_to_key[nickname])
        client.send(encrypted_msg)


def handle(client):
    global running
    while running:
        try:
            msg = client.recv(2048)
            if running:
                broadcast_encrypted(msg)
        except ConnectionResetError as e:
            index = clients.index(client)
            clients.remove(client)
            client.close()
            nickname = nicknames[index]
            if len(clients):
                broadcast(f'b:{nickname} has left the chat.'.encode('utf-8'))
            print(f"{nickname} has left the chat.")
            nicknames.remove(nickname)
            break
        except Exception as e:
            print(f"Unexpected error: {e}")
            break

def receive():
    global running
    while running:
        try:
            client, address = server.accept()   #new connection
            print(f"New connection from {str(address)}")

            client.send("s:setup".encode('utf-8'))
            nickname = client.recv(2048).decode()
            nicknames.append(nickname)

            public_key_pem = client.recv(2048)
            client_public_key = rsa.PublicKey.load_pkcs1(public_key_pem)
            nickname_to_key[nickname] = client_public_key

            public_key_pem = public_key.save_pkcs1('PEM')
            client.send(public_key_pem)

            print(f'The connection from {address} chose the nickname {nickname}')

            time.sleep(2)
            broadcast(f"b:{nickname} has joined the chat.\n".encode('utf-8'))
            clients.append(client)
            client.send("b:Welcome to your encrypted chat.\nYou are now connected!\n".encode('utf-8'))

            thread = threading.Thread(target=handle, args=(client,))
            thread.start()
            client_threads.append(thread)
        except socket.timeout:
            continue
        except Exception as e:
            print(f"Server error: {e}")
    for client in clients:
        client.close()
    server.close()


if __name__ == "__main__":
    server_thread = threading.Thread(target=receive)
    server_thread.start()

    print("Server now listening..\nType q to quit.")
    while input("") != 'q':
        pass
    running = False  # Signal server loop to stop
    print("Beginning Server Shutdown...")
    time.sleep(1.5)
    print("Gracefully shutting down clients...")
    if clients:
        broadcast("b:shutdown".encode('utf-8'))
    time.sleep(3)
    server_thread.join()  # Wait for the server thread to finish
    print("Server shutdown complete.")