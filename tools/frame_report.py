"""Summarize presentation intervals; no hardware performance claim from CI."""
import argparse
import json
import math


def summarize(intervals, hz):
    if hz <= 0 or not math.isfinite(hz) or not intervals:
        raise ValueError('positive refresh rate and nonempty samples required')
    if any(x <= 0 or not math.isfinite(x) for x in intervals):
        raise ValueError('intervals must be finite positive milliseconds')
    values = sorted(intervals)
    budget = 1000 / hz
    percentile = lambda p: values[max(0, math.ceil(len(values) * p) - 1)]
    return {'samples': len(values), 'refresh_hz': hz, 'budget_ms': budget,
            'p95_ms': percentile(.95), 'p99_ms': percentile(.99),
            'late_interval_ratio': sum(x > budget * 1.05 for x in values) / len(values)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('capture', help='JSON containing interval_ms and refresh_hz')
    args = parser.parse_args()
    with open(args.capture) as stream:
        capture = json.load(stream)
    print(json.dumps(summarize(capture['interval_ms'], capture['refresh_hz']), indent=2))
