"""
Prometheus metrics for advanced analysis module.
"""
import time
from functools import wraps

from prometheus_client import Counter, Histogram, Gauge

# Request counters
PRODUCT_LIFECYCLE_REQUESTS = Counter(
    "advanced_product_lifecycle_requests_total",
    "Total product lifecycle analysis requests",
    ["status"]
)

CUSTOMER_LIFECYCLE_REQUESTS = Counter(
    "advanced_customer_lifecycle_requests_total",
    "Total customer lifecycle analysis requests",
    ["status"]
)

PRODUCT_CLUSTER_REQUESTS = Counter(
    "advanced_product_cluster_requests_total",
    "Total product cluster analysis requests",
    ["status"]
)

CUSTOMER_CLUSTER_REQUESTS = Counter(
    "advanced_customer_cluster_requests_total",
    "Total customer cluster analysis requests",
    ["status"]
)

# Request latency histograms
PRODUCT_LIFECYCLE_DURATION = Histogram(
    "advanced_product_lifecycle_duration_seconds",
    "Product lifecycle analysis duration in seconds",
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

CUSTOMER_LIFECYCLE_DURATION = Histogram(
    "advanced_customer_lifecycle_duration_seconds",
    "Customer lifecycle analysis duration in seconds",
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

PRODUCT_CLUSTER_DURATION = Histogram(
    "advanced_product_cluster_duration_seconds",
    "Product cluster analysis duration in seconds",
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0]
)

CUSTOMER_CLUSTER_DURATION = Histogram(
    "advanced_customer_cluster_duration_seconds",
    "Customer cluster analysis duration in seconds",
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0]
)

# Data volume gauges
PRODUCT_LIFECYCLE_DATA_POINTS = Gauge(
    "advanced_product_lifecycle_data_points",
    "Number of product lifecycle data points in last request"
)

CUSTOMER_LIFECYCLE_DATA_POINTS = Gauge(
    "advanced_customer_lifecycle_data_points",
    "Number of customer lifecycle data points in last request"
)

PRODUCT_CLUSTER_DATA_POINTS = Gauge(
    "advanced_product_cluster_data_points",
    "Number of product cluster data points in last request"
)

CUSTOMER_CLUSTER_DATA_POINTS = Gauge(
    "advanced_customer_cluster_data_points",
    "Number of customer cluster data points in last request"
)

# Cluster quality metrics
CLUSTER_INERTIA = Histogram(
    "advanced_cluster_inertia",
    "K-Means inertia (within-cluster sum of squares)",
    ["cluster_type"],
    buckets=[100, 500, 1000, 5000, 10000, 50000, 100000]
)


def track_request(metric_counter, metric_duration, metric_gauge=None):
    """Decorator to track request metrics."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                metric_counter.labels(status="success").inc()
                if metric_gauge is not None and isinstance(result, dict):
                    data_points = len(result.get("lifecycle_data", []) or
                                     result.get("customer_data", []) or
                                     result.get("cluster_data", []))
                    metric_gauge.set(data_points)
                return result
            except Exception as e:
                metric_counter.labels(status="error").inc()
                raise
            finally:
                duration = time.time() - start_time
                metric_duration.observe(duration)
        return wrapper
    return decorator
