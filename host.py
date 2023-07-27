from websocket import WebSocketApp
from json import dumps, loads

from threading import Thread

from pygetwindow import getActiveWindow
from vlc import Instance, MediaPlayer
from keyboard import on_press, wait
from time import time, sleep

verify = None
server = "ws://127.0.0.1:58978"


class VideoPlayer:
    def __init__(self, video_path):
        self.instance = Instance()
        self.media = self.instance.media_new(video_path)
        self.player: MediaPlayer = self.instance.media_player_new()
        self.player.set_media(self.media)
        self.fix = True
        self.video_path = video_path

    def hot_keys(self, event):
        active_window = getActiveWindow()
        if "VLC" in active_window.title:
            key = event.name.lower()
            match key:
                case "space":
                    self.player.pause()
                case "enter":
                    f_s = self.player.get_fullscreen()
                    self.player.set_fullscreen(not f_s)
                case "esc":
                    return self.finish()
                case "down" | "up":
                    self.set_volume(key)
                case "right" | "left":
                    self.set_seek(key)
                case "-":
                    return client.send_query(
                        "timeMatch", dict(
                            videotime=self.player.get_time(),
                            timestamp=time())
                    )
            if key == "*" or not self.fix:
                self.fix = not self.fix
            else:
                client.send_query("keyAction", dict(key=key))

    def action(self):
        self.player.play()
        on_press(self.hot_keys), wait()
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


player, video_path = None, ""


def functional_actions(action: str, needed={}):
    global player, video_path
    match action.lower():
        case "share":
            player = VideoPlayer(video_path)
            return player.action()
        case "pause":
            return player and player.player.set_pause(needed.get('stat'))
        case "set_path":
            video_path = input('enter the video path: ')
            client.send_query("getReady", dict(filename=video_path))


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
        self.on_error = lambda _, error: print(error) if "unreachable" not in str(error) else None
        self.on_message = on_message_handler
        self.on_close = self.close_check
        self.run_forever()


client = Client(server)


def match(v, r):
    while True:
        if player:
            return player.match_time(v, r)
        sleep(1)


def main(_, result):
    global verify, video_path
    res, method, query, status = loads(result), None, None, 'OK'
    Status, Method = res.get("status"), res.get("method")
    print(res)

    if Method == "register":
        method = "newUser"
        query = dict(username="radin", password='Python3++')

    elif Method == "newUser" and Status == "OK":
        verify = res['auth']
        if res.get("get_time"):
            return
        method = "newRoom"

    elif Method == "roomIsReady":
        client.close_check(functional_actions)
        client.send_query("openFile", dict(filename=video_path))
        if player:
            functional_actions('pause')
        else:
            Thread(target=functional_actions, args=("share",)).start()

    elif Method == "timeMatch":
        video_path = res.get('filename')
        client.close_check(functional_actions)
        if player:
            functional_actions('pause', {'stat': False})
        else:
            Thread(target=functional_actions, args=("share",)).start()

        Thread(target=match, args=(res.get('videotime'), res.get('timestamp'),)).start()

    elif Method == "clientLeft" and player:
        functional_actions('pause', {'stat': True})

    elif Method in ["joinRoom", "isOnRoom"]:
        if Method == "joinRoom":
            sleep(.2)
            client.send_query(
                "timeMatch", dict(
                    videotime=player.player.get_time(),
                    timestamp=time(),
                    filename=video_path,
                ),
            )
            functional_actions('pause', {'stat': False})
        else:
            return Thread(target=functional_actions, args=("set_path",)).start()

    elif Method == "keyAction":
        if res.get('key') == 'space' and player:
            player.player.pause()

    return client.send_query(method, query, status)


while True:
    client.run(main)
    if client.sock:
        client = Client(server)
    sleep(3), print("Re try")
