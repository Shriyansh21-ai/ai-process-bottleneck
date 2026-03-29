from src.intelligence.duration import detect_duration_bottlenecks
from src.intelligence.waiting import detect_waiting_time
from src.intelligence.rework import detect_rework_loops
from src.intelligence.resource import detect_resource_overload
from src.intelligence.risk_engine import compute_risk_score

def run_bottleneck_engine(df):
    duration_bn, dur_threshold = detect_duration_bottlenecks(df)
    waiting_bn, wait_threshold = detect_waiting_time(df)
    rework_bn = detect_rework_loops(df)
    resource_bn, res_threshold = detect_resource_overload(df)

    df = compute_risk_score(df)

    return {
        "duration_bottlenecks": duration_bn,
        "duration_threshold": dur_threshold,
        "waiting_bottlenecks": waiting_bn,
        "waiting_threshold": wait_threshold,
        "rework_summary": rework_bn,
        "resource_overload": resource_bn,
        "resource_threshold": res_threshold,
        "risk_scored_tasks": df
    }
