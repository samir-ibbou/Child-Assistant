#!/home/pi/GoogleEnv/bin/python

# This module vocalises a quiz game for children

import json
import time
import logging

try:
    from . import (
        synth_mp3,
        playback
    )
except SystemError:
    import synth_mp3
    import playback

json_file='/home/pi/GoogleEnv/lib/python3.5/site-packages/childassistant/quiz/animaux_celebres/debutant/data/openquizzdb_116.json'

def read_question(n):
    logging.info('Vocalise question ' + str(n) + ' from quiz')
    playback.playback_audio_file('/home/pi/GoogleEnv/lib/python3.5/site-packages/childassistant/quiz/animaux_celebres/debutant/audio/questions/question' + str(n) + '.mp3')

def read_reponses(n):
    logging.info('Vocalise responses from question ' + str(n))
    playback.playback_audio_file('/home/pi/GoogleEnv/lib/python3.5/site-packages/childassistant/quiz/animaux_celebres/debutant/audio/reponses/reponses' + str(n) + '.mp3')

def synth_questions():
    with open(json_file) as f:
        data = json.load(f)
    n=0
    for level in data['quizz']:
        if level=='débutant':
            for questions in data['quizz'][level]:
                logging.info('Vocalise question ' + str(n+1))
                synth_mp3.synth_mp3_file("Question " + str(data['quizz'][level][n]['id'])+ " : " + str(data['quizz'][level][n]['question']))
                n += 1
            #synth_mp3.synth_mp3_file("Question " + str(data['quizz'][level][n]['id'])+ " : " + str(data['quizz'][level][n]['question']) + "." + sentence)
            #playback.playback_audio_file('/home/pi/GoogleEnv/lib/python3.5/site-packages/childassistant/quiz/audio/animaux_celebres/debutant/question_1.mp3')
            #logging.info('Vocalise propositions from quiz')
            #time.sleep(10)
def synth_reponses():
    with open(json_file) as f:
        data = json.load(f)
    n=0
    for level in data['quizz']:
        if level=='débutant':
            for questions in data['quizz'][level]:
                propositions=''
                m=0
                for responses in data['quizz'][level][n]['propositions']:
                    propositions = propositions + "Réponse " + str(m+1) + " : " + str(data['quizz'][level][n]['propositions'][m] + ". ")
                    m += 1
                logging.info('Vocalise responses from question ' + str(data['quizz'][level][n]['id']))
                synth_mp3.synth_mp3_file(propositions)
                n += 1