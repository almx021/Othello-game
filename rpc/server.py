from classes.proxy import Proxy
from enums.messageSender import MessageSender
from enums.piece import Piece
from enums.reason import Reason

from random import randint
from threading import Lock, Thread
from time import sleep

import Pyro5.api
import Pyro5.server


@Pyro5.api.expose
class Server(object):
    def __init__(self, daemon):
        self.__daemon = daemon
        self.__clients: dict[int, list[Proxy | bool]] = {} # estrutura: {client_id: [client_Proxy, client_Ready]}
        self.__CONNECTED_CLIENTS = 0
        self.__MAX_CLIENTS = 2
        self.__GAME_RUNNING = False
        self.__TURN = False
        self.lock = Lock()
        self.chat_lock = Lock()

        self.__GAME_BOARD = ...

        Thread(target=self.ping, args=(), daemon=True).start()

    def add_client(self, uri):
        with self.lock:
            if self.__CONNECTED_CLIENTS < self.__MAX_CLIENTS:
                client = Proxy(uri)
                client._Proxy__pyroCreateConnection()
                
                self.__CONNECTED_CLIENTS += 1
                if len(self.__clients) == 1:
                    id = 3 - next(iter(self.__clients.keys()))
                else:
                    id = self.__CONNECTED_CLIENTS
                self.__clients[id] = [client, False]
                return id
            else:
                return 0

    def ping(self):
        while True:
            sleep(1)
            try:
                if self.__clients != {}:
                    for player in range(1, 3):
                        try:
                            with self.__clients[player][0].lending_ownership():
                                    self.__clients[player][0].ping(), player
                        except KeyError:
                            continue
            except Exception:
                self.release(player, True)

    def release(self, client_id, sudden=False):
        with self.lock:
            self.__CONNECTED_CLIENTS -= 1
            if not sudden:
                self.__clients[client_id][0]._pyroRelease()
            del self.__clients[client_id]
            # print(f"cliente {client_id} saiu. sobrou: {self.__clients}")
            if self.__clients == {}:
                    return self.__daemon.shutdown()
            self.send_message_to(3 - client_id, "Oponente desconectado!")

    def alert_connection(self, client_id: int):
        try:
            self.send_message_to(client_id, 'Conectado com sucesso!')
        except Exception:
            pass
        try:
            self.send_message_to(3 - client_id, 'Oponente conectado!')
        except Exception:
            pass

    def send_message_to(self, client_id: int, text: str):
        if client_id not in (1, 2):
            raise ValueError
        with self.chat_lock:
            with self.__clients[client_id][0].lending_ownership():
                sender = MessageSender.SERVER
                text = text.upper()
                self.__clients[client_id][0].handle_message(text, sender)

    def broadcast_message(self, source_id: int, text: str):
        with self.chat_lock:
            for client_id, client in self.__clients.copy().items():
                with client[0].lending_ownership():
                    if source_id == client_id:
                        sender = MessageSender.USER
                    elif source_id == 0:
                        sender = MessageSender.SERVER
                        text = text.upper()
                    else:
                        sender = MessageSender.OPONENT
                    client[0].handle_message(text, sender)

    def create_board(self):
        board = []
        for row in range(8):
            row_buttons = []
            for col in range(8):
                row_buttons.append(Piece.NONE)
            board.append(row_buttons)
        board[3][3], board[4][4] = Piece.BLUE, Piece.BLUE
        board[3][4], board[4][3] = Piece.BLACK, Piece.BLACK 
        del row_buttons
        return board

    def update_clients_boards(self):
        with self.lock:
            for client in self.__clients.values():
                with client[0].lending_ownership():
                    client[0].update_board()

    def change_turn(self):
        with self.lock:
            for client in self.__clients.values():
                with client[0].lending_ownership():
                    client[0].change_turn_to(self.current_player)

    def check_valid_move(self, row, col, player_piece, opponent_piece, opponent_turn=False):
        if self.game_board[row][col] != Piece.NONE:
            return False

        with self.lock:
            if opponent_turn:
                player_piece, opponent_piece = opponent_piece, player_piece

        for dr, dc in self.__DIRECTIONS:
            r, c = row + dr, col + dc
            has_opponent = False

            while 0 <= r < 8 and 0 <= c < 8 and self.game_board[r][c] == opponent_piece:
                has_opponent = True
                r += dr
                c += dc

            if has_opponent and 0 <= r < 8 and 0 <= c < 8 and self.game_board[r][c] == player_piece:
                return True

        return False

    def _calculate_result(self):
        with self.lock:
            if self.current_player == 1:
                player_piece = Piece.BLACK
                opponent_piece = Piece.BLUE
            else:
                player_piece = Piece.BLUE
                opponent_piece = Piece.BLACK

        player_piece_total, opponent_piece_total = 0, 0

        for row in self.game_board:
            for piece in row:
                if piece == player_piece:
                    player_piece_total += 1
                elif piece == opponent_piece:
                    opponent_piece_total += 1

        if player_piece_total == opponent_piece_total:
            self.finish_game(0, Reason.DRAW)
        elif player_piece_total > opponent_piece_total:
            self.finish_game(self.current_player, Reason.VICTORY)
        else:
            self.finish_game(self.opponent_player, Reason.VICTORY)

    def start_game(self):
        with self.lock:
            self.__GAME_RUNNING = True
            self.game_board = self.create_board()
            self.current_player = randint(1, 2)
            self.__DIRECTIONS = (
            (-1, 0), (-1, 1), (0, 1), (1, 1),
            (1, 0), (1, -1), (0, -1), (-1, -1)
            )
            
        self.update_clients_boards()

        self.change_turn()
        self.broadcast_message(0, "JOGO INICIADO")

    def finish_game(self, id, reason):
        with self.lock:
            self.__GAME_RUNNING = False
            self.current_player = False

            for client_id, client in self.__clients.items():
                try:
                    with client[0].lending_ownership():
                        client[0].reset_data()
                        client[1] = False
                        
                        sender = MessageSender.SERVER
                        if reason == Reason.FORFEITH:
                                if id == client_id:
                                    client[0].handle_message("VOCÊ PERDEU! VOCÊ DESISTIU!", sender)
                                else:
                                    client[0].handle_message("VOCÊ GANHOU! OPONENTE DESISTIU!", sender)
                        elif reason == Reason.DRAW:
                            client[0].handle_message("EMPATE!", sender)
                        else:
                            if id == client_id:
                                client[0].handle_message("VOCÊ GANHOU!", sender)
                            else:
                                client[0].handle_message("VOCÊ PERDEU", sender)
                except Exception as e:
                        print(str(e))

    @Pyro5.api.oneway
    def check_move(self, row, col):
        # print(f"clicado na linha {row} coluna {col}")
        with self.lock:
            if self.current_player == 1:
                player_piece = Piece.BLACK
                opponent_piece = Piece.BLUE
            else:
                player_piece = Piece.BLUE
                opponent_piece = Piece.BLACK

        if not self.check_valid_move(row, col, player_piece, opponent_piece):
            self.send_message_to(self.current_player, "Movimento inválido")
            return

        for vector_row, vector_column in self.__DIRECTIONS:
            r, c = row + vector_row, col + vector_column
            pieces_to_flip = []
            while 0 <= r < 8 and 0 <= c < 8 and self.game_board[r][c] == opponent_piece:
                pieces_to_flip.append((r, c))
                r += vector_row
                c += vector_column

            if pieces_to_flip and 0 <= r < 8 and 0 <= c < 8 and self.game_board[r][c] == player_piece:
                pieces_to_flip.insert(0, (row, col))
                for target_row, target_column in pieces_to_flip:
                    self.game_board[target_row][target_column] = player_piece
        
        self.update_clients_boards()

        if not any(self.check_valid_move(row, col, player_piece, opponent_piece, opponent_turn=True) for col in range(8) for row in range(8)):
            if any(self.check_valid_move(row, col, player_piece, opponent_piece) for col in range(8) for row in range(8)):
                self.send_message_to(self.current_player, "OPONENTE SEM JOGADAS VÁLIDAS! JOGUE NOVAMENTE!")
                self.send_message_to(self.opponent_player, "SEM JOGADAS VÁLIDAS! PASSOU A VEZ!")
                return
            
            self._calculate_result()
            return
        
        with self.lock:
            self.current_player = self.opponent_player
        self.change_turn()
        return    

    @Pyro5.api.oneway
    def ready(self, client_id):
        self.__clients[client_id][1] = not self.__clients[client_id][1]
        if len(self.__clients.values()) == 2:
            if all(x[1] is True for x in self.__clients.values()):
                with self.lock:
                    if self.is_game_running or not self.__CONNECTED_CLIENTS == self.__MAX_CLIENTS:
                        return
                self.start_game()
            elif self.__GAME_RUNNING:
                self.finish_game(client_id, Reason.FORFEITH)

    @property
    def is_game_running(self):
        return self.__GAME_RUNNING
    
    @property
    def current_player(self):
        return self.__TURN

    @current_player.setter
    def current_player(self, value):
        if value not in (False, 1, 2):
            raise ValueError
        self.__TURN = value

    @property
    def opponent_player(self):
        return 3 - self.current_player

    @property
    def game_board(self):
        return self.__GAME_BOARD
    
    @game_board.setter
    def game_board(self, board):
        self.__GAME_BOARD = board
                

if __name__ == '__main__':
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]

    try:
        with Pyro5.api.Daemon(ip) as daemon:
            with Pyro5.api.locate_ns(ip) as ns:
                server = Server(daemon)
                uri = daemon.register(server)
                ns.register("server", uri)
                print(f"Servidor pronto. URI: {uri}")
                daemon.requestLoop()
                daemon.close()
    except Exception:
        with Pyro5.api.Daemon('localhost') as daemon:
            with Pyro5.api.locate_ns('localhost') as ns:
                server = Server(daemon)
                uri = daemon.register(server)
                ns.register("server", uri)
                print(f"Servidor pronto. URI: {uri}")
                daemon.requestLoop()
                daemon.close()