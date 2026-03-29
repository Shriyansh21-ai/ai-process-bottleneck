import statistics

def run_ml_analysis(input_data: dict):
    durations = input_data.get("durations", [])

    if not durations:
        return {"status": "no_data"}

    avg = statistics.mean(durations)
    threshold = avg * 1.5

    bottlenecks = [d for d in durations if d > threshold]

    return {
        "average_duration": avg,
        "threshold": threshold,
        "bottleneck_count": len(bottlenecks)
    }
