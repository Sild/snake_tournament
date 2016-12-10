import websockets
import asyncio
import datetime

from json import dumps, loads
from collections import namedtuple
from enum import Enum

Client = namedtuple("Client", ["id", "fd"])
Position = namedtuple("Position", ["x", "y"])

# protocol
def greeting(id):
    return dumps({"id": id})

class InitialMessageBuilder:

    def __init__(self):
        self.clients = {}

    def add_client(self, id, head, length, direction):
        self.clients[id] = {
            "head": {"x": head.x, "y": head.y},
            "length": length,
            "direction": str(direction)
        }

    def build(self):
        return dumps(self.clients)


class PartialStatusMessageBuilder:

    def __init__(self):
        self.clients = {}

    def add_client_info(self, id, head, direction):
        self.clients[id] = {
            "head": {"x": head.x, "y": head.y},
            "direction": str(direction)
        }

    def build(self):
        return dumps(self.clients)

class Direction(Enum):
    top = 0
    left = 1
    bottom = 2
    right = 3

    def get_x_factor(self):
        if self == Direction.left:
            return -1
        if self == Direction.right:
            return 1
        return 0

    def get_y_factor(self):
        if self == Direction.top:
            return -1
        if self == Direction.bottom:
            return 1
        return 0

    def __str__(self):
        if self == Direction.top:
            return "TOP"
        elif self == Direction.left:
            return "LEFT"
        elif self == Direction.bottom:
            return "BOTTOM"
        elif self == Direction.right:
            return "RIGHT"
        return "UNKNOWN_DIRECTION"

    @staticmethod
    def create(str_direction):
        if str_direction == "TOP":
            return Direction.top
        elif str_direction == "LEFT":
            return Direction.left
        elif str_direction == "BOTTOM":
            return Direction.bottom
        elif str_direction == "RIGHT":
            return Direction.right
        raise Exception()



class IntersectionCalculator:
    def __init__(self):
        pass

class Snake:
    def __init__(self, head_position, length, direction):
        self.body = [head_position]
        self.direction = direction

        x_factor = direction.get_x_factor()
        y_factor = direction.get_y_factor()
        for i in range(0, length):
            self.body.append(Position(self.body[-1].x - x_factor, self.body[-1].y - y_factor))

    def move(self, speed=1):
        for i in range(0, speed):
            self.body.pop() # TODO: avoid of pessimisation
            self.body = [self.get_new_head_position()] + self.body

    def get_new_head_position(self):
        return Position(self.body[0].x + self.direction.get_x_factor(),
                        self.body[0].y + self.direction.get_y_factor())

    def update(self, direction):
        self.direction = direction


class GameBoard:

    def __init__(self, weight, height, clients_info, speed=1):
        self.weight = weight
        self.height = height
        self.clients_info = clients_info
        self.speed = speed

    def next(self):
        for id, snake in self.clients_info.items():
            snake.move()

    def turn_client(self, id, direction):
        if id in self.clients_info:
            self.clients_info[id].update(direction)

    def increase_speed(self):
        self.speed *= 2

    def encode_state(self):
        info = {}
        for id, client_info in self.clients_info.items():
            info[id] = {"head":{"x":client_info.body[0].x, "y":client_info.body[0].y},
                        "direction":str(client_info.direction)}
        return dumps(info)


class SnakeServer:

    REFRESH_TIMEOUT = 0.5
    NUM_CLIENTS_TO_GAME = 2
    BUSY_MESSAGE = "BUSY NOW"

    def __init__(self, loop):
        self.clients = []
        self.loop = loop
        self.game_started = False

    async def on_client_connect(self, websocket, path):
        if self.game_started:
            websocket.send(SnakeServer.BUSY_MESSAGE)
            return

        id = hash("{}{}".format(websocket.remote_address, datetime.datetime.utcnow().isoformat()))
        client = Client(id, websocket)
        self.clients.append(Client(id, websocket))

        try:
            await websocket.send(greeting(id))

            while not self.game_started:
                await asyncio.sleep(SnakeServer.REFRESH_TIMEOUT)

            while True:
                message = await websocket.recv()
                decoded = loads(message)
                direction = Direction.create(decoded["direction"])
                self.board.turn_client(id, direction)
        except websockets.ConnectionClosed:
            self.clients.remove(client)

    async def presentation_loop(self):
        while len(self.clients) != 2:
            await asyncio.sleep(SnakeServer.REFRESH_TIMEOUT)

        self.game_started = True
        clients_info = {}
        initial_state = InitialMessageBuilder()
        for index, client in enumerate(self.clients):
            head = Position(40 + 20 * index, 40 + 20 * index)
            length = 20
            direction = Direction.left if index == 0 else Direction.right
            clients_info[client.id] = Snake(head, length, direction)
            initial_state.add_client(client.id, head, length, direction)

        initial_message = initial_state.build()

        for client in self.clients:
            await client.fd.send(initial_message)

        self.board = GameBoard(100, 100, clients_info)
        num = 0
        while True:
            for client in self.clients:
                try:
                    await client.fd.send(self.board.encode_state())
                except websockets.ConnectionClosed:
                    self.clients.remove(client)

            num += 1
            if num == 50:
                self.board.increase_speed()
                num = 0

            self.board.next()
            await asyncio.sleep(SnakeServer.REFRESH_TIMEOUT)

        self.game_started = False


if __name__ == "__main__":
    try:
        server = SnakeServer(asyncio.get_event_loop())
        start_server = websockets.serve(server.on_client_connect, '', 5678)

        asyncio.get_event_loop().run_until_complete(start_server)
        asyncio.get_event_loop().run_until_complete(asyncio.Task(server.presentation_loop()))
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        print("We've been fucked")



class IntersectionCalculator:
    def __init__(self, x_size, y_size, snakes, time_speed_pairs):
        self.init_time_millisecond = datetime.datetime.utcnow().microsecond * 1000
        self.x_size = x_size
        self.y_size = y_size
        self.snakes = snakes
        self.speed_time_pairs = time_speed_pairs
        self.intersection_time = 1 #will be more then required interval
        for time, speed in time_speed_pairs:
            self.intersection_time = self.intersection_time + time

    async def run(self):
        call_delay = datetime.datetime.utcnow().microsecond * 1000 - self.init_time_millisecond
        for time, speed in self.speed_time_pairs:
            if call_delay < time:
                actual_time = time - call_delay
                self.check_intersection(actual_time, speed)
            else:
                call_delay = call_delay - time

    def reset(self, snakes, speed_time_pairs):
        pass

    def check_intersection(self, duration, speed):
        pass


