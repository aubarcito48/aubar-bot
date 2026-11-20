"""Local semantic features for Aubar's classifier. No downloads during inference.

Feature extractor: Sentence Transformers multilingual MiniLM (Apache-2.0).
Aubar's labels, classifier, acceptance thresholds and visual catalog are separate.
"""
from pc.aubar_control.paths import PROJECT_ROOT
from functools import lru_cache
import hashlib
from pathlib import Path
import re

FOLDER = PROJECT_ROOT/'models/aubar-director-minilm'
REVISION = 'e8f8c211226b894fcb81acc59f3b34ba3efd5f42'
REPOSITORY = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
ASSETS = (
    ('onnx/model_quint8_avx2.onnx', 'model.onnx', 118453870,
     '98a01d88b7de996cdea58c32ca71208c09968d143798814b2ea09d3439dc334f'),
    ('tokenizer.json', 'tokenizer.json', 9081518,
     '2c3387be76557bd40970cec13153b3bbf80407865484b209e655e5e4729076b8'),
)
ENCODER_VERSION = 'minilm-multilingual-aubar-request-v1'


def instruction(text):
    return re.sub(r'"[^"\n]*"|«[^»\n]*»', ' ', text[:1000]).strip()


@lru_cache(maxsize=1)
def _encoder():
    import onnxruntime as ort
    from tokenizers import Tokenizer
    for _, name, size, checksum in ASSETS:
        path = FOLDER/name
        if not path.is_file() or path.stat().st_size != size:
            raise ValueError('Aubar semantic encoder is not prepared')
        if hashlib.sha256(path.read_bytes()).hexdigest() != checksum:
            raise ValueError('Aubar semantic encoder checksum mismatch')
    options = ort.SessionOptions()
    options.intra_op_num_threads = 2
    options.inter_op_num_threads = 1
    options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    try:
        session = ort.InferenceSession(str(FOLDER/'model.onnx'), sess_options=options,
                                       providers=['CPUExecutionProvider'])
        tokenizer = Tokenizer.from_file(str(FOLDER/'tokenizer.json'))
    except Exception:
        raise ValueError('Aubar semantic encoder could not initialize') from None
    return tokenizer, session


def encode_many(questions):
    import numpy as np
    tokenizer, session = _encoder()
    results = []
    for offset in range(0, len(questions), 16):
        batch = questions[offset:offset+16]
        encoded = tokenizer.encode_batch([instruction(q) for q in batch])
        if any(not 0 < len(row.ids) <= 128 for row in encoded):
            raise ValueError('Aubar request exceeds semantic context; abstain')
        length = max(len(row.ids) for row in encoded)
        ids = np.zeros((len(batch), length), dtype=np.int64)
        mask = np.zeros_like(ids)
        for i, row in enumerate(encoded):
            ids[i, :len(row.ids)] = row.ids
            mask[i, :len(row.ids)] = 1
        fields = {'input_ids': ids, 'attention_mask': mask, 'token_type_ids': np.zeros_like(ids)}
        inputs = {item.name: fields[item.name] for item in session.get_inputs()}
        try:
            hidden = session.run(None, inputs)[0]
        except Exception:
            raise ValueError('Aubar semantic inference failed') from None
        vectors = (hidden * mask[..., None]).sum(axis=1) / mask.sum(axis=1, keepdims=True)
        vectors /= np.maximum(np.linalg.norm(vectors, axis=1, keepdims=True), 1e-9)
        if vectors.shape != (len(batch), 384) or not np.isfinite(vectors).all():
            raise ValueError('Invalid Aubar semantic features')
        results.extend(vectors)
    return np.asarray(results, dtype=np.float32)
