#!/home/pi/GoogleEnv/bin/python3

import socket
import subprocess
import os, sys
import tempfile
import time

QUIT_CMD = b'{"command": ["quit"]}\n'

def _prepare_socket(self):
    """Create a random socket filename which we pass to mpv with the
        --input-unix-socket option.
    """
    fd, self._sock_filename = tempfile.mkstemp(prefix="mpv.")
    os.close(fd)
    os.remove(self._sock_filename)

def start_playback():
    fd, MPV_SOCKET = tempfile.mkstemp(prefix="mpv.")
    #os.close(fd)
    #os.remove(MPV_SOCKET)
    print (MPV_SOCKET)
    time.sleep(0.1)
    if os.path.exists(MPV_SOCKET):
        client = socket.socket(socket.AF_UNIX)
        try:
            client.connect(MPV_SOCKET)
            #client.send(QUIT_CMD)
            #client.close()
        except socket.error as e:
            return "already stopped or error while sending quit: %s" % e
    else:
        return "no mpv running"
    return MPV_SOCKET

def playback(uri):
    MPV_SOCKET = start_playback()
    print (MPV_SOCKET)
    proc = subprocess.Popen(["mpv", "--no-terminal", "--input-ipc-server="+MPV_SOCKET, "--", uri])
    proc.poll()
    #os.remove(MPV_SOCKET)

if __name__ == "__main__":
    playback('https://m.youtube.com/watch?v=nsxFgyAzNu4')
    #import time
    #time.sleep(1)
    #stop_playback()