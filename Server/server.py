import socket
import struct
import sys
import time

COMMAND_JOIN = 0
COMMAND_CREATE_ROOM = 1
COMMAND_CHALLENGE = 2
COMMAND_MOVE = 3
COMMAND_QUIT = 4
COMMAND_UPDATE_ROOM = 5
COMMAND_SEND_PLAYFIELD= 6
COMMAND_SEND_GAME_STATE= 7

GAME_STATE_JOIN = 0
GAME_STATE_LOBBY = 1
GAME_STATE_PLAY = 2

MAX_ROOMS = 10


class Room:

    def __init__(self, room_id, owner):
        self.room_id = room_id
        self.owner = owner
        self.challenger = None
        self.reset()

    def is_door_open(self):
        return self.challenger is None

    def has_started(self):
        for cell in self.playfield:
            if cell is not None:
                return True
        return False

    def return_int_symbol(self, cell):
        player = self.playfield[cell]
        if not player:
            return 0
        if player == self.owner:
            return 1
        if player == self.challenger:
            return 2
        else:
            return 3

    def return_playfield_state(self):
        playfield_array = [0] * 9
        for cell in range(len(self.playfield)):
            playfield_array[cell] = self.return_int_symbol(cell)
        return playfield_array


    def reset(self, reset_challenger = True):
        if reset_challenger and self.challenger:
            self.challenger.room=None
            self.challenger = None
        self.playfield = [None] * 9
        self.turn = self.owner
        self.winner = None
        self.draw = False

    def check_horizontal(self, row):
        for col in range(0, 3):
            if self.playfield[row * 3 + col] is None:
                return None
        player = self.playfield[row * 3]
        if self.playfield[row * 3 + 1] != player:
            return None
        if self.playfield[row * 3 + 2] != player:
            return None
        return player

    def check_vertical(self, col):
        for row in range(0, 3):
            if self.playfield[row * 3 + col] is None:
                return None
        player = self.playfield[col]
        if self.playfield[3 + col] != player:
            return None
        if self.playfield[6 + col] != player:
            return None
        return player

    def check_diagonal_left(self):
        for cell in (0, 4, 8):
            if self.playfield[cell] is None:
                return None
        player = self.playfield[0]
        if self.playfield[4] != player:
            return None
        if self.playfield[8] != player:
            return None
        return player

    def check_diagonal_right(self):
        for cell in (2, 4, 6):
            if self.playfield[cell] is None:
                return None
        player = self.playfield[2]
        if self.playfield[4] != player:
            return None
        if self.playfield[6] != player:
            return None
        return player

    def check_victory(self):
        for row in range(0, 3):
            winner = self.check_horizontal(row)
            if winner:
                return winner
        for col in range(0, 3):
            winner = self.check_vertical(col)
            if winner:
                return winner
        winner = self.check_diagonal_left()
        if winner:
            return winner
        return self.check_diagonal_right()

    def check_draw(self):
        if self.winner: return False
        for cell in range(0, 8):
            if self.playfield[cell] is None:
                return False
        return True

    def move(self, player, cell):
        if cell < 0 or cell > 8:
            return False
        if self.playfield[cell] is not None:
            return False
        if self.winner:
            return False
        if self.challenger is None:
            return False
        if player.room != self:
            return False
        if player != self.owner and player != self.challenger:
            return False
        if player != self.turn:
            return False
        self.playfield[cell] = player
        self.winner = self.check_victory()
        self.draw = self.check_draw()
        self.turn = self.challenger if self.turn == self.owner else self.owner
        return True


class Player:

    def __init__(self, name, address):
        self.name = name
        self.room = None
        self.address=address
        self.last_packet_ts = time.time()


class Server:

    def __init__(self, address, port):
        self.players = {}
        self.rooms = {}
        self.rooms_ids=[0]*MAX_ROOMS
        self.room_counter = 100
        self.address = address
        self.port = port
        self.last_update_time = time.time()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(1)
        self.socket.bind((address, port))
        self.command_functions={
            COMMAND_JOIN: self.join,
            COMMAND_CREATE_ROOM: self.create_room,
            COMMAND_CHALLENGE: self.challenge,
            COMMAND_MOVE: self.move,
            COMMAND_QUIT: self.quit
        }
        print("Server ready: waiting for packets...")

    def kick(self, sender):
        bad_player = self.players[sender]
        if bad_player.room:
            if bad_player.room.owner == bad_player:
                self.destroy_room(bad_player.room)
            else:
                bad_player.room.reset()
                self.updaterooms()
        del self.players[sender]
        self.send_game_state(sender, GAME_STATE_JOIN)
        print("{} ({}) has been kicked".format(sender, bad_player.name))

    def destroy_room(self, room):
        del self.rooms[room.room_id]
        room.owner.room = None
        if room.challenger:
            self.send_game_state(room.challenger.address, GAME_STATE_LOBBY)
            room.challenger.room=None
            room.challenger = None
        self.updaterooms()
        print("Room {} destroyed".format(room.room_id))

    def remove_player(self, sender):
        player = self.players[sender]
        self.send_game_state(sender, GAME_STATE_JOIN)
        if not player.room:
            del self.players[sender]
            print("Player {} removed".format(player.name))
            return
        if player == player.room.challenger:
            player.room.reset()
            del self.players[sender]
            self.updaterooms()
            print("Player {} removed".format(player.name))
            return
        del self.players[sender]
        self.destroy_room(player.room)
        print("Player {} removed".format(player.name))

    def join(self, packet, sender):
        if len(packet)==24:
            if sender in self.players:
                print("{} has already joined!".format(sender))
                self.kick(sender)
                return
            self.players[sender] = Player(packet[4:24], sender)
            print("player {} joined from {} [{} players on server]".format(self.players[sender].name, sender, len(self.players)))
            self.send_game_state(sender, GAME_STATE_LOBBY)
            self.send_rooms(sender)
        else:
            print("invalid packet size for join: {}".format(len(packet)))

    def create_room(self, packet, sender):
        if len(packet)==4:
            if sender not in self.players:
                print("Unknown player {}".format(sender))
                return
            player = self.players[sender]
            if player.room:
                print("Player {} ({}) already has a room".format(sender, player.name))
                return
            if len(self.rooms) >= MAX_ROOMS:
                print("Maximum number of rooms reached, cannot create more.")
                return
            player.room = Room(self.room_counter, player)
            self.rooms[self.room_counter] = player.room
            print("Room {} for player {} ({}) created".format(self.room_counter, sender, player.name))
            self.room_counter = (self.room_counter + 1) % 1000
            player.last_packet_ts = time.time()
            self.send_game_state(sender, GAME_STATE_PLAY)
            self.updaterooms()
            self.send_playfield_state_to_room(player.room)
        else:
            print("invalid packet size for create room: {}".format(len(packet)))

    def challenge(self, packet, sender):
        if len(packet) != 8:
            print("invalid packet size for challenge: {}".format(len(packet)))
            return
        if sender not in self.players:
            print("Unknown player {}".format(sender))
            return
        player = self.players[sender]
        if player.room:
            print("Player {} ({}) already in a room".format(sender, player.name))
            return
        room_id, = struct.unpack("<I", packet[4:8])
        if room_id not in self.rooms:
            print("Unknown room {}".format(room_id))
            return
        room = self.rooms[room_id]
        if not room.is_door_open():
            print("Room {} is closed!".format(room_id))
            return
        room.challenger = player
        player.room = room
        player.last_packet_ts = time.time()
        self.send_game_state(sender, GAME_STATE_PLAY)
        self.send_playfield_state_to_room(player.room)
        self.updaterooms()
        print("Game on room {} started!".format(room_id))

    def move(self, packet, sender):
        if len(packet) != 8:
            print("invalid packet size for move: {}".format(len(packet)))
            return
        if sender not in self.players:
            print("Unknown player {}".format(sender))
            return
        player = self.players[sender]
        if not player.room:
            print("Player {} ({}) is not in a room".format(sender, player.name))
            return
        (cell,) = struct.unpack("<I", packet[4:8])
        if not player.room.move(player, cell):
            print("player {} did an invalid move!".format(player.name))
            return
        player.last_packet_ts = time.time()
        self.send_playfield_state_to_room(player.room)
        if player.room.winner:
            room_to_reset=player.room
            print("player {} did WON!".format(player.room.winner.name))
            self.send_game_state(room_to_reset.challenger.address, GAME_STATE_LOBBY)
            room_to_reset.reset()
            self.updaterooms()
            self.send_playfield_state_to_room(room_to_reset)
            return
        if player.room.draw :
            player.room.reset(False)
            self.send_playfield_state_to_room(player.room)
            print("DRAW")

    def quit(self, packet, sender):
        if len(packet) != 4:
            print("invalid packet size for quit: {}".format(len(packet)))
            return
        if sender not in self.players:
            print("Unknown player {}".format(sender))
            return
        self.remove_player(sender)
        return
        
    def tick(self):
        try:
            packet, sender = self.socket.recvfrom(64)
            print(packet, sender)
            if len(packet) < 4:
                print("invalid packet size: {}".format(len(packet)))
                return
            command, = struct.unpack("<I", packet[0:4])
            if command in self.command_functions:
                self.command_functions[command](packet, sender)
            else:
                print("unknown command from {}".format(sender))
        except TimeoutError:
            return
        except KeyboardInterrupt:
            sys.exit(1)
        except ConnectionResetError:
           return
        except:
            print(sys.exc_info())
            return

    def send_game_state(self, client, state):
        packet = struct.pack("<II", COMMAND_SEND_GAME_STATE, state)
        self.socket.sendto(packet, client)
        

    def updaterooms(self):
        self.rooms_ids=[0]*MAX_ROOMS
        i=0
        for room_id in self.rooms:
            room = self.rooms[room_id]
            if room.is_door_open():
                self.rooms_ids[i]=room_id
                i += 1

        for sender in self.players:
            packet = struct.pack("<11I", COMMAND_UPDATE_ROOM, *self.rooms_ids)
            self.socket.sendto(packet, sender)

    def send_rooms(self, client):
            packet = struct.pack("<11I", COMMAND_UPDATE_ROOM, *self.rooms_ids)
            self.socket.sendto(packet, client)

    def send_playfield_state_to_room(self, room):
        playfield_state=room.return_playfield_state()
        packet=struct.pack("<10I", COMMAND_SEND_PLAYFIELD, *playfield_state)
        if (room.owner):
            self.socket.sendto(packet, room.owner.address)
        if (room.challenger):
            self.socket.sendto(packet, room.challenger.address)

    def send_playfield_state_to_player(self, player):
        playfield_state=player.room.return_playfield_state()
        packet=struct.pack("<10I", COMMAND_SEND_PLAYFIELD, *playfield_state)
        self.socket.sendto(packet, player.address)

    def check_dead_peers(self):
        now = time.time()
        dead_players = []
        for sender in self.players:
            player = self.players[sender]
            if now - player.last_packet_ts > 30:
                dead_players.append(sender)

        for sender in dead_players:
            print('removing {} for inactivity...'.format(sender))
            self.remove_player(sender)

    def update_client(self):
        now=time.time()
        if (now - self.last_update_time > 3):
            self.last_update_time=time.time()
            for sender in self.players:
                player=self.players[sender]
                if  player.room :
                    self.send_playfield_state_to_player(player)
                    self.send_game_state(sender, GAME_STATE_PLAY)
                else:
                    self.send_rooms(sender)
                    self.send_game_state(sender, GAME_STATE_LOBBY)
               


    def run(self):
        while True:
            self.tick()
            self.check_dead_peers()
            self.update_client()


if __name__ == "__main__":
    Server("127.0.0.1", 9999).run()