"""Lightweight ES/EN routing for Onyx; ambiguous short text defaults to Spanish.

This is a word-based heuristic, not a general language detector. It does not
rewrite the user's text or turn Latin American Spanish into a regional accent.
"""
import re

SPANISH = frozenset('hola che vos tu tú yo soy estoy estás como cómo que qué de del el la los las un una y en para por con me te se lo es está esto eso gracias buen buenas bien podemos podés querés decime contame vamos dale listo hoy mañana ahora también música ayuda necesito tengo'.split())
ENGLISH = frozenset('hello hi hey you your i am is are the a an and in on for with of to this that it my we can could would should do does how what why where when thanks thank please today tomorrow now help need have ready let welcome'.split())


def pronunciation_language(text):
    words = re.findall(r"[^\W\d_]+", text.casefold())
    spanish = sum(word in SPANISH for word in words)
    english = sum(word in ENGLISH for word in words)
    return 'en-us' if english > spanish else 'es-419'


def speech_speed(rate):
    return max(.5, min(2.0, 1.08 * 2 ** (rate / 10)))
