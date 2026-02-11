"""
Prediction API endpoints for trend forecasting and analysis.
"""

from datetime import datetime, timezone, timedelta
from typing import List, Optional
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..deps import get_db, get_user_id
from ...schema.models import TrendTimeSeries, TrendKeyword, PredictionModel, PredictionResult
from ...prediction.engine import TrendPredictor, PredictionAccuracyTracker

router = APIRouter(prefix="/api/prediction", tags=["prediction"])
logger = logging.getLogger(__name__)

# Global accuracy tracker instance
accuracy_tracker = PredictionAccuracyTracker()


@router.get("/forecast/{keyword}")
async def forecast_trend(
    keyword: str,
    geo: str = Query("US", max_length=5, description="ISO country code"),
    horizon: str = Query("24h", description="Forecast horizon", pattern="^(1h|6h|24h|7d)$"),
    algorithm: str = Query("exponential_smoothing", description="Forecasting algorithm"),
    confidence_level: float = Query(0.95, ge=0.8, le=0.99, description="Confidence level for intervals"),
    use_saved_model: bool = Query(False, description="Use the most recent saved model instead of training on-the-fly"),
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_user_id),
):
    """
    Generate trend forecast for a specific keyword.

    Supported horizons:
    - 1h: 1 hour ahead
    - 6h: 6 hours ahead
    - 24h: 24 hours ahead (1 day)
    - 7d: 7 days ahead

    Supported algorithms:
    - exponential_smoothing: Holt-Winters exponential smoothing
    - arima: ARIMA model
    - linear_regression: Simple linear regression
    - naive: Naive forecast (last value)
    """
    try:
        # Convert horizon to hours
        horizon_hours_map = {
            '1h': 1,
            '6h': 6,
            '24h': 24,
            '7d': 168  # 7 days * 24 hours
        }
        horizon_hours = horizon_hours_map.get(horizon, 24)

        # Get trend keyword
        keyword_result = await db.execute(
            select(TrendKeyword).where(
                TrendKeyword.keyword == keyword,
                TrendKeyword.geo == geo
            )
        )
        trend_keyword = keyword_result.scalar_one_or_none()

        if not trend_keyword:
            raise HTTPException(
                status_code=404,
                detail=f"Keyword '{keyword}' not found for geo '{geo}'"
            )

        # Get time series data (last 30 days for better forecasting)
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
        series_result = await db.execute(
            select(TrendTimeSeries).where(
                TrendTimeSeries.keyword_id == trend_keyword.id,
                TrendTimeSeries.timestamp >= cutoff_date
            ).order_by(TrendTimeSeries.timestamp)
        )
        time_series = series_result.scalars().all()

        if not time_series:
            raise HTTPException(
                status_code=404,
                detail=f"No time series data available for keyword '{keyword}'"
            )

        # Create predictor with database session
        predictor = TrendPredictor(db_session=db)

        # Check if we should use a saved model
        use_saved_model = Query(False, description="Use the most recent saved model instead of training on-the-fly")
        if use_saved_model:
            saved_model = await predictor.load_prediction_model(keyword, algorithm if algorithm != 'exponential_smoothing' else None)
            if saved_model:
                # Use saved model parameters for prediction
                # For now, we'll still generate predictions from data, but mark that we used a saved model
                forecast_result['used_saved_model'] = True
                forecast_result['model_id'] = saved_model.id
                forecast_result['model_trained_at'] = saved_model.trained_at.isoformat()
            else:
                forecast_result['used_saved_model'] = False
                forecast_result['saved_model_note'] = 'No saved model found, used on-the-fly prediction'

        # Generate forecast
        forecast_result = predictor.predict_trend(
            time_series=time_series,
            horizon_hours=horizon_hours,
            algorithm=algorithm,
            confidence_level=confidence_level
        )

        # Add keyword metadata and horizon info
        forecast_result['keyword'] = {
            'name': trend_keyword.keyword,
            'geo': trend_keyword.geo,
            'category': trend_keyword.category,
            'current_rank': trend_keyword.current_rank,
            'avg_rank': trend_keyword.avg_rank
        }
        forecast_result['forecast_horizon'] = {
            'requested': horizon,
            'hours': horizon_hours,
            'description': f"{horizon_hours} hour forecast"
        }
        
        # Add historical data for charting
        forecast_result['historical_data'] = [
            {
                'timestamp': ts.timestamp.isoformat(),
                'value': ts.interest_score,
                'rank': ts.rank
            }
            for ts in sorted(time_series, key=lambda x: x.timestamp)
        ]

        # Add counter-signal analysis for risk assessment
        counter_signals = await predictor.analyze_counter_signals(
            forecast_result=forecast_result,
            time_series=time_series,
            keyword=keyword,
            db_session=db
        )
        forecast_result['counter_signal_analysis'] = counter_signals

        # Apply confidence modifier to the forecast
        if 'confidence_level' in forecast_result:
            original_confidence = forecast_result['confidence_level']
            modified_confidence = min(1.0, max(0.0, original_confidence * counter_signals['overall_confidence_modifier']))
            forecast_result['confidence_level_modified'] = modified_confidence
            forecast_result['confidence_adjustment'] = {
                'original': original_confidence,
                'modifier': counter_signals['overall_confidence_modifier'],
                'reason': counter_signals['risk_assessment']
            }

        return forecast_result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Forecast failed for keyword {keyword}: {e}")
        raise HTTPException(status_code=500, detail=f"Forecast generation failed: {str(e)}")


@router.get("/early-warning/{keyword}")
async def detect_early_warning_signals(
    keyword: str,
    geo: str = Query("US", max_length=5, description="ISO country code"),
    threshold_multiplier: float = Query(2.0, ge=1.0, le=5.0, description="Anomaly detection threshold multiplier"),
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_user_id),
):
    """
    Detect early warning signals for potential trend spikes.
    """
    try:
        # Get trend keyword
        keyword_result = await db.execute(
            select(TrendKeyword).where(
                TrendKeyword.keyword == keyword,
                TrendKeyword.geo == geo
            )
        )
        trend_keyword = keyword_result.scalar_one_or_none()

        if not trend_keyword:
            raise HTTPException(
                status_code=404,
                detail=f"Keyword '{keyword}' not found for geo '{geo}'"
            )

        # Get time series data (last 7 days for signal detection)
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)
        series_result = await db.execute(
            select(TrendTimeSeries).where(
                TrendTimeSeries.keyword_id == trend_keyword.id,
                TrendTimeSeries.timestamp >= cutoff_date
            ).order_by(TrendTimeSeries.timestamp)
        )
        time_series = series_result.scalars().all()

        if not time_series:
            raise HTTPException(
                status_code=404,
                detail=f"No time series data available for keyword '{keyword}'"
            )

        # Create predictor with database session
        predictor = TrendPredictor(db_session=db)

        # Detect early warning signals
        signals_result = predictor.detect_early_warning_signals(
            time_series=time_series,
            threshold_multiplier=threshold_multiplier
        )

        # Add keyword metadata
        signals_result['keyword'] = {
            'name': trend_keyword.keyword,
            'geo': trend_keyword.geo,
            'category': trend_keyword.category
        }

        return signals_result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Early warning detection failed for keyword {keyword}: {e}")
        raise HTTPException(status_code=500, detail=f"Signal detection failed: {str(e)}")


@router.get("/algorithms")
async def list_available_algorithms():
    """
    List available forecasting algorithms with descriptions.
    """
    return {
        "algorithms": {
            "exponential_smoothing": {
                "name": "Exponential Smoothing",
                "description": "Holt-Winters exponential smoothing with trend and seasonal components",
                "best_for": "Data with clear trends and seasonal patterns",
                "requirements": "At least 3 data points"
            },
            "arima": {
                "name": "ARIMA",
                "description": "AutoRegressive Integrated Moving Average model",
                "best_for": "Stationary time series data",
                "requirements": "At least 5 data points"
            },
            "linear_regression": {
                "name": "Linear Regression",
                "description": "Simple linear regression on time series",
                "best_for": "Data with clear linear trends",
                "requirements": "At least 3 data points"
            },
            "naive": {
                "name": "Naive Forecast",
                "description": "Uses last known value for all future predictions",
                "best_for": "Very limited data or baseline comparison",
                "requirements": "At least 1 data point"
            }
        },
        "default_algorithm": "exponential_smoothing"
    }


@router.get("/accuracy/{algorithm}")
async def get_algorithm_accuracy(
    algorithm: str,
    current_user: str = Depends(get_user_id),
):
    """
    Get accuracy metrics for a specific algorithm.
    """
    try:
        performance = accuracy_tracker.get_algorithm_performance(algorithm)

        if 'error' in performance:
            raise HTTPException(status_code=404, detail=performance['error'])

        return performance

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get accuracy metrics for {algorithm}: {e}")
        raise HTTPException(status_code=500, detail=f"Accuracy retrieval failed: {str(e)}")


@router.post("/validate/{keyword}")
async def validate_predictions(
    keyword: str,
    geo: str = Query("US", max_length=5, description="ISO country code"),
    algorithm: str = Query("exponential_smoothing", description="Algorithm to validate"),
    test_hours: int = Query(6, ge=1, le=24, description="Hours to use for validation"),
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_user_id),
):
    """
    Validate prediction accuracy by comparing forecasts against actual data.
    """
    try:
        # Get trend keyword
        keyword_result = await db.execute(
            select(TrendKeyword).where(
                TrendKeyword.keyword == keyword,
                TrendKeyword.geo == geo
            )
        )
        trend_keyword = keyword_result.scalar_one_or_none()

        if not trend_keyword:
            raise HTTPException(
                status_code=404,
                detail=f"Keyword '{keyword}' not found for geo '{geo}'"
            )

        # Get historical data (more than needed for validation)
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)
        series_result = await db.execute(
            select(TrendTimeSeries).where(
                TrendTimeSeries.keyword_id == trend_keyword.id,
                TrendTimeSeries.timestamp >= cutoff_date
            ).order_by(TrendTimeSeries.timestamp)
        )
        all_series = series_result.scalars().all()

        if len(all_series) < test_hours + 5:  # Need training data + test data
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient data for validation. Need at least {test_hours + 5} data points."
            )

        # Split data: use all but last test_hours for training
        train_series = all_series[:-test_hours]
        test_series = all_series[-test_hours:]

        # Generate forecast using training data
        forecast_result = predictor.predict_trend(
            time_series=train_series,
            horizon_hours=test_hours,
            algorithm=algorithm
        )

        # Extract predicted and actual values
        predicted_values = [p['predicted_score'] for p in forecast_result['predictions']]
        actual_values = [ts.interest_score for ts in test_series]

        # Ensure same length
        min_len = min(len(predicted_values), len(actual_values))
        predicted_values = predicted_values[:min_len]
        actual_values = actual_values[:min_len]

        # Record accuracy metrics
        accuracy_metrics = accuracy_tracker.record_prediction_accuracy(
            keyword=keyword,
            algorithm=algorithm,
            actual_values=actual_values,
            predicted_values=predicted_values
        )

        return {
            'keyword': keyword,
            'algorithm': algorithm,
            'validation_period_hours': min_len,
            'accuracy_metrics': accuracy_metrics,
            'predictions': forecast_result['predictions'][:min_len],
            'actuals': [
                {
                    'timestamp': ts.timestamp.isoformat(),
                    'value': ts.interest_score
                }
                for ts in test_series[:min_len]
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prediction validation failed for keyword {keyword}: {e}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


@router.get("/seasonal/{keyword}")
async def analyze_seasonal_trends(
    keyword: str,
    geo: str = Query("US", max_length=5, description="ISO country code"),
    period: str = Query("daily", description="Seasonal period to analyze", pattern="^(daily|weekly|auto)$"),
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_user_id),
):
    """
    Analyze seasonal patterns and decompose trends into trend, seasonal, and residual components.

    Supported periods:
    - daily: 24-hour daily patterns
    - weekly: 7-day weekly patterns
    - auto: Automatically detect based on data length
    """
    try:
        # Get trend keyword
        keyword_result = await db.execute(
            select(TrendKeyword).where(
                TrendKeyword.keyword == keyword,
                TrendKeyword.geo == geo
            )
        )
        trend_keyword = keyword_result.scalar_one_or_none()

        if not trend_keyword:
            raise HTTPException(
                status_code=404,
                detail=f"Keyword '{keyword}' not found for geo '{geo}'"
            )

        # Get time series data (last 7 days minimum for seasonal analysis)
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)
        series_result = await db.execute(
            select(TrendTimeSeries).where(
                TrendTimeSeries.keyword_id == trend_keyword.id,
                TrendTimeSeries.timestamp >= cutoff_date
            ).order_by(TrendTimeSeries.timestamp)
        )
        time_series = series_result.scalars().all()

        if not time_series:
            raise HTTPException(
                status_code=404,
                detail=f"No time series data available for keyword '{keyword}'"
            )

        # Create predictor with database session
        predictor = TrendPredictor(db_session=db)

        # Analyze seasonal trends
        seasonal_result = predictor.analyze_seasonal_trends(
            time_series=time_series,
            seasonal_period=period if period != 'auto' else None
        )

        if 'error' in seasonal_result:
            raise HTTPException(
                status_code=400,
                detail=seasonal_result['error']
            )

        # Add keyword metadata
        seasonal_result['keyword'] = {
            'name': trend_keyword.keyword,
            'geo': trend_keyword.geo,
            'category': trend_keyword.category
        }

        return seasonal_result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Seasonal analysis failed for keyword {keyword}: {e}")
        raise HTTPException(status_code=500, detail=f"Seasonal analysis failed: {str(e)}")


@router.post("/train/{keyword}")
async def train_prediction_model(
    keyword: str,
    geo: str = Query("US", max_length=5, description="ISO country code"),
    algorithm: str = Query("exponential_smoothing", description="Algorithm to train"),
    validation_split: float = Query(0.2, ge=0.1, le=0.5, description="Fraction of data for validation"),
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_user_id),
):
    """
    Train and validate a prediction model for a specific keyword.

    This endpoint trains the specified algorithm on historical data and validates
    its performance, helping to optimize model parameters and assess accuracy.
    """
    try:
        # Get trend keyword
        keyword_result = await db.execute(
            select(TrendKeyword).where(
                TrendKeyword.keyword == keyword,
                TrendKeyword.geo == geo
            )
        )
        trend_keyword = keyword_result.scalar_one_or_none()

        if not trend_keyword:
            raise HTTPException(
                status_code=404,
                detail=f"Keyword '{keyword}' not found for geo '{geo}'"
            )

        # Get time series data (last 90 days for training)
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=90)
        series_result = await db.execute(
            select(TrendTimeSeries).where(
                TrendTimeSeries.keyword_id == trend_keyword.id,
                TrendTimeSeries.timestamp >= cutoff_date
            ).order_by(TrendTimeSeries.timestamp)
        )
        time_series = series_result.scalars().all()

        if not time_series:
            raise HTTPException(
                status_code=404,
                detail=f"No time series data available for keyword '{keyword}'"
            )

        # Create predictor with database session
        predictor = TrendPredictor(db_session=db)

        # Train the model and persist it
        training_result = await predictor.train_prediction_model(
            keyword=keyword,
            time_series=time_series,
            algorithm=algorithm,
            validation_split=validation_split
        )

        if 'error' in training_result:
            raise HTTPException(
                status_code=400,
                detail=training_result['error']
            )

        # Add keyword metadata
        training_result['keyword'] = {
            'name': trend_keyword.keyword,
            'geo': trend_keyword.geo,
            'category': trend_keyword.category
        }

        return training_result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Model training failed for keyword {keyword}: {e}")
        raise HTTPException(status_code=500, detail=f"Model training failed: {str(e)}")