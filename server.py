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

clients = []
nickname_to_key = {}
nicknames = []


def broadcast(msg):
    for client in clients:
        client.send(msg)


def broadcast_encrypted(msg):
    decrypted_msg = rsa.decrypt(msg, private_key).decode('utf-8')
    print(decrypted_msg)
    for client in clients:
        nickname = nicknames[clients.index(client)]
        encrypted_msg = rsa.encrypt(decrypted_msg.encode('utf-8'), nickname_to_key[nickname])
        client.send(encrypted_msg)


def handle(client):
    while True:
        try:
            msg = client.recv(2048)
            client_nickname = nicknames[clients.index(client)]
            print(f"{client_nickname} wants to send an encrypted message.")
            broadcast_encrypted(msg)
        except:
            index = clients.index(client)
            clients.remove(client)
            client.close()
            nickname = nicknames[index]
            broadcast(f'b:{nickname} has left the chat.').encode('utf-8')
            nicknames.remove(nickname)
            break

def receive():
    while True:
        client, address = server.accept()   #new connection
        print(f"New connection from {str(address)}")

        client.send("s:setup".encode('utf-8'))
        nickname = client.recv(2048).decode()
        print(f"Received nickname: {nickname}")
        nicknames.append(nickname)

        public_key_pem = client.recv(2048)
        client_public_key = rsa.PublicKey.load_pkcs1(public_key_pem)
        nickname_to_key[nickname] = client_public_key

        public_key_pem = public_key.save_pkcs1('PEM')
        client.send(public_key_pem)

        print(f'Nickname of the client is {nickname}')

        time.sleep(2)
        broadcast(f"b:{nickname} has joined the chat.\n".encode('utf-8'))
        clients.append(client)
        client.send("b:Welcome to your encrypted chat.\nYou are now connected!\n".encode('utf-8'))

        threading.Thread(target=handle, args=(client,)).start()

print('Server now listening...')
receive()