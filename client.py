import socket
import threading
import tkinter as tk
import tkinter.scrolledtext
import rsa

HOST = '127.0.0.1'
PORT = 9999


class Client:
    def __init__(self, host, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))
        self.public_key, self.private_key = rsa.newkeys(1024)
        self.server_public_key = None
        self.shift_pressed = False

        self.gui_done = False
        self.running = True
        self.start_screen()

    def start_screen(self):
        self.start_win = tk.Tk()
        self.start_win.title("Encrypted ChatRoom")
        window_width = 450
        window_height = 220

        screen_width = self.start_win.winfo_screenwidth()
        screen_height = self.start_win.winfo_screenheight()

        x = (screen_width / 2) - (window_width / 2) - 100
        y = (screen_height / 2) - (window_height / 2) - 100

        self.start_win.geometry('%dx%d+%d+%d' % (window_width, window_height, x, y))
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

            recv_thread = threading.Thread(target=self.receive)
            recv_thread.setDaemon(True)  # Set the thread as daemon
            recv_thread.start()

            threading.Thread(target=self.gui_loop).start()

    def gui_loop(self):
        self.win = tk.Tk()
        self.win.title("Encrypted Chat Room")

        # Set window size
        window_width = 650
        window_height = 650

        # Get screen dimensions
        screen_width = self.win.winfo_screenwidth()
        screen_height = self.win.winfo_screenheight()

        # Calculate x and y coordinates for the Tk window
        x = (screen_width / 2) - (window_width / 2)
        y = (screen_height / 2) - (window_height / 2)

        # Set the window size and position
        self.win.geometry('%dx%d+%d+%d' % (window_width, window_height, x, y))
        self.win.configure(bg="#282a36")

        # Chat label
        self.chat_label = tk.Label(self.win, text="Encrypted Chat Room", bg="#282a36", fg="#ffffff")
        self.chat_label.config(font=("Helvetica", 16))
        self.chat_label.pack(padx=20, pady=5)

        # Text area
        self.text_area = tkinter.scrolledtext.ScrolledText(self.win, bg="#ffffff")
        self.text_area.pack(padx=20, pady=5, fill=tk.BOTH, expand=True)
        self.text_area.config(state='disabled', font=("Helvetica", 12))

        # Message label
        self.msg_label = tkinter.Label(self.win, text="Type your message:", bg="#282a36", fg="#ffffff")
        self.msg_label.config(font=("Helvetica", 12))
        self.msg_label.pack(padx=20, pady=5)

        # Input area
        self.input_area = tkinter.Text(self.win, height=3, bg="#f0f0f0")
        self.input_area.pack(padx=20, pady=5, fill=tk.X)
        self.input_area.config(font=("Helvetica", 12))
        self.input_area.bind("<Return>", self.handle_return_key)  # Bind the return key

        # Send button setup...
        self.send_button = tkinter.Button(self.win, text="Send", command=self.write, bg="#50fa7b", fg="#282a36")
        self.send_button.config(font=("Helvetica", 12))
        self.send_button.pack(padx=20, pady=5, side=tk.BOTTOM)

        self.win.bind("<Shift_L>", self.shift_press)
        self.win.bind("<KeyRelease-Shift_L>", self.shift_release)

        self.gui_done = True
        self.win.protocol("WM_DELETE_WINDOW", self.terminate)
        self.win.mainloop()

    def handle_return_key(self, event):
        if self.shift_pressed:
            # Insert a newline if Shift+Enter is pressed
            self.input_area.insert(tk.INSERT, "\n")
            # Move the cursor to the new line
            self.input_area.see(tk.INSERT)
            return "break"  # This prevents the default newline insertion behavior
        else:
            # Send the message
            self.write()
            return "break"  # Prevent the default behavior of inserting a newline

    def shift_press(self, event):
        self.shift_pressed = True

    def shift_release(self, event):
        self.shift_pressed = False

    def write(self):
        msg = f"{self.nickname}: {self.input_area.get('1.0', 'end')}".encode('utf-8')
        if msg != "":
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
                            if msg == 'shutdown':
                                self.handle_server_shutdown()
                                break
                            else:
                                self.text_area.config(state='normal')
                                self.text_area.insert('end', msg)
                                self.text_area.yview('end')
                                self.text_area.config(state='disabled')
                else:
                    # Handle as encrypted binary data
                    print("Decrypting...")
                    decrypted_msg = rsa.decrypt(raw_msg, self.private_key).decode('utf-8')
                    if self.gui_done:
                        self.text_area.config(state='normal')
                        self.text_area.insert('end', decrypted_msg)
                        self.text_area.yview('end')
                        self.text_area.config(state='disabled')
            except ConnectionAbortedError:
                self.handle_connection_aborted()
                break
            except UnicodeDecodeError:
                # This except block might be redundant now but kept for safety
                print("Error during message decoding. Potential binary data received.")
            except Exception as e:
                self.handle_unexpected_disconnect(e)
                break

    def handle_server_shutdown(self):
        # This function should only be called when the server sends a 'shutdown' message
        msg = "Server is shutting down. Try reconnecting shortly."
        self.terminate(msg)

    def handle_connection_aborted(self):
        # This function should be called when a ConnectionAbortedError exception is caught
        msg = "The connection was closed by the server. Try reconnecting shortly."
        self.terminate(msg)

    def handle_unexpected_disconnect(self, e):
        # This function should be called for unexpected exceptions
        msg = f"An unexpected error occurred: {e}"
        if self.running:
            self.terminate(msg)

    def update_gui(self, message):
        if self.gui_done:
            self.text_area.config(state='normal')
            self.text_area.insert('end', message)
            self.text_area.yview('end')
            self.text_area.config(state='disabled')
        # Handle the Tkinter operations in the main thread
        self.win.after(0, self.terminate)

    def terminate(self,m):
        print(m)
        print("Thank you for using our chat. See you soon!")
        self.running = False
        if self.gui_done:
            # Schedule the GUI to close on the main thread
            self.win.destroy()
        self.sock.close()
        exit(0)

if __name__ == "__main__":
    client = Client(HOST, PORT)