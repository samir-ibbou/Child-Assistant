#!/home/pi/GoogleEnv/bin/python

# This module vocalise a sentence into a wav file

from gtts import gTTS
from io import BytesIO
import subprocess
import tempfile
import logging
try:
    from . import (
        playback
    )
except SystemError:
    import playback

def synth_mp3_object(sentence) : 
    mp3_fp = BytesIO()
    tts = gTTS(sentence, 'fr-fr')
    tts.write_to_fp(mp3_fp)
    return str(mp3_fp)

def synth_mp3_file(sentence) :
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as f:
        tts = gTTS(sentence, 'fr-fr')
        with open(f.name, 'wb') as fp:
            tts.write_to_fp(fp)
        f.seek(0)
        logging.debug('File name mp3: ' + f.name)        
        playback.playback_audio_file(f.name)
        f.close()