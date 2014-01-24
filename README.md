pyws
====

pyws is a simple websocket server written in Python. It's in an early development state and has not yet every protocol standards implementend. Although early in progress, it's working, so feel free wo fork and extend it. 

Usage:
------
The WebSocketServer class is intended to be extended by a parent class and the handleClient() function should get an override there to make the class really useful.

This class can be used in Python version 2 and 3 as well.

A basic implementation would look like this: 

```python
import WebSocketServer

class Demo(WebSocketServer.WebSocketServer):
    def __init__(self, portno, debug=False):
        super(self.__class__, self).__init__(portno, debug)

    def handleClient(self, sock):
        data = self._fetch(sock)
        if data:
            print data

    def run(self):
        while(1):
            cli = self.accept()
            if cli:
                print "Client connected!"

# Start
demo = Demo(12345)
demo.run()
```

Save this file to demo.py and run it with: python demo.py

This would simply open a websocket server waiting for connections and printing data received to the console. Of course you have to add more logic to the class to make it useful, but that's up to you. ;)

To learn more on how to connect to a websocket server read the tutorial at:
http://www.html5rocks.com/en/tutorials/websockets/basics/
