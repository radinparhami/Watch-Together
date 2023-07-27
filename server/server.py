from sqlalchemy import Column, String, Integer
from websocket_server import WebsocketServer
from string import ascii_letters, digits
from json import loads, dumps
from random import choices
from ORM import Data_Base

server_ip, port = '127.0.0.1', 58978
sql_db = Data_Base('sqlite:///watch_together.db')
rooms, access = {}, []

users = sql_db.table(
    'users',
    Column('name', String),
    Column('password', String),
    Column('client_id', Integer),
    Column('room', String),
)

set_user = (lambda kwargs: sql_db.insert(users, **kwargs))
get_user = (lambda name: sql_db.select(users, users.c.name == name))
update_user = (lambda kwargs: sql_db.update(users, users.c.name == kwargs.get('name'), **kwargs))

get_client = (lambda id: sql_db.select(users, users.c.client_id == int(id)))

get_room = lambda room_id: [{'key': i, 'value': rooms[i]} for i in rooms.keys() if rooms[i]['id'] == room_id]
get_rnd = lambda length: ''.join(choices(digits + ascii_letters, k=length))


class Client(WebsocketServer):
    on_message_handler = None

    def user_to_client(self, user_name):
        uid = get_user(user_name)[0]['client_id']
        for client in self.clients:
            if client['id'] == uid:
                return client

    def send(
            self, client, method,
            query: dict = None, status="OK"
    ):
        default = {
            'status': status,
            'method': method,
        }
        query and default.update(query)
        return self.send_message(
            client, dumps(default)
        )

    def on_update(self, client, _, msg):
        if self.on_message_handler:
            if "method" in msg:
                try:
                    dict_rec = loads(msg)
                    if m := dict_rec.get('method'):
                        self.on_message_handler(client, dict_rec, m)
                except:
                    pass

    def on_message(self, func):
        self.on_message_handler = func

    def client_left(self, client, server):
        try:
            user = get_client(client['id'])[0]
            if rid := user['room']:
                if room := get_room(rid):
                    owner = self.user_to_client(room[0]['key'])
                    if owner['id'] == client['id']:
                        owner = self.user_to_client(rooms[room[0]['key']]['partner'])
                    rooms[room[0]['key']]['ready'] = False
                    self.send(owner, 'clientLeft', {'username': user['name']})
        except:
            pass

    def run(self):
        self.on_error = lambda _, error: print(error) if "unreachable" not in str(error) else None
        self.message_received = self.on_update
        self.new_client = lambda client, _: self.send(client, "register")
        self.run_forever()


server = Client(server_ip, port)


@server.on_message
def new_query(client, data, method):
    if method != "setTime":
        print(data)

    if user_name := data.get('username'):
        user = get_user(user_name)
        if method == "newUser":
            if password := data.get('password'):
                new_user, ok = dict(
                    name=user_name,
                    password=password,
                    client_id=client['id'],
                ), None
                if user:
                    user = user[0]
                    if user['room']:
                        if room := get_room(user['room']):
                            owner, value = room[0]['key'], room[0]['value']
                            target_reflex = value['partner'] if owner == user['name'] else owner
                            if target_reflex:
                                if target := server.user_to_client(target_reflex):
                                    ok = value
                                    server.send(target, "joinRoom", {'username': user['name']})
                    if user['password'] == password:
                        update_user(new_user)
                    else:
                        return server.send(client, method, {'msg': 'password is wrong!'}, status="ERROR")
                else:
                    new_user.update(dict(room=None))
                    set_user(new_user)
                auth = f"{user_name}:{get_rnd(16)}"
                res = {'result': 'OK', 'auth': auth}
                if ok and ok['partner'] and not ok['ready']:
                    res.update(dict(get_time=True))
                access.append(auth), server.send(client, method, res)

    if auth := data.get('auth'):
        if auth in access:
            user = get_user(auth.split(':')[0])[0]
            if method == "newRoom":
                rid = user['room']
                if not rid:
                    while True:
                        rid = get_rnd(8)
                        if not get_room(rid):
                            break
                    update_user({'name': user['name'], 'room': rid})
                rooms[user['name']] = {'id': rid, 'partner': None, 'filename': None, 'ready': False}
                return server.send(client, method, {'roomID': rid})
            elif method == "joinRoom":
                if rid := data.get('roomID'):
                    if room := get_room(rid):
                        partner = room[0]['value']['partner']
                        if not partner or partner == user['name']:
                            owner = room[0]['key']
                            rooms[owner]['partner'] = user['name']
                            update_user({'name': user['name'], 'room': rid})
                            server.send(server.user_to_client(owner), "isOnRoom", {'username': user['name']})
                            return server.send(client, method, {'roomID': rid, 'owner': owner})
            elif user['room']:
                if room := get_room(user['room']):
                    owner, value = room[0]['key'], room[0]['value']
                    target_reflex = value['partner'] if owner == user['name'] else owner
                    if value['ready'] or method == "timeMatch":
                        data.pop('auth')
                        return server.send(server.user_to_client(target_reflex), method, data)
                    elif method == "getReady":
                        if file_name := data.get('filename'):
                            if target := value['partner']:
                                rooms[owner]['filename'] = file_name
                                return server.send(server.user_to_client(target), "waitReady", {'filename': file_name})
                    elif method == "waitReady" and value['filename']:
                        Method = "roomNotReady"
                        if data.get('filename') == value['filename']:
                            rooms[owner]['ready'] = True
                            Method = "roomIsReady"
                        else:
                            rooms[owner]['filename'] = None
                        for client in [owner, value['partner']]:
                            server.send(server.user_to_client(client), Method)


print("Server IS RUN")
server.run()
