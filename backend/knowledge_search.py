import json
import re
from collections import Counter
from math import sqrt

def load_list(raw):
    try:
        value = json.loads(raw or "[]")
        return value if isinstance(value, list) else []
    except (TypeError, ValueError):
        return []

def dump_list(value):
    return json.dumps(value, ensure_ascii=False)

def semantic_score(keyword, document):
    def features(value):
        value = re.sub(r"\s+", "", value.lower())
        tokens = re.findall(r"[a-z0-9_+#.-]+|[\u4e00-\u9fff]", value)
        joined = "".join(tokens)
        return Counter(tokens + [joined[i:i+2] for i in range(max(0, len(joined)-1))])
    left, right = features(keyword), features(document)
    dot = sum(v * right.get(k, 0) for k, v in left.items())
    norms = sqrt(sum(v*v for v in left.values())) * sqrt(sum(v*v for v in right.values()))
    return dot / norms if norms else 0.0
