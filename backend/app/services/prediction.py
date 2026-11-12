"""Delay prediction: historical median baseline + optional CatBoost on synthetic history."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

DATA_PATH = Path(__file__).resolve().parents[3] / "data" / "synthetic_leg_history.csv"

# Cached metrics from last evaluation (synthetic)
_LAST_MAE: dict[str, float | None] = {"median": None, "catboost": None}


@dataclass
class DelayEstimate:
    extra_hours: float
    model_name: str
    mae_hours_holdout: float | None
    factors: list[dict]


def _load_history() -> pd.DataFrame | None:
    if not DATA_PATH.exists():
        return None
    df = pd.read_csv(DATA_PATH, parse_dates=["as_of", "actual_end"])
    return df


def evaluate_models() -> dict[str, float | None]:
    """Time-based split; features available_at implied by as_of. No future labels in training features."""
    global _LAST_MAE
    df = _load_history()
    if df is None or len(df) < 40:
        _LAST_MAE = {"median": None, "catboost": None}
        return _LAST_MAE

    df = df.sort_values("as_of")
    cutoff = df["as_of"].quantile(0.7)
    train = df[df["as_of"] <= cutoff]
    test = df[df["as_of"] > cutoff]
    if train.empty or test.empty:
        return _LAST_MAE

    # Median by mode (baseline)
    medians = train.groupby("mode")["delay_hours"].median().to_dict()
    pred_med = test["mode"].map(lambda m: medians.get(m, train["delay_hours"].median()))
    mae_med = float((pred_med - test["delay_hours"]).abs().mean())

    mae_cb: float | None = None
    try:
        from catboost import CatBoostRegressor

        features = ["weather_severity", "port_queue_hours", "doc_delay_hours", "mode"]
        X_train = train[features].copy()
        X_test = test[features].copy()
        # CatBoost handles categorical mode as string
        model = CatBoostRegressor(
            iterations=80,
            depth=4,
            learning_rate=0.1,
            verbose=False,
            allow_writing_files=False,
        )
        model.fit(X_train, train["delay_hours"], cat_features=["mode"])
        pred_cb = model.predict(X_test)
        mae_cb = float(pd.Series(pred_cb).sub(test["delay_hours"].values).abs().mean())
    except Exception:
        mae_cb = None

    _LAST_MAE = {"median": round(mae_med, 2), "catboost": round(mae_cb, 2) if mae_cb is not None else None}
    return _LAST_MAE


def estimate_extra_delay(
    *,
    mode: str,
    weather_severity: float,
    port_queue_hours: float,
    document_delay_hours: float,
) -> DelayEstimate:
    """Point estimate only — no confidence intervals without calibrated method."""
    metrics = _LAST_MAE if _LAST_MAE["median"] is not None else evaluate_models()
    df = _load_history()

    factors = []
    # Rule-augmented median: associative factors for UI, not causal claims
    weather_h = round(weather_severity * 10.0, 1)
    queue_h = round(max(0.0, port_queue_hours - 4.0) * 0.75, 1)
    doc_h = round(document_delay_hours, 1)

    baseline = 2.0
    if df is not None and not df.empty:
        subset = df[df["mode"] == mode]
        if not subset.empty:
            # Only rows with as_of in past relative to "now" already ensured in seed history
            baseline = float(subset["delay_hours"].median())

    # Prefer CatBoost point estimate when model MAE exists and is not worse by >20%
    use_cb = False
    cb_pred = None
    if metrics.get("catboost") is not None and metrics.get("median") is not None:
        if metrics["catboost"] <= metrics["median"] * 1.2:
            try:
                from catboost import CatBoostRegressor

                train = df.sort_values("as_of") if df is not None else None
                if train is not None and len(train) >= 40:
                    cutoff = train["as_of"].quantile(0.7)
                    tr = train[train["as_of"] <= cutoff]
                    model = CatBoostRegressor(
                        iterations=80, depth=4, learning_rate=0.1, verbose=False, allow_writing_files=False
                    )
                    model.fit(
                        tr[["weather_severity", "port_queue_hours", "doc_delay_hours", "mode"]],
                        tr["delay_hours"],
                        cat_features=["mode"],
                    )
                    import pandas as pd

                    row = pd.DataFrame(
                        [
                            {
                                "weather_severity": weather_severity,
                                "port_queue_hours": port_queue_hours,
                                "doc_delay_hours": document_delay_hours,
                                "mode": mode,
                            }
                        ]
                    )
                    cb_pred = float(model.predict(row)[0])
                    use_cb = True
            except Exception:
                use_cb = False

    if use_cb and cb_pred is not None:
        extra = max(0.0, cb_pred)
        model_name = "catboost_point_synthetic"
        mae = metrics.get("catboost")
    else:
        extra = max(0.0, baseline * 0.3 + weather_h + queue_h + doc_h * 0.5)
        model_name = "historical_median_baseline"
        mae = metrics.get("median")

    if weather_h > 0:
        factors.append(
            {
                "code": "weather",
                "label": "Погодные условия (демо)",
                "contribution_hours": weather_h,
                "note": "Ассоциативный фактор, не доказанная причина задержки.",
            }
        )
    if queue_h > 0:
        factors.append(
            {
                "code": "port_queue",
                "label": "Очередь / загрузка порта (демо)",
                "contribution_hours": queue_h,
                "note": "Ассоциативный фактор, не доказанная причина задержки.",
            }
        )
    if doc_h > 0:
        factors.append(
            {
                "code": "documents",
                "label": "Задержка документов (демо)",
                "contribution_hours": round(doc_h * 0.5, 1),
                "note": "Ассоциативный фактор, не доказанная причина задержки.",
            }
        )

    return DelayEstimate(
        extra_hours=round(extra, 1),
        model_name=model_name,
        mae_hours_holdout=mae,
        factors=factors,
    )
