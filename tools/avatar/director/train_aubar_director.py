"""Train a reproducible Aubar-only pilot; no Groq, microphone, USB or user logs."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.avatar.director.corpus import corpus
from pc.aubar_control.services.assistant.director.aubar_director import FEATURE_VERSION, WEIGHTS, catalog_hash


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=WEIGHTS)
    args = parser.parse_args()
    import numpy as np
    import sklearn
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score, balanced_accuracy_score, classification_report
    rows = corpus()
    train = [r for r in rows if r['split'] == 'train']
    validation = [r for r in rows if r['split'] == 'validation']
    test = [r for r in rows if r['split'] == 'test']
    # No shared complete request across partitions. Tokens necessarily overlap:
    # this pilot tests new wording of styles, not unseen vocabulary or real users.
    partitions = [{r['question'] for r in part} for part in (train, validation, test)]
    assert not any(partitions[i] & partitions[j] for i, j in ((0, 1), (0, 2), (1, 2)))
    from pc.aubar_control.services.assistant.director.director_encoder import encode_many, REVISION, REPOSITORY, ASSETS
    embedding_cache = ROOT/'tmp/aubar-director-embeddings.npz'
    key = hashlib.sha256((FEATURE_VERSION + json.dumps(rows, ensure_ascii=True, sort_keys=True)).encode()).hexdigest()
    if embedding_cache.is_file():
        with np.load(embedding_cache, allow_pickle=False) as data:
            all_vectors = data['vectors'] if str(data['key']) == key else None
    else:
        all_vectors = None
    if all_vectors is None:
        print('Encoding synthetic Aubar requests locally...', flush=True)
        all_vectors = encode_many([r['question'] for r in rows])
        embedding_cache.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(embedding_cache, key=key, vectors=all_vectors)
    indices = {r['question']: i for i, r in enumerate(rows)}
    def matrix(part):
        return all_vectors[[indices[row['question']] for row in part]]
    candidates = {
        'random-forest': RandomForestClassifier(n_estimators=96, max_depth=18, min_samples_leaf=1,
                         class_weight='balanced', max_features=.3, random_state=17011, n_jobs=1),
        'logistic-regression': LogisticRegression(C=10, class_weight={'EXPRESSION:neutral': 2.0}, max_iter=2000, random_state=17011),
    }
    targets = np.array([r['label'] for r in validation])
    comparison = {}
    def calibrate(model):
        vp = model.predict_proba(matrix(validation))
        predictions = model.classes_[vp.argmax(axis=1)]
        confidence = vp.max(axis=1)
        margin = confidence - np.sort(vp, axis=1)[:, -2]
        selection = None
        for cutoff in np.arange(.35, .96, .05):
            for gap in (.05, .1, .15, .2, .3):
                acting = (confidence >= cutoff) & (margin >= gap) & (predictions != 'EXPRESSION:neutral')
                precision = float((predictions[acting] == targets[acting]).mean()) if acting.any() else 0
                false_acts = int((acting & (targets == 'EXPRESSION:neutral')).sum())
                if precision >= .95 and false_acts == 0 and acting.sum() >= 10:
                    candidate = (int(acting.sum()), float(cutoff), gap)
                    if selection is None or candidate[0] > selection[0]:
                        selection = candidate
        return selection or (0, .99, .3)
    for name, candidate in candidates.items():
        candidate.fit(matrix(train), [r['label'] for r in train])
        selection = calibrate(candidate)
        comparison[name] = {'validation_raw_accuracy': float(accuracy_score(targets, candidate.predict(matrix(validation)))),
                            'validation_accepted_acts': selection[0], 'threshold': selection[1], 'margin': selection[2]}
    model_type = max(comparison, key=lambda name: (comparison[name]['validation_accepted_acts'], comparison[name]['validation_raw_accuracy']))
    classifier = candidates[model_type]
    vp = classifier.predict_proba(matrix(validation))
    labels = list(classifier.classes_)
    best = vp.argmax(axis=1)
    confidence = vp.max(axis=1)
    margin = confidence - np.sort(vp, axis=1)[:, -2]
    predictions = np.array(labels)[best]
    _, cutoff, gap = calibrate(classifier)
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    roots, left, right, columns, thresholds, probability = [], [], [], [], [], []
    for estimator in getattr(classifier, 'estimators_', []):
        tree = estimator.tree_
        offset = len(left)
        roots.append(offset)
        left.extend(np.where(tree.children_left < 0, -1, tree.children_left + offset))
        right.extend(np.where(tree.children_right < 0, -1, tree.children_right + offset))
        columns.extend(tree.feature)
        thresholds.extend(tree.threshold)
        value = tree.value[:, 0, :]
        probability.extend(value / value.sum(axis=1, keepdims=True))
    arrays = dict(roots=np.asarray(roots, dtype=np.int32),
                        left=np.asarray(left, dtype=np.int32), right=np.asarray(right, dtype=np.int32),
                        feature=np.asarray(columns, dtype=np.int32), threshold=np.asarray(thresholds, dtype=np.float32),
                        probability=np.asarray(probability, dtype=np.float32))
    if model_type == 'logistic-regression':
        arrays = {'coefficient': classifier.coef_.astype(np.float32), 'intercept': classifier.intercept_.astype(np.float32)}
    np.savez_compressed(output/'classifier.npz', **arrays)
    metadata = {'version': 'aubar-director-request-pilot-v1', 'feature_version': FEATURE_VERSION, 'model_type': model_type,
                'encoder_repository': REPOSITORY, 'encoder_revision': REVISION,
                'encoder_assets_sha256': {name: digest for _, name, _, digest in ASSETS},
                'catalog_sha256': catalog_hash(), 'labels': labels,
                'classifier_sha256': hashlib.sha256((output/'classifier.npz').read_bytes()).hexdigest(),
                'confidence_threshold': cutoff, 'margin_threshold': gap, 'max_depth': 18,
                'sklearn_training_version': sklearn.__version__, 'seed': 17011,
                'corpus_sha256': hashlib.sha256(json.dumps(rows, ensure_ascii=True, sort_keys=True).encode()).hexdigest()}
    (output/'model.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    reports = {}
    for name, part, probabilities in [('validation', validation, vp), ('test', test, classifier.predict_proba(matrix(test)))]:
        expected = np.array([r['label'] for r in part])
        raw = np.array(labels)[probabilities.argmax(axis=1)]
        accepted = (probabilities.max(axis=1) >= cutoff) & (
            probabilities.max(axis=1) - np.sort(probabilities, axis=1)[:, -2] >= gap)
        final = np.where(accepted, raw, 'EXPRESSION:neutral')
        acted = final != 'EXPRESSION:neutral'
        wrong = [{'question': r['question'], 'expected': r['label'], 'predicted': str(p),
                  'confidence': float(c), 'accepted': bool(a)}
                 for r, p, c, a in zip(part, final, probabilities.max(axis=1), accepted) if p != r['label']]
        reports[name] = {'count': len(part), 'raw_accuracy': float(accuracy_score(expected, raw)),
                         'final_accuracy': float(accuracy_score(expected, final)),
                         'balanced_final_accuracy': float(balanced_accuracy_score(expected, final)),
                         'accepted_fraction': float(accepted.mean()), 'expressive_decisions': int(acted.sum()),
                         'expressive_precision': float((expected[acted] == final[acted]).mean()) if acted.any() else None,
                         'false_acting_on_mentions': int((acted & (expected == 'EXPRESSION:neutral')).sum()),
                         'per_class': classification_report(expected, final, output_dict=True, zero_division=0),
                         'errors': wrong}
    report = {'scope': 'synthetic requested acting only; not general conversation or lip sync accuracy',
              'train_count': len(train), 'validation_selected_threshold': cutoff,
              'validation_selected_margin': gap, 'catalog_sha256': catalog_hash(),
              'runtime_classifier_bytes': (output/'classifier.npz').stat().st_size,
              'comparison': comparison, 'selected': model_type, 'results': reports}
    destination = ROOT/'tmp/director-training/report.json'
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({name: {k: v for k, v in result.items() if k not in ('errors', 'per_class')}
                      for name, result in reports.items()}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
