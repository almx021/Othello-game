from classes.proxy import Proxy
from enums.messageSender import MessageSender
from enums.piece import Piece

from random import randint
from threading import Thread

import socket
import Pyro5.api
import Pyro5.errors
import Pyro5.server
import tkinter as tk

@Pyro5.api.expose
class OthelloGame:
    def __init__(self, root):
        self.__connected = False

        self.root = root
        self.root.title("Jogo de Othello")
        self.root.geometry("800x600")
        self.root.configure(bg="#243256")

        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=2)
        self.root.protocol("WM_DELETE_WINDOW", self.finish)
        self.show_start_screen()

    def ping(self):
        return 'pong'

    def finish(self):
        self.root.destroy()
        if hasattr(self, 'server'):
            self.server.release(self.client_id)
            self.server._pyroRelease()

    def connect(self):
        try:
            id = str(randint(0, 10))

            if server_ip:
                self._connect_remote(id)
            else:
                self._connect_local(id)

            self.server._Proxy__pyroCreateConnection()
            
            self.daemon_thread = Thread(target=self._listener_thread, args=(), daemon=True)
            self.daemon_thread.start()
            
            self.client_id = self.server.add_client(self.uri)
            print('id', self.client_id)
        except Exception as e:
            print(e)
            self.__connected = 3
            return
        if self.client_id == 0:
            self.server._pyroRelease()
            self.__connected = 2
        else:
            self.__connected = 1

    def _connect_local(self, id):
        try:
            self.daemon = Pyro5.server.Daemon('localhost')
            self.ns = Pyro5.api.locate_ns('localhost')
            self.uri = self.daemon.register(self)
            self.ns.register("client" + id, self.uri)
        except:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(('8.8.8.8', 80))
                ip = s.getsockname()[0] 

            self.daemon = Pyro5.server.Daemon(ip)
            self.ns = Pyro5.api.locate_ns(ip)
            self.uri = self.daemon.register(self)
            self.ns.register("client" + id, self.uri)
        
        self.server = Proxy("PYRONAME:server")

    def _connect_remote(self, id):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]

        self.daemon = Pyro5.server.Daemon(ip)
        self.ns = Pyro5.api.locate_ns(ip)
        self.uri = self.daemon.register(self)
        self.ns.register("client" + id, self.uri)
        
        ns2 = Pyro5.api.locate_ns(server_ip)
        ns2.register("client" + id, self.uri)
        
        self.server = Proxy("PYRONAME:server@"+server_ip)

    def _listener_thread(self):
        self.daemon.requestLoop()
        self.daemon.close()

    def show_start_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        start_frame = tk.Frame(self.root, bg="#243256")
        start_frame.pack(expand=True)

        new_game_button = tk.Button(
            start_frame, text="Entrar", font=("Arial", 12, "bold"), command=self._open_loading_page
        )
        new_game_button.pack(pady=10)

    def _open_loading_page(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        text_list = ("Carregando.", "Carregando..", "Carregando...")
        idx = 0

        loading_frame = tk.Frame(self.root, bg="#243256")
        loading_frame.pack(expand=True)       

        loading_label = tk.Label(loading_frame, text="", font=("Arial", 16, "bold"), bg="#243256", fg="white")
        loading_label.pack()

        def update_text():
            nonlocal idx
            if not self.__connected:
                loading_label.config(text=text_list[idx])
                idx = (idx + 1) % len(text_list)
                root.after(500, update_text) 
            elif self.__connected == 1:
                self.server._pyroClaimOwnership()
                self.show_game_screen()
            elif self.__connected == 2:
                loading_label.config(text="Jogo em andamento. Não é possível conectar.")
                del self.server
            elif self.__connected == 3:
                loading_label.config(text="Não foi possível conectar. Tente novamente.")
                if hasattr(self, 'server'):
                    del self.server

        Thread(target=self.connect, daemon=True).start()
        update_text()

    def show_game_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        player_piece = Piece.BLACK.value if self.client_id == 1 else Piece.BLUE.value
        opponent_piece = Piece.BLUE.value if self.client_id == 1 else Piece.BLACK.value

        self._create_board(player_piece, opponent_piece)
        self._create_info_label(player_piece)
        self._create_chat()
        self._create_input()
        self._check_reconnection()
        self.server.alert_connection(self.client_id)

    def _create_board(self, player_piece, opponent_piece):
        self.board_buttons = []
        board_frame = tk.Frame(self.root, bg="#835672")
        board_frame.grid(row=0, column=0, padx=10, pady=10, sticky="new")

        for row in range(8):
            row_buttons = []
            for col in range(8):
                btn = tk.Button(
                    board_frame, text="", width=4, height=2, font=("Arial", 12, "bold"), 
                    command=lambda r=row, c=col: self._play(r, c)
                )
                btn.grid(row=row+1, column=col+1, padx=2, pady=2)
                row_buttons.append(btn)
            self.board_buttons.append(row_buttons)

        del row_buttons

        for row_col in range(8):
            label = tk.Label(board_frame, text=chr(65 + row_col), font=("Arial", 10, "bold"), bg="#835672")
            label.grid(row=0, column=row_col + 1, sticky="n", pady=(0, 5))

            label = tk.Label(board_frame, text=str(row_col + 1), font=("Arial", 10, "bold"), bg="#835672")
            label.grid(row=row_col + 1, column=0, sticky="e", padx=(0, 5))

        if self.server.is_game_running:
            self.update_board()
        else:
            self.board_buttons[3][3].config(text="⚫", fg=player_piece)
            self.board_buttons[4][4].config(text="⚫", fg=player_piece)
            self.board_buttons[3][4].config(text="⚫", fg=opponent_piece)
            self.board_buttons[4][3].config(text="⚫", fg=opponent_piece)

    def _create_info_label(self, player_color):
        self.info_frame = tk.Frame(self.root)
        self.info_frame.grid(row=1, column=0,sticky='ns')
        self.info_frame.rowconfigure(1, weight=1)

        self.info_label = tk.Label(self.info_frame, text="JOGO NÃO INICIADO")
        self.info_label.grid(row=0, column=0, sticky='ns')

        piece_info = tk.Text(self.info_frame, height=1, width=13, borderwidth=0, highlightthickness=0, font=self.info_label.cget('font'), background=self.info_label.cget('background'))
        piece_info.insert("1.0", "SUA PEÇA: ⚫")
        piece_info.config(state="disabled")
        piece_info.tag_add("player_color", "1.10", "1.11")
        piece_info.tag_config("player_color", foreground=player_color)
        piece_info.grid(row=1, column=0, sticky='ns')        

        self.state_button = tk.Button(self.root, text="INICIAR", command=self._get_ready)
        self.state_button.grid(row=1, column=1)

    def _create_chat(self):
        chat_frame = tk.Frame(self.root, width=300, bg="#f0f0f0")
        chat_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        self.chat_display = tk.Text(chat_frame, bg="#ffffff", font=("Arial", 10), bd=0, state="disabled", wrap="word")
        self.chat_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        scrollbar = tk.Scrollbar(chat_frame, orient="vertical", command=self.chat_display.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.chat_display.config(yscrollcommand=scrollbar.set)

    def _create_input(self):
        input_frame = tk.Frame(self.root, bg="#e0e0e0")
        input_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky="nsew")

        self.entry = tk.Entry(input_frame, font=("Arial", 10))
        self.entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.entry.bind("<Return>", lambda event: self._send_message())

        send_button = tk.Button(input_frame, text="Enviar", command=self._send_message)
        send_button.pack(side=tk.RIGHT, padx=5, pady=5)

    def _check_reconnection(self):
        if not self.server.is_game_running:
            return
        self.state_button.config(command=self._give_up, text="DESISTIR")
        self.change_turn_to(self.server.current_player)

    def _get_ready(self):
        self.server.ready(self.client_id)
        self.state_button.config(command=self._give_up, text="DESISTIR")

    def _give_up(self):
        self.server.ready(self.client_id)
        self.state_button.config(command=self._get_ready, text="INICIAR")

    def _play(self, row, col):
        if not self.server.is_game_running:
            return

        if self.server.current_player == self.client_id:
            self.server.check_move(row, col)
        else:
            self.handle_message(text="VEZ DO OPONENTE!", sender=MessageSender.SERVER.value)
    
    def _send_message(self):
        text = self.entry.get()
        if not text.strip() == '':
            try:
                self.server.broadcast_message(self.client_id, text)
            except RuntimeError as e:
                print('Não foi possível enviar a mensagem para todos os usuários.')
            else:
                self.entry.delete(0, tk.END)

    @Pyro5.api.oneway
    def handle_message(self, text: str, sender: MessageSender):
        self.chat_display.config(state="normal")
    
        if len(self.chat_display.get('1.0', tk.END)) > 1:
            self.chat_display.insert(tk.END, '\n')

        self.chat_display.insert(tk.END, f"{sender}: {text}")        
    
        self.chat_display.config(state="disabled")
        self.chat_display.see(tk.END)
            
    @Pyro5.api.oneway
    def update_board(self):
        try:
            with self.server.lending_ownership():
                board = self.server.game_board
        except Exception as e:
            print(str(e))
        for row in range(8):
            for col in range(8):
                if board[row][col] == "": self.board_buttons[row][col].config(text="")
                else: self.board_buttons[row][col].config(text="⚫", fg=board[row][col])

    @Pyro5.api.oneway
    def change_turn_to(self, player):
        if player == self.client_id:
            label_text = "SEU TURNO"
        else:
            label_text = "TURNO DO OPONENTE"
        self.info_label.config(text=label_text)

    @Pyro5.api.oneway
    def reset_data(self):
        self.info_label.config(text="JOGO NÃO INICIADO")
        self.state_button.config(command=self._get_ready, text="INICIAR")

if __name__ == '__main__':
    import sys
    server_ip = None
    if len(sys.argv) > 1:
        server_ip = sys.argv[1]

    root = tk.Tk()
    app = OthelloGame(root)
    root.mainloop()