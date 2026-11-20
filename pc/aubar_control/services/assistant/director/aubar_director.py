"""Aubar's local performance director; never executes functions.

The learned pilot recognizes requested acting styles, not a person's emotion.
The full visual catalog remains available through explicit local commands.
Runtime uses NumPy arrays, never pickle, sklearn, network or Isa weights.
"""
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
import re
from pathlib import Path

from ....models.avatar.ai_avatar import AvatarReply, PerformanceSegment, normalize_reply, safe_avatar_action
from ....models.avatar.catalog import CATALOG
from ...recognition.voice_commands import match_command
from .director_encoder import ENCODER_VERSION, REVISION, instruction
from ...recognition.voice_commands import normalize

WEIGHTS = Path(__file__).with_name('director_weights')
FEATURE_VERSION = ENCODER_VERSION
ONYX_PROFILES = {
    'angry': (.98, 1.08, 120), 'sad': (.94, .92, 180),
    'excited': (1.04, 1.05, 80), 'scared': (.97, .96, 140),
    'shy': (.96, .94, 120), 'laughing': (1.03, 1.02, 80),
}


def catalog_hash():
    return hashlib.sha256(json.dumps(CATALOG, sort_keys=True, ensure_ascii=True).encode()).hexdigest()


@dataclass(frozen=True)
class DirectorDecision:
    reply: AvatarReply
    origin: str
    label: str
    confidence: float


@lru_cache(maxsize=1)
def _model():
    import numpy as np
    if (WEIGHTS/'model.json').stat().st_size > 65536 or (WEIGHTS/'classifier.npz').stat().st_size > 16*1024*1024:
        raise ValueError('Aubar classifier artifact too large')
    metadata = json.loads((WEIGHTS/'model.json').read_text(encoding='utf-8'))
    payload = (WEIGHTS/'classifier.npz').read_bytes()
    if (metadata['feature_version'] != FEATURE_VERSION or metadata['encoder_revision'] != REVISION or metadata['catalog_sha256'] != catalog_hash()
        or hashlib.sha256(payload).hexdigest() != metadata['classifier_sha256']):
        raise ValueError('Aubar director artifact mismatch')
    if (metadata['model_type'] not in ('logistic-regression', 'random-forest')
        or not 2 <= len(metadata['labels']) <= 51 or len(set(metadata['labels'])) != len(metadata['labels'])
        or not 0 <= metadata['confidence_threshold'] <= 1 or not 0 <= metadata['margin_threshold'] <= 1
        or type(metadata['max_depth']) is not int or not 1 <= metadata['max_depth'] <= 32):
        raise ValueError('Invalid Aubar classifier metadata')
    keys = ('coefficient', 'intercept') if metadata['model_type'] == 'logistic-regression' else (
        'roots', 'left', 'right', 'feature', 'threshold', 'probability')
    with np.load(WEIGHTS/'classifier.npz', allow_pickle=False) as data:
        arrays = {key: data[key].copy() for key in keys}
    for label in metadata['labels']:
        kind, identifier = label.split(':', 1)
        if safe_avatar_action(kind, identifier)[1]:
            raise ValueError('Unknown Aubar visual class')
    if metadata['model_type'] == 'logistic-regression':
        if (arrays['coefficient'].shape != (len(metadata['labels']), 384)
            or arrays['intercept'].shape != (len(metadata['labels']),)
            or any(not np.isfinite(a).all() for a in arrays.values())):
            raise ValueError('Invalid Aubar linear classifier')
        return metadata, arrays
    n = len(arrays['left'])
    if (not 0 < n <= 200000 or not 1 <= len(arrays['roots']) <= 256
        or arrays['probability'].shape != (n, len(metadata['labels']))
        or any(arrays[key].shape != (n,) for key in ('right', 'feature', 'threshold'))
        or any(arrays[key].dtype.kind not in 'iu' for key in ('roots', 'left', 'right', 'feature'))
        or not np.isfinite(arrays['probability']).all() or not np.isfinite(arrays['threshold']).all()
        or np.any(arrays['probability'] < 0) or not np.allclose(arrays['probability'].sum(axis=1), 1)):
        raise ValueError('Invalid Aubar forest')
    return metadata, arrays


def predict_style(question):
    import numpy as np
    from .director_encoder import encode_many
    metadata, model = _model()
    vector = encode_many([question])[0]
    if metadata['model_type'] == 'logistic-regression':
        logits = model['coefficient'] @ vector + model['intercept']
        probabilities = np.exp(logits - logits.max())
        probabilities /= probabilities.sum()
        return _decision(metadata, probabilities)
    probabilities = np.zeros(len(metadata['labels']))
    for root in model['roots']:
        node = int(root)
        for _ in range(metadata['max_depth'] + 1):
            if not 0 <= node < len(model['left']):
                raise ValueError('Invalid Aubar tree index')
            left, right = int(model['left'][node]), int(model['right'][node])
            if left < 0 and right < 0:
                probabilities += model['probability'][node]
                break
            column = int(model['feature'][node])
            if left <= node or right <= node or not 0 <= column < len(vector):
                raise ValueError('Invalid Aubar tree branch')
            node = left if vector[column] <= model['threshold'][node] else right
        else:
            raise ValueError('Aubar tree exceeds depth budget')
    probabilities /= len(model['roots'])
    return _decision(metadata, probabilities)


def _decision(metadata, probabilities):
    import numpy as np
    order = np.argsort(probabilities)
    best = int(order[-1])
    confidence = float(probabilities[best])
    margin = confidence - float(probabilities[order[-2]])
    accepted = confidence >= metadata['confidence_threshold'] and margin >= metadata['margin_threshold']
    return metadata['labels'][best], confidence, accepted


def direct_reply(text, question):
    """Preserve approved words; choose only catalog visuals and bounded Onyx controls."""
    neutral = normalize_reply(text)
    if not isinstance(question, str) or not question.strip() or len(question) > 1000 or '\x00' in question:
        return DirectorDecision(neutral, 'invalid-request', 'EXPRESSION:neutral', 0.0)
    action = match_command(question)
    if action is not None and action.command in ('EXPRESSION', 'ANIMATION') and action.look is None:
        # This chooses a visual. No USB command, browser action or MODE is executed.
        return DirectorDecision(AvatarReply(neutral.text, action, False), 'explicit-catalog',
                                action.command + ':' + action.argument, 1.0)
    # A requested gentle smile is different from laughter or exuberant joy.
    # Ignore quoted dialogue: the words to speak must not select an emotion.
    cue = normalize(instruction(question))
    negative = ('sin sonreir', 'sin sonrisa', 'without smiling', 'no smile',
                'no actues', 'no quiero que actues', 'sin actuar', 'sin representarlo',
                'do not act', 'without acting', 'just define', 'solo defini')
    if any(phrase in cue for phrase in negative):
        return DirectorDecision(AvatarReply(neutral.text, neutral.action, False),
                                'explicit-neutral', 'EXPRESSION:neutral', 1.0)
    acting = re.search(r'\b(?:decime|deci|decilo|dime|di|dilo|lee|leeme|habla|hables|'
                       r'responde|actua|interpreta|say|reply|read|speak|act|perform)\b', cue)
    if (cue in ('sonrei', 'sonrie', 'sonreir', 'smile') or acting and (
        any(word in cue.split() for word in ('sonriendo', 'smiling')) or
        any(phrase in cue for phrase in ('con una sonrisa', 'con sonrisa', 'with a smile')))):
        action, _ = safe_avatar_action('EXPRESSION', 'contento')
        return DirectorDecision(AvatarReply(neutral.text, action, False),
                                'explicit-smile', 'EXPRESSION:contento', 1.0)
    # Direct acting instructions take priority over uncertain learned wording.
    # Only inspect the start of the instruction, never the quoted spoken words.
    if acting and not re.search(r'\b(?:explicame|explica|defini|define|significa|explain|means)\b', cue):
        delivery = cue[acting.end():].strip()
        for identifier, forms in (
            ('laughing', r'riendo|con risa|con una risa|laughing|with laughter'),
            ('sad', r'con tristeza|triste|tristemente|sadly|with sadness'),
            ('angry', r'con enojo|enojado|con bronca|angrily|with anger'),
            ('happy', r'contento|alegre|con alegria|happily|cheerfully'),
        ):
            if re.match(r'(?:(?:esto|eso|el texto|un texto|la frase|este mensaje)\s+)?(?:'+forms+r')\b', delivery):
                action, _ = safe_avatar_action('ANIMATION', identifier)
                return DirectorDecision(AvatarReply(neutral.text, action, False),
                                        'explicit-style', 'ANIMATION:'+identifier, 1.0)
    try:
        label, confidence, accepted = predict_style(question)
        if not accepted:
            return DirectorDecision(neutral, 'uncertain', label, confidence)
        kind, identifier = label.split(':', 1)
        action, invalid = safe_avatar_action(kind, identifier)
        if invalid:
            raise ValueError('Unavailable Aubar action')
        speed, energy, pause = ONYX_PROFILES.get(identifier, (1.0, 1.0, 0))
        segment = PerformanceSegment(neutral.text, action, 'Aubar Director local', speed, energy, pause)
        return DirectorDecision(AvatarReply(neutral.text, action, False, (segment,)),
                                'local-classifier-pilot', label, confidence)
    except (OSError, ValueError, KeyError, TypeError, ImportError):
        return DirectorDecision(neutral, 'model-unavailable', 'EXPRESSION:neutral', 0.0)


class AubarDirector:
    """Entry point owned by Aubar; local visual direction cannot dispatch functions."""
    def direct(self, text, request):
        return direct_reply(text, request.question).reply
