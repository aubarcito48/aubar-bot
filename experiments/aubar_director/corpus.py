"""Synthetic acting requests for Aubar, not emotional/personality diagnoses.

Templates define split groups: holdout wording is never used for training.
All visual IDs come from Aubar's own catalog. No Isa data or user chat logs.
"""
STYLES = {
    'angry': ('con enojo|enojado|furioso|con bronca', 'angrily|with anger|furiously|in an angry tone'),
    'happy': ('con alegría|alegre|contento|con felicidad', 'happily|with joy|cheerfully|in a happy tone'),
    'sad': ('con tristeza|triste|apenado|con pena', 'sadly|with sadness|sorrowfully|in a sad tone'),
    'scared': ('con miedo|asustado|con temor|atemorizado', 'fearfully|with fear|scared|in a frightened tone'),
    'surprised': ('con sorpresa|sorprendido|asombrado|con asombro', 'with surprise|surprised|astonished|in an amazed tone'),
    'curious': ('con curiosidad|curioso|intrigado|con interés', 'curiously|with curiosity|intrigued|in an inquisitive tone'),
    'confused': ('con confusión|confundido|desconcertado|sin entender', 'confused|with confusion|puzzled|in a bewildered tone'),
    'proud': ('con orgullo|orgulloso|con satisfacción|satisfecho', 'proudly|with pride|with satisfaction|in a proud tone'),
    'shy': ('con timidez|tímido|avergonzado|con vergüenza', 'shyly|with shyness|bashfully|in a shy tone'),
    'bored': ('con aburrimiento|aburrido|sin entusiasmo|desganado', 'with boredom|bored|without enthusiasm|in a bored tone'),
    'suspicious': ('con sospecha|desconfiado|con desconfianza|suspicaz', 'suspiciously|with suspicion|distrustfully|in a suspicious tone'),
    'playful': ('juguetón|con picardía|de forma juguetona|con humor juguetón', 'playfully|in a playful tone|mischievously|with playful humor'),
    'laughing': ('riendo|entre risas|con una risa|con carcajadas', 'laughing|with laughter|with a chuckle|while chuckling'),
    'excited': ('entusiasmado|emocionado|con entusiasmo|lleno de emoción', 'excitedly|with excitement|enthusiastically|in an excited tone'),
    'celebrate': ('festejando|celebrando|con festejo|con tono de celebración', 'celebrating|with celebration|in a celebratory tone|with a festive mood'),
}

TRAIN = {
    'es': ['Decime {style}: "Buen día, Nahuel."', 'Respondé {style}: "Estoy muy bien."',
           'Leé {style} la frase "Eso es interesante."', 'Quiero que hables {style} al saludar.',
           'Actuá {style} cuando digas "Buenas tardes."', 'Interpretá {style} este mensaje.'],
    'en': ['Say {style}: "Good morning, Nahuel."', 'Reply {style}: "I am doing well."',
           'Read {style} the phrase "That is interesting."', 'I want you to speak {style} when greeting me.',
           'Act {style} when saying "Good afternoon."', 'Perform this message {style}.'],
}
VALIDATION = {
    'es': ['Probemos una interpretación {style} para "Qué alegría verte."', 'Tu actuación tiene que sonar {style} en esta lectura.'],
    'en': ['Try a performance {style} for "Nice to see you."', 'Your acting should sound {style} in this reading.'],
}
TEST = {
    'es': ['Para el próximo saludo, hacé la actuación {style}: "Nos vemos mañana."'],
    'en': ['For the next greeting, deliver it {style}: "See you tomorrow."'],
}
NEGATIVE_TRAIN = {
    'es': ['Explicame qué significa actuar {style}.', 'No quiero que actúes {style}; contestá normalmente.',
           'Estoy {style}, necesito ayuda para organizarme.', 'La palabra {style} aparece en este cuento, resumilo.'],
    'en': ['Explain what acting {style} means.', 'Do not act {style}; answer normally.',
           'The word {style} appears in this story; summarize it.', 'My friend is {style}; explain the situation.'],
}
NEGATIVE_VALIDATION = {'es': ['Solo definí {style}, sin representarlo.'], 'en': ['Just define {style}, without acting it.']}
NEGATIVE_TEST = {'es': ['Hablamos de alguien {style}, no de tu forma de responder.'],
                 'en': ['We are discussing someone {style}, not how you should perform.']}
NEUTRAL = {
    'train': ['Hola, ¿cómo estás?', 'Contame algo interesante.', 'Explicame qué es una variable.',
              'Abrí YouTube.', 'Buscá música en YouTube.', 'What is a variable?', 'Hello there.',
              'Explain how to cook pasta.', 'Respondé sin actuar una emoción.', 'Answer in a neutral tone.'],
    'validation': ['Ayudame con mis tareas.', 'Tell me about computers.', '¿Cómo estará el día?', 'No actúes.'],
    'test': ['Necesito organizar mi semana.', 'Give me a brief explanation.', 'Muchas gracias por ayudarme.', 'Stay neutral.'],
}


def corpus():
    result = []
    for split, positive, negative in [('train', TRAIN, NEGATIVE_TRAIN),
                                      ('validation', VALIDATION, NEGATIVE_VALIDATION),
                                      ('test', TEST, NEGATIVE_TEST)]:
        for identifier, variants in STYLES.items():
            for language, choices in zip(('es', 'en'), variants):
                for style in choices.split('|'):
                    for template in positive[language]:
                        result.append({'question': template.format(style=style), 'label': 'ANIMATION:'+identifier,
                                       'split': split, 'language': language, 'kind': 'requested-acting'})
                    for template in negative[language]:
                        result.append({'question': template.format(style=style), 'label': 'EXPRESSION:neutral',
                                       'split': split, 'language': language, 'kind': 'mention-or-negation'})
        for question in NEUTRAL[split]:
            result.append({'question': question, 'label': 'EXPRESSION:neutral', 'split': split,
                           'language': 'mixed', 'kind': 'ordinary-chat'})
    return result
