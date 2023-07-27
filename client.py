from websocket import WebSocketApp
from json import dumps, loads
from time import time, sleep

from threading import Thread

from vlc import Instance, MediaPlayer
from keyboard import wait, on_press
from os import path

datas = {}
with open('config.ini', 'r') as file:
    temp_key = ''
    for line in file.read().split('\n'):
        if '[' in line and ']' in line:
            temp_key = line.strip('[]')
        elif temp_key and line:
            datas[temp_key] = line
username, password, room = (
    datas.get('username'),
    datas.get('password'),
    datas.get('room'),
)
if not (username and password and room):
    print('invalid data'), exit()

verify, player = None, None
server = "ws://127.0.0.1:58978"


class VideoPlayer:
    def __init__(self, video_path):
        self.instance = Instance()
        self.media = self.instance.media_new(video_path)
        self.player: MediaPlayer = self.instance.media_player_new()
        self.player.set_media(self.media)
        self.video_path = video_path

    def hot_keys(self, key):
        if key == "space":
            self.player.pause()
        elif key == "enter":
            f_s = self.player.get_fullscreen()
            self.player.set_fullscreen(not f_s)
        elif key == "esc":
            return self.finish()
        elif key == "down" or key == "up":
            self.set_volume(key)
        elif key == "right" or key == "left":
            self.set_seek(key)
        # case _:
        #     # print(self.player.get_time())
        #     print(key)

    def limited_keys(self, event):
        key = event.name.lower()
        if key == 'space':
            self.player.pause()
            client.send_query("keyAction", dict(key=key))
        elif key == 'esc':
            return self.finish()

    def action(self):
        self.player.play(), on_press(self.limited_keys), wait()
        return self.finish()

    def finish(self):
        self.player.stop(), self.player.release(), exit()

    def set_time(self, ms):
        return self.player.set_time(int(int(ms)))

    def match_time(self, v: int, r: float):
        return self.player.set_time(
            v + int(round(time() - r, 3) * 1e3)
        )

    def set_seek(self, action='right', ms=5e3):
        if timestamp := self.player.get_time():
            try:
                return self.set_time(
                    timestamp + (1 if action == 'right' else -1) * ms
                )
            except:
                pass

    def set_volume(self, action='down'):
        volume = self.player.audio_get_volume()
        if (action == 'down' and volume > 0) or (action == 'up' and volume < 100):
            self.player.audio_set_volume(
                volume + (-1 if action == 'down' else 1) * 10
            )


class Client(WebSocketApp):
    def send_query(
            self, method,
            query: dict = None,
            status="OK",
    ):
        default = {
            'status': status,
            'method': method,
            'auth': verify,
        }
        query and default.update(query)
        return self.send(
            dumps(default)
        )

    def close_check(self, *_):
        player and player.player.set_pause(True)

    def run(self, on_message_handler):
        self.on_message = on_message_handler
        self.on_close = self.close_check
        self.run_forever()


client = Client(server)


def re_connect(stat):
    if player:
        player.player.set_pause(stat)


def match(v, r):
    while True:
        if player:
            return player.match_time(v, r)
        sleep(1)


video_path = ""


def main(server: Client, result):
    global verify, player, video_path
    res, method, query, status = loads(result), None, None, 'OK'
    Status, Method = res.get("status"), res.get("method")
    print(res)

    if Method == "register":
        method = "newUser"
        print(username, password)
        query = dict(username=username, password=password)

    elif Method == "newUser" and Status == "OK":
        verify = res['auth']
        if res.get("get_time"):
            return
        query = dict(roomID=room)
        method = "joinRoom"

    elif Method == "waitReady":
        method, name = Method, res.get('filename')
        query = dict(filename=path.exists(name) and name)

    elif Method == "openFile":
        video_path = res.get('filename')
        player = VideoPlayer(video_path)
        Thread(target=player.action).start()

    elif Method == "keyAction":
        player.hot_keys(res.get('key'))

    elif Method == "timeMatch":
        check = res.get('filename')
        if player:
            re_connect(False)
        elif check:
            player, video_path = VideoPlayer(check), check
            Thread(target=player.action).start()

        Thread(target=match, args=(res.get('videotime'), res.get('timestamp'),)).start()

    elif Method == "clientLeft":
        re_connect(True)

    elif Method == "joinRoom":
        sleep(.2)
        client.send_query(
            "timeMatch", dict(
                videotime=player.player.get_time(),
                timestamp=time(),
                filename=video_path,
            ),
        )
        re_connect(False)

    return client.send_query(method, query, status)


while True:
    client.run(main)
    if client.sock:
        client = Client(server)
    sleep(3), print("Re try")
