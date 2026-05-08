from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Dict, List


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows = []
    with path.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def bootstrap_ci(sample: List[float], *, n_boot: int = 1000, alpha: float = 0.05, seed: int = 20260419) -> Dict[str, float]:
    rng = random.Random(seed)
    means = []
    for _ in range(n_boot):
        boot = [rng.choice(sample) for _ in range(len(sample))]
        means.append(mean(boot))
    means.sort()
    low_idx = int((alpha / 2) * len(means))
    high_idx = int((1 - alpha / 2) * len(means)) - 1
    return {
        'ci_low': round(means[low_idx], 4),
        'ci_high': round(means[max(high_idx, low_idx)], 4),
    }


def welch_like_score(sample_a: List[float], sample_b: List[float]) -> Dict[str, float]:
    mean_a = mean(sample_a)
    mean_b = mean(sample_b)
    std_a = pstdev(sample_a) if len(sample_a) > 1 else 0.0
    std_b = pstdev(sample_b) if len(sample_b) > 1 else 0.0
    denom = math.sqrt((std_a ** 2) / max(len(sample_a), 1) + (std_b ** 2) / max(len(sample_b), 1))
    score = 0.0 if denom == 0 else (mean_a - mean_b) / denom
    return {
        'mean_a': round(mean_a, 4),
        'mean_b': round(mean_b, 4),
        'std_a': round(std_a, 4),
        'std_b': round(std_b, 4),
        'welch_like_score': round(score, 4),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='进行 bootstrap 置信区间与轻量显著性分析。')
    parser.add_argument('--input-a', type=Path, required=True)
    parser.add_argument('--input-b', type=Path, required=True)
    parser.add_argument('--metric', type=str, default='oracle_final_utility')
    parser.add_argument('--n-boot', type=int, default=1000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows_a = load_jsonl(args.input_a)
    rows_b = load_jsonl(args.input_b)
    sample_a = [float(row[args.metric]) for row in rows_a]
    sample_b = [float(row[args.metric]) for row in rows_b]
    result = welch_like_score(sample_a, sample_b)
    result.update({f'a_{k}': v for k, v in bootstrap_ci(sample_a, n_boot=args.n_boot).items()})
    result.update({f'b_{k}': v for k, v in bootstrap_ci(sample_b, n_boot=args.n_boot).items()})
    print(result)


if __name__ == '__main__':
    main()
