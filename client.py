import pickle
import socket
import threading
import tkinter as tk
import tkinter.scrolledtext
from tkinter import simpledialog
import rsa

HOST = '127.0.0.1'
PORT = 9999


class Client:
    def __init__(self, host, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))
        self.public_key, self.private_key = rsa.newkeys(1024)
        self.server_public_key = None

        self.gui_done = False
        self.running = True
        self.start_screen()

    def start_screen(self):
        self.start_win = tk.Tk()
        self.start_win.title("Encrypted ChatRoom")
        self.start_win.geometry("520x333")  # Width x Height
        self.start_win.configure(bg="#282a36")

        # Label
        lbl = tk.Label(self.start_win, text="Welcome to your encrypted chat.\n Any message sent will be protected from MitM attacks", bg="#282a36", fg="#f8f8f2")
        lbl.config(font=("Helvetica", 12))
        lbl.pack(pady=(50, 10))

        lbl = tk.Label(self.start_win, text="Enter your nickname:", bg="#282a36", fg="#f8f8f2")
        lbl.config(font=("Helvetica", 12))
        lbl.pack(pady=(50, 10))

        # Nickname Entry
        self.nickname_entry = tk.Entry(self.start_win, font=("Helvetica", 12), justify="center")
        self.nickname_entry.pack(ipadx=50, ipady=6)

        # Join Button
        join_btn = tk.Button(self.start_win, text="Join Chat", command=self.join_chat,
                             font=("Helvetica", 12), bg="#50fa7b", fg="#282a36", relief="flat")
        join_btn.pack(pady=(20, 0), ipadx=10, ipady=5)

        self.start_win.mainloop()

    def join_chat(self):
        self.nickname = self.nickname_entry.get()
        if self.nickname:
            self.start_win.destroy()
            threading.Thread(target=self.receive).start()
            threading.Thread(target=self.gui_loop).start()

    def gui_loop(self):
        self.win = tkinter.Tk()
        self.win.configure(bg="lightgray")

        self.chat_label = tkinter.Label(self.win, text="Encrypted Chat Room:", bg="lightgray")
        self.chat_label.config(font=("Arial", 12))
        self.chat_label.pack(padx=20, pady=5)

        self.text_area = tkinter.scrolledtext.ScrolledText(self.win)
        self.text_area.pack(padx=20, pady=5)
        self.text_area.config(state='disabled')

        self.msg_label = tkinter.Label(self.win, text="Message:", bg="lightgray")
        self.msg_label.config(font=("Arial", 12))
        self.msg_label.pack(padx=20, pady=5)

        self.input_area = tkinter.Text(self.win, height=3)
        self.input_area.pack(padx=20, pady=5)

        self.send_button = tkinter.Button(self.win, text="Send", command=self.write)
        self.send_button.config(font=("Arial", 12))
        self.send_button.pack(padx=20, pady=5)

        self.gui_done = True

        self.win.protocol("WM_DELETE_WINDOW", self.terminate)
        self.win.mainloop()

    def write(self):
        msg = f"{self.nickname}: {self.input_area.get('1.0', 'end')}".encode('utf-8')
        encrypted_msg = rsa.encrypt(msg, self.server_public_key)
        self.sock.send(encrypted_msg)
        self.input_area.delete('1.0', 'end')

    def receive(self):
        while self.running:
            try:
                raw_msg = self.sock.recv(2048)
                # Attempt to peek at the prefix without disturbing the binary data
                try:
                    prefix = raw_msg[:2].decode('utf-8')
                except UnicodeDecodeError:
                    # If decoding fails, it's likely binary data (encrypted message)
                    prefix = ''

                if prefix == 's:' or prefix == 'b:':
                    msg_type, msg = raw_msg.decode('utf-8').split(':', 1)
                    if msg_type == 's':
                        self.sock.send(self.nickname.encode('utf-8'))
                        public_key_pem = self.public_key.save_pkcs1('PEM')
                        self.sock.send(public_key_pem)
                        self.server_public_key = rsa.PublicKey.load_pkcs1(self.sock.recv(2048))
                    elif msg_type == 'b':
                        if self.gui_done:
                            self.text_area.config(state='normal')
                            self.text_area.insert('end', msg)
                            self.text_area.yview('end')
                            self.text_area.config(state='disabled')
                else:
                    # Handle as encrypted binary data
                    print("Decrypting...")
                    decrypted_msg = rsa.decrypt(raw_msg, self.private_key).decode('utf-8')
                    print(decrypted_msg)
                    if self.gui_done:
                        self.text_area.config(state='normal')
                        self.text_area.insert('end', decrypted_msg)
                        self.text_area.yview('end')
                        self.text_area.config(state='disabled')
            except ConnectionAbortedError:
                break
            except UnicodeDecodeError:
                # This except block might be redundant now but kept for safety
                print("Error during message decoding. Potential binary data received.")
            except Exception as e:
                print(f"Error: {str(e)}")
                self.sock.close()
                break

    def terminate(self):
        self.running = False
        self.win.destroy()
        self.sock.close()
        exit(0)

client = Client(HOST,PORT)