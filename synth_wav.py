#!/home/pi/GoogleEnv/bin/python

# This module vocalise a sentence into a wav file

import wave
from picotts import PicoTTS

def synth_wav(sentence):
    picotts = PicoTTS(voice='fr-FR')
    filename = picotts.synth_wav(sentence)
    wave.open(filename, 'rb')
    return filename