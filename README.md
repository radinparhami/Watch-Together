# Watch Together **[ 1.0 ]**
> Master Files { server.py, host.py, client.py }

### server.py [ handle server and R-S data ]
> make db, control & match users.

### host.py [ room creater & movie controler ]
> create & share room, select & control video.

### client.py [ member of room, viewer ]
> link to config.ini & read data, make connection by datas.

#### Installation
```pip install -r reqiurements.txt```

## working steps
1. Start the server.
2. Run host.py and get RoomID ( automatic ).
3. Write the RoomID into **config.ini**.
4. Set video path by **client** [ Make sure that the video path is the same for the client and the host ].
5. Wait for many secons, when server said roomIsReady, the video playback process starts automatically with the host control.
