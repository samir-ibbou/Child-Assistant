#!/home/pi/GoogleEnv/bin/python

# This module playbacks a audio file with MPV player

import subprocess
import pyaudio
import wave
import sys
import pygame

def playback_audio_file(file):
    proc = subprocess.Popen(["mpv", file], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        stdout, stderr = proc.communicate(timeout=30)
    except:
        proc.kill()
        stdout, stderr = proc.communicate()
