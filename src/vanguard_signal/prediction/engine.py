"""
Trend prediction engine for forecasting future trend behavior.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.seasonal import seasonal_decompose
from sklearn.metrics import mean_absolute_error, mean_squared_error

from ..schema.models import TrendTimeSeries, PredictionModel, PredictionResult, TrendKeyword
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class TrendPredictor:
    """
    Core trend prediction engine with multiple forecasting algorithms.
    """

    def __init__(self, db_session: Optional[AsyncSession] = None):
        self.db_session = db_session
        self.models = {
            'exponential_smoothing': self._exponential_smoothing_forecast,
            'arima': self._arima_forecast,
            'linear_regression': self._linear_regression_forecast,
            'naive': self._naive_forecast,
        }

    def predict_trend(
        self,
        time_series: List[TrendTimeSeries],
        horizon_hours: int = 24,
        algorithm: str = 'exponential_smoothing',
        confidence_level: float = 0.95
    ) -> Dict[str, Any]:
        """
        Generate trend predictions for the given time series.

        Args:
            time_series: List of TrendTimeSeries objects
            horizon_hours: Number of hours to forecast
            algorithm: Forecasting algorithm to use
            confidence_level: Confidence level for prediction intervals

        Returns:
            Dictionary containing predictions, confidence intervals, and metadata
        """
        if not time_series:
            return self._empty_prediction()

        # Convert to pandas DataFrame
        df = self._time_series_to_dataframe(time_series)

        if len(df) < 3:
            # Not enough data for meaningful prediction
            return self._naive_prediction(df, horizon_hours)

        try:
            predictor_func = self.models.get(algorithm, self._exponential_smoothing_forecast)
            return predictor_func(df, horizon_hours, confidence_level)
        except Exception as e:
            logger.error(f"Prediction failed with {algorithm}: {e}")
            # Fallback to naive prediction
            return self._naive_prediction(df, horizon_hours)

    def _time_series_to_dataframe(self, time_series: List[TrendTimeSeries]) -> pd.DataFrame:
        """Convert TrendTimeSeries objects to pandas DataFrame."""
        data = []
        for ts in sorted(time_series, key=lambda x: x.timestamp):
            data.append({
                'timestamp': ts.timestamp,
                'interest_score': ts.interest_score,
                'rank': ts.rank
            })

        df = pd.DataFrame(data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp').sort_index()

        # Resample to hourly data if needed
        df = df.resample('H').mean().fillna(method='ffill')

        return df

    def _exponential_smoothing_forecast(
        self,
        df: pd.DataFrame,
        horizon_hours: int,
        confidence_level: float
    ) -> Dict[str, Any]:
        """Exponential smoothing forecast."""
        try:
            # Use interest_score for forecasting
            series = df['interest_score'].dropna()

            if len(series) < 3:
                return self._naive_prediction(df, horizon_hours)

            # Fit exponential smoothing model
            model = ExponentialSmoothing(
                series,
                seasonal_periods=24,  # Daily seasonality
                trend='add',
                seasonal='add'
            ).fit()

            # Generate forecast
            forecast = model.forecast(horizon_hours)

            # Calculate confidence intervals (simplified)
            mse = mean_squared_error(series[-24:], model.fittedvalues[-24:]) if len(series) >= 24 else series.var()
            std_error = np.sqrt(mse)
            z_score = 1.96  # 95% confidence
            confidence_interval = std_error * z_score

            predictions = []
            last_timestamp = df.index[-1]

            for i, pred_value in enumerate(forecast):
                timestamp = last_timestamp + timedelta(hours=i+1)
                predictions.append({
                    'timestamp': timestamp.isoformat(),
                    'predicted_score': max(0, float(pred_value)),
                    'lower_bound': max(0, float(pred_value - confidence_interval)),
                    'upper_bound': max(0, float(pred_value + confidence_interval)),
                    'confidence_level': confidence_level
                })

            return {
                'algorithm': 'exponential_smoothing',
                'predictions': predictions,
                'metadata': {
                    'horizon_hours': horizon_hours,
                    'data_points': len(series),
                    'model_fit_quality': self._calculate_model_quality(series, model.fittedvalues),
                    'trend_direction': self._analyze_trend_direction(forecast),
                    'seasonal_pattern': True
                }
            }

        except Exception as e:
            logger.error(f"Exponential smoothing failed: {e}")
            return self._naive_prediction(df, horizon_hours)

    def _arima_forecast(
        self,
        df: pd.DataFrame,
        horizon_hours: int,
        confidence_level: float
    ) -> Dict[str, Any]:
        """ARIMA forecast."""
        try:
            series = df['interest_score'].dropna()

            if len(series) < 5:
                return self._naive_prediction(df, horizon_hours)

            # Fit ARIMA model (simplified parameters)
            model = ARIMA(series, order=(1, 1, 1)).fit()

            # Generate forecast with confidence intervals
            forecast_result = model.get_forecast(steps=horizon_hours)

            predictions = []
            last_timestamp = df.index[-1]

            for i in range(horizon_hours):
                timestamp = last_timestamp + timedelta(hours=i+1)
                pred_mean = forecast_result.predicted_mean.iloc[i]
                pred_ci = forecast_result.conf_int().iloc[i]

                predictions.append({
                    'timestamp': timestamp.isoformat(),
                    'predicted_score': max(0, float(pred_mean)),
                    'lower_bound': max(0, float(pred_ci[0])),
                    'upper_bound': max(0, float(pred_ci[1])),
                    'confidence_level': confidence_level
                })

            return {
                'algorithm': 'arima',
                'predictions': predictions,
                'metadata': {
                    'horizon_hours': horizon_hours,
                    'data_points': len(series),
                    'model_fit_quality': self._calculate_model_quality(series, model.fittedvalues),
                    'trend_direction': self._analyze_trend_direction(forecast_result.predicted_mean),
                    'seasonal_pattern': False
                }
            }

        except Exception as e:
            logger.error(f"ARIMA forecast failed: {e}")
            return self._naive_prediction(df, horizon_hours)

    def _linear_regression_forecast(
        self,
        df: pd.DataFrame,
        horizon_hours: int,
        confidence_level: float
    ) -> Dict[str, Any]:
        """Simple linear regression forecast."""
        try:
            series = df['interest_score'].dropna()

            if len(series) < 3:
                return self._naive_prediction(df, horizon_hours)

            # Create time index
            x = np.arange(len(series))
            y = series.values

            # Fit linear regression
            coeffs = np.polyfit(x, y, 1)
            slope, intercept = coeffs

            # Generate predictions
            predictions = []
            last_timestamp = df.index[-1]

            for i in range(horizon_hours):
                future_x = len(series) + i
                pred_value = slope * future_x + intercept
                timestamp = last_timestamp + timedelta(hours=i+1)

                # Simple confidence interval based on residuals
                residuals = y - (slope * x + intercept)
                std_error = np.std(residuals)
                z_score = 1.96
                confidence_interval = std_error * z_score

                predictions.append({
                    'timestamp': timestamp.isoformat(),
                    'predicted_score': max(0, float(pred_value)),
                    'lower_bound': max(0, float(pred_value - confidence_interval)),
                    'upper_bound': max(0, float(pred_value + confidence_interval)),
                    'confidence_level': confidence_level
                })

            return {
                'algorithm': 'linear_regression',
                'predictions': predictions,
                'metadata': {
                    'horizon_hours': horizon_hours,
                    'data_points': len(series),
                    'model_fit_quality': self._calculate_model_quality(series, slope * x + intercept),
                    'trend_direction': 'increasing' if slope > 0 else 'decreasing',
                    'seasonal_pattern': False
                }
            }

        except Exception as e:
            logger.error(f"Linear regression forecast failed: {e}")
            return self._naive_prediction(df, horizon_hours)

    def _naive_forecast(
        self,
        df: pd.DataFrame,
        horizon_hours: int,
        confidence_level: float = 0.95
    ) -> Dict[str, Any]:
        """Naive forecast using last value."""
        return self._naive_prediction(df, horizon_hours, confidence_level)

    def _naive_prediction(
        self,
        df: pd.DataFrame,
        horizon_hours: int,
        confidence_level: float = 0.95
    ) -> Dict[str, Any]:
        """Generate naive prediction using last known value."""
        if df.empty:
            return self._empty_prediction()

        last_value = df['interest_score'].iloc[-1]
        last_timestamp = df.index[-1]

        # Calculate standard deviation for confidence intervals
        std_dev = df['interest_score'].std() if len(df) > 1 else abs(last_value) * 0.1
        z_score = 1.96  # 95% confidence
        confidence_interval = std_dev * z_score

        predictions = []
        for i in range(horizon_hours):
            timestamp = last_timestamp + timedelta(hours=i+1)
            predictions.append({
                'timestamp': timestamp.isoformat(),
                'predicted_score': max(0, float(last_value)),
                'lower_bound': max(0, float(last_value - confidence_interval)),
                'upper_bound': max(0, float(last_value + confidence_interval)),
                'confidence_level': confidence_level
            })

        return {
            'algorithm': 'naive',
            'predictions': predictions,
            'metadata': {
                'horizon_hours': horizon_hours,
                'data_points': len(df),
                'model_fit_quality': 0.0,  # No model to fit
                'trend_direction': 'stable',
                'seasonal_pattern': False
            }
        }

    def _empty_prediction(self) -> Dict[str, Any]:
        """Return empty prediction structure."""
        return {
            'algorithm': 'none',
            'predictions': [],
            'metadata': {
                'horizon_hours': 0,
                'data_points': 0,
                'model_fit_quality': 0.0,
                'trend_direction': 'unknown',
                'seasonal_pattern': False
            }
        }

    def _calculate_model_quality(self, actual: pd.Series, fitted: pd.Series) -> float:
        """Calculate model fit quality (0-1, higher is better)."""
        try:
            if len(actual) != len(fitted):
                return 0.0

            # Calculate R-squared
            ss_res = np.sum((actual - fitted) ** 2)
            ss_tot = np.sum((actual - actual.mean()) ** 2)

            if ss_tot == 0:
                return 1.0 if ss_res == 0 else 0.0

            r_squared = 1 - (ss_res / ss_tot)
            return max(0.0, min(1.0, r_squared))

        except Exception:
            return 0.0

    def _analyze_trend_direction(self, forecast: pd.Series) -> str:
        """Analyze the direction of the trend."""
        try:
            if len(forecast) < 2:
                return 'stable'

            start_value = forecast.iloc[0]
            end_value = forecast.iloc[-1]

            change_percent = (end_value - start_value) / abs(start_value) if start_value != 0 else 0

            if change_percent > 0.05:
                return 'increasing'
            elif change_percent < -0.05:
                return 'decreasing'
            else:
                return 'stable'

        except Exception:
            return 'unknown'

    def analyze_seasonal_trends(
        self,
        time_series: List[TrendTimeSeries],
        period: Optional[str] = 'daily'
    ) -> Dict[str, Any]:
        """
        Analyze seasonal patterns and decompose trends into components.

        Args:
            time_series: Time series data
            period: Seasonality period ('daily', 'weekly', or None for auto-detect)

        Returns:
            Dictionary with seasonal decomposition results
        """
        if not time_series or len(time_series) < 24:  # Need at least a day of data
            return {
                'error': 'Insufficient data for seasonal analysis',
                'required_minimum': 24,
                'available_points': len(time_series) if time_series else 0
            }

        df = self._time_series_to_dataframe(time_series)
        series = df['interest_score'].dropna()

        if len(series) < 24:
            return {
                'error': 'Insufficient data for seasonal analysis',
                'required_minimum': 24,
                'available_points': len(series)
            }

        try:
            # Determine seasonality period
            if period == 'daily':
                seasonal_periods = 24  # Assuming hourly data
            elif period == 'weekly':
                seasonal_periods = 168  # 7 days * 24 hours
            else:
                # Auto-detect based on data length
                if len(series) >= 168:
                    seasonal_periods = 168  # Weekly
                elif len(series) >= 24:
                    seasonal_periods = 24   # Daily
                else:
                    seasonal_periods = None

            if seasonal_periods is None or len(series) < seasonal_periods * 2:
                return {
                    'error': 'Data too short for meaningful seasonal decomposition',
                    'detected_period': seasonal_periods,
                    'available_points': len(series)
                }

            # Perform seasonal decomposition
            decomposition = seasonal_decompose(
                series,
                model='additive',
                period=seasonal_periods,
                extrapolate_trend='freq'
            )

            # Extract components
            trend_component = decomposition.trend.dropna()
            seasonal_component = decomposition.seasonal.dropna()
            residual_component = decomposition.resid.dropna()

            # Calculate seasonal strength
            seasonal_strength = 1 - (residual_component.var() / (trend_component.var() + seasonal_component.var()))

            # Analyze seasonal patterns
            seasonal_patterns = self._analyze_seasonal_patterns(seasonal_component, seasonal_periods)

            # Detect anomalies in residuals
            residual_anomalies = self._detect_residual_anomalies(residual_component)

            return {
                'seasonal_analysis': {
                    'period': period,
                    'seasonal_periods': seasonal_periods,
                    'seasonal_strength': max(0, min(1, float(seasonal_strength))),
                    'decomposition_quality': self._calculate_model_quality(series, trend_component + seasonal_component)
                },
                'components': {
                    'trend': {
                        'values': [{'timestamp': idx.isoformat(), 'value': float(val)}
                                 for idx, val in trend_component.items()],
                        'direction': self._analyze_trend_direction(trend_component),
                        'slope': float(np.polyfit(range(len(trend_component)), trend_component.values, 1)[0])
                    },
                    'seasonal': {
                        'pattern': [{'hour': i % seasonal_periods, 'value': float(val)}
                                  for i, val in enumerate(seasonal_component.values)],
                        'amplitude': float(seasonal_component.max() - seasonal_component.min()),
                        'peak_hour': int(seasonal_component.idxmax().hour) if hasattr(seasonal_component.idxmax(), 'hour') else None
                    },
                    'residual': {
                        'values': [{'timestamp': idx.isoformat(), 'value': float(val)}
                                 for idx, val in residual_component.items()],
                        'variance': float(residual_component.var()),
                        'anomalies': residual_anomalies
                    }
                },
                'patterns': seasonal_patterns,
                'metadata': {
                    'data_points': len(series),
                    'analysis_period': f"{df.index[0].isoformat()} to {df.index[-1].isoformat()}",
                    'frequency': 'hourly'
                }
            }

        except Exception as e:
            logger.error(f"Seasonal analysis failed: {e}")
            return {'error': f'Seasonal analysis failed: {str(e)}'}

    def _analyze_seasonal_patterns(self, seasonal_component: pd.Series, periods: int) -> Dict[str, Any]:
        """Analyze seasonal patterns and extract insights."""
        try:
            patterns = {}

            # Peak and trough analysis
            peak_idx = seasonal_component.idxmax()
            trough_idx = seasonal_component.idxmin()

            patterns['peaks_and_troughs'] = {
                'peak_time': peak_idx.isoformat() if peak_idx else None,
                'peak_value': float(seasonal_component.max()),
                'trough_time': trough_idx.isoformat() if trough_idx else None,
                'trough_value': float(seasonal_component.min())
            }

            # Daily pattern (if applicable)
            if periods == 24:
                hourly_pattern = []
                for hour in range(24):
                    hour_values = seasonal_component[seasonal_component.index.hour == hour]
                    if not hour_values.empty:
                        hourly_pattern.append({
                            'hour': hour,
                            'average_effect': float(hour_values.mean()),
                            'volatility': float(hour_values.std())
                        })

                patterns['daily_pattern'] = hourly_pattern

                # Identify busy hours
                busy_hours = [p['hour'] for p in hourly_pattern
                            if p['average_effect'] > np.mean([p['average_effect'] for p in hourly_pattern]) + np.std([p['average_effect'] for p in hourly_pattern])]

                patterns['busy_hours'] = busy_hours

            # Weekly pattern (if applicable)
            elif periods == 168:
                daily_pattern = []
                for day in range(7):
                    day_values = seasonal_component[seasonal_component.index.dayofweek == day]
                    if not day_values.empty:
                        daily_pattern.append({
                            'day': day,
                            'day_name': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][day],
                            'average_effect': float(day_values.mean()),
                            'volatility': float(day_values.std())
                        })

                patterns['weekly_pattern'] = daily_pattern

                # Identify busy days
                if daily_pattern:
                    avg_effect = np.mean([p['average_effect'] for p in daily_pattern])
                    std_effect = np.std([p['average_effect'] for p in daily_pattern])
                    busy_days = [p['day_name'] for p in daily_pattern
                               if p['average_effect'] > avg_effect + std_effect]

                    patterns['busy_days'] = busy_days

            return patterns

        except Exception as e:
            logger.error(f"Seasonal pattern analysis failed: {e}")
            return {'error': str(e)}

    async def train_prediction_model(
        self,
        keyword: str,
        time_series: List[TrendTimeSeries],
        algorithm: str = 'exponential_smoothing',
        validation_split: float = 0.2
    ) -> Dict[str, Any]:
        """
        Train and validate a prediction model on historical data.

        Args:
            time_series: Training time series data
            algorithm: Algorithm to train
            validation_split: Fraction of data to use for validation

        Returns:
            Dictionary with training results and model performance
        """
        if not time_series or len(time_series) < 10:
            return {
                'error': 'Insufficient data for model training',
                'required_minimum': 10,
                'available_points': len(time_series) if time_series else 0
            }

        df = self._time_series_to_dataframe(time_series)
        series = df['interest_score'].dropna()

        if len(series) < 10:
            return {
                'error': 'Insufficient data for model training',
                'required_minimum': 10,
                'available_points': len(series)
            }

        try:
            # Split data for training and validation
            split_idx = int(len(series) * (1 - validation_split))
            train_series = series[:split_idx]
            val_series = series[split_idx:]

            if len(val_series) < 3:
                return {
                    'error': 'Validation set too small',
                    'validation_points': len(val_series),
                    'required_minimum': 3
                }

            training_results = {}

            # Train the model on training data
            if algorithm == 'exponential_smoothing':
                training_results = self._train_exponential_smoothing_model(train_series, val_series)
            elif algorithm == 'arima':
                training_results = self._train_arima_model(train_series, val_series)
            elif algorithm == 'linear_regression':
                training_results = self._train_linear_regression_model(train_series, val_series)
            else:
                return {'error': f'Unsupported algorithm for training: {algorithm}'}

            # Add metadata
            training_results.update({
                'algorithm': algorithm,
                'training_data_points': len(train_series),
                'validation_data_points': len(val_series),
                'total_data_points': len(series),
                'training_period': f"{train_series.index[0].isoformat()} to {train_series.index[-1].isoformat()}",
                'validation_period': f"{val_series.index[0].isoformat()} to {val_series.index[-1].isoformat()}",
                'trained_at': datetime.now(timezone.utc).isoformat()
            })

            # Save the trained model to database if session is available
            if self.db_session and 'error' not in training_results:
                try:
                    # Extract model parameters based on algorithm
                    model_params = self._extract_model_parameters(training_results, algorithm)

                    saved_model = await self.save_prediction_model(
                        keyword=keyword,
                        model_type=algorithm,
                        model_parameters=model_params,
                        training_results=training_results,
                        training_data_start=train_series.index[0].to_pydatetime(),
                        training_data_end=train_series.index[-1].to_pydatetime(),
                        training_samples=len(train_series)
                    )

                    training_results['model_id'] = saved_model.id
                    training_results['saved_to_database'] = True

                    logger.info(f"Successfully saved trained {algorithm} model for keyword '{keyword}'")

                except Exception as e:
                    logger.error(f"Failed to save trained model to database: {e}")
                    training_results['database_save_error'] = str(e)

            return training_results

        except Exception as e:
            logger.error(f"Model training failed for {algorithm}: {e}")
            return {'error': f'Model training failed: {str(e)}'}

    def _train_exponential_smoothing_model(self, train_series: pd.Series, val_series: pd.Series) -> Dict[str, Any]:
        """Train and validate exponential smoothing model."""
        try:
            # Try different parameter combinations
            best_model = None
            best_score = float('inf')
            best_params = {}

            param_combinations = [
                {'trend': 'add', 'seasonal': 'add', 'seasonal_periods': 24},
                {'trend': 'add', 'seasonal': None, 'seasonal_periods': None},
                {'trend': None, 'seasonal': 'add', 'seasonal_periods': 24},
                {'trend': None, 'seasonal': None, 'seasonal_periods': None},
            ]

            for params in param_combinations:
                try:
                    model = ExponentialSmoothing(
                        train_series,
                        trend=params['trend'],
                        seasonal=params['seasonal'],
                        seasonal_periods=params['seasonal_periods']
                    ).fit()

                    # Generate predictions for validation period
                    pred_steps = len(val_series)
                    predictions = model.forecast(pred_steps)

                    # Calculate validation error
                    mse = mean_squared_error(val_series, predictions)
                    rmse = np.sqrt(mse)

                    if rmse < best_score:
                        best_score = rmse
                        best_model = model
                        best_params = params

                except Exception:
                    continue

            if best_model is None:
                return {'error': 'Could not fit any exponential smoothing model'}

            # Calculate final validation metrics
            final_predictions = best_model.forecast(len(val_series))
            mae = mean_absolute_error(val_series, final_predictions)
            mse = mean_squared_error(val_series, final_predictions)
            rmse = np.sqrt(mse)
            mape = np.mean(np.abs((val_series.values - final_predictions.values) / val_series.values)) * 100

            return {
                'model_type': 'exponential_smoothing',
                'best_parameters': best_params,
                'validation_metrics': {
                    'mae': float(mae),
                    'mse': float(mse),
                    'rmse': float(rmse),
                    'mape': float(mape),
                    'accuracy_score': max(0, 100 - mape)
                },
                'training_quality': self._calculate_model_quality(train_series, best_model.fittedvalues),
                'model_summary': {
                    'trend_component': best_params.get('trend'),
                    'seasonal_component': best_params.get('seasonal'),
                    'seasonal_periods': best_params.get('seasonal_periods')
                }
            }

        except Exception as e:
            logger.error(f"Exponential smoothing training failed: {e}")
            return {'error': f'Training failed: {str(e)}'}

    def _train_arima_model(self, train_series: pd.Series, val_series: pd.Series) -> Dict[str, Any]:
        """Train and validate ARIMA model."""
        try:
            # Try different ARIMA orders
            best_model = None
            best_score = float('inf')
            best_order = None

            orders = [(1, 1, 1), (1, 1, 0), (0, 1, 1), (2, 1, 1), (1, 1, 2)]

            for order in orders:
                try:
                    model = ARIMA(train_series, order=order).fit()

                    # Generate predictions for validation period
                    pred_steps = len(val_series)
                    predictions = model.forecast(pred_steps)

                    # Calculate validation error
                    mse = mean_squared_error(val_series, predictions)
                    rmse = np.sqrt(mse)

                    if rmse < best_score:
                        best_score = rmse
                        best_model = model
                        best_order = order

                except Exception:
                    continue

            if best_model is None:
                return {'error': 'Could not fit any ARIMA model'}

            # Calculate final validation metrics
            final_predictions = best_model.forecast(len(val_series))
            mae = mean_absolute_error(val_series, final_predictions)
            mse = mean_squared_error(val_series, final_predictions)
            rmse = np.sqrt(mse)
            mape = np.mean(np.abs((val_series.values - final_predictions.values) / val_series.values)) * 100

            return {
                'model_type': 'arima',
                'best_parameters': {'order': best_order},
                'validation_metrics': {
                    'mae': float(mae),
                    'mse': float(mse),
                    'rmse': float(rmse),
                    'mape': float(mape),
                    'accuracy_score': max(0, 100 - mape)
                },
                'training_quality': self._calculate_model_quality(train_series, best_model.fittedvalues),
                'model_summary': {
                    'ar_order': best_order[0],
                    'differencing_order': best_order[1],
                    'ma_order': best_order[2]
                }
            }

        except Exception as e:
            logger.error(f"ARIMA training failed: {e}")
            return {'error': f'Training failed: {str(e)}'}

    def _train_linear_regression_model(self, train_series: pd.Series, val_series: pd.Series) -> Dict[str, Any]:
        """Train and validate linear regression model."""
        try:
            # Prepare data
            x_train = np.arange(len(train_series))
            y_train = train_series.values

            x_val = np.arange(len(train_series), len(train_series) + len(val_series))
            y_val = val_series.values

            # Fit linear regression
            coeffs = np.polyfit(x_train, y_train, 1)
            slope, intercept = coeffs

            # Generate predictions
            predictions = slope * x_val + intercept

            # Calculate validation metrics
            mae = mean_absolute_error(y_val, predictions)
            mse = mean_squared_error(y_val, predictions)
            rmse = np.sqrt(mse)
            mape = np.mean(np.abs((y_val - predictions) / y_val)) * 100

            # Calculate training fit quality
            fitted_values = slope * x_train + intercept
            training_quality = self._calculate_model_quality(train_series, fitted_values)

            return {
                'model_type': 'linear_regression',
                'best_parameters': {'slope': float(slope), 'intercept': float(intercept)},
                'validation_metrics': {
                    'mae': float(mae),
                    'mse': float(mse),
                    'rmse': float(rmse),
                    'mape': float(mape),
                    'accuracy_score': max(0, 100 - mape)
                },
                'training_quality': training_quality,
                'model_summary': {
                    'slope': float(slope),
                    'intercept': float(intercept),
                    'trend_direction': 'increasing' if slope > 0 else 'decreasing'
                }
            }

        except Exception as e:
            logger.error(f"Linear regression training failed: {e}")
            return {'error': f'Training failed: {str(e)}'}

    async def analyze_counter_signals(
        self,
        forecast_result: Dict[str, Any],
        time_series: List[TrendTimeSeries],
        keyword: str,
        db_session: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Analyze counter-signals for a bullish forecast to identify disconfirming evidence.

        This implements the Counter-Signal Engine to reduce false positives by actively
        searching for opposing trends, historical failures, and contradictory indicators.

        Args:
            forecast_result: The forecast result from predict_trend
            time_series: Original time series data
            keyword: The keyword being analyzed
            db_session: Database session for additional queries

        Returns:
            Dictionary with counter-signal analysis results
        """
        counter_signals = {
            'overall_confidence_modifier': 1.0,  # Multiplier for forecast confidence
            'disconfirming_evidence': [],
            'historical_precedents': [],
            'opposing_trends': [],
            'risk_assessment': 'low',
            'recommendations': []
        }

        try:
            # 1. Check for opposing trends in related keywords
            if db_session:
                opposing_trends = await self._find_opposing_trends(keyword, forecast_result, db_session)
                counter_signals['opposing_trends'] = opposing_trends

                if opposing_trends:
                    counter_signals['disconfirming_evidence'].append({
                        'type': 'opposing_trends',
                        'severity': 'medium',
                        'description': f"Found {len(opposing_trends)} related keywords with opposing trends",
                        'details': opposing_trends
                    })

            # 2. Analyze historical cases where similar signals failed
            historical_failures = self._analyze_historical_failures(forecast_result, time_series)
            counter_signals['historical_precedents'] = historical_failures

            if historical_failures:
                failure_rate = len(historical_failures) / max(1, len(time_series) // 24)  # Rough daily estimate
                if failure_rate > 0.3:
                    counter_signals['disconfirming_evidence'].append({
                        'type': 'historical_failures',
                        'severity': 'high',
                        'description': f"High historical failure rate ({failure_rate:.1%}) for similar signals",
                        'details': historical_failures
                    })

            # 3. Check for overbought conditions or momentum exhaustion
            momentum_analysis = self._analyze_momentum_exhaustion(time_series, forecast_result)
            if momentum_analysis['exhausted']:
                counter_signals['disconfirming_evidence'].append({
                    'type': 'momentum_exhaustion',
                    'severity': 'medium',
                    'description': momentum_analysis['reason'],
                    'details': momentum_analysis
                })

            # 4. Assess signal persistence and decay potential
            persistence_check = self._check_signal_persistence(time_series, forecast_result)
            if not persistence_check['persistent']:
                counter_signals['disconfirming_evidence'].append({
                    'type': 'weak_persistence',
                    'severity': 'medium',
                    'description': persistence_check['reason'],
                    'details': persistence_check
                })

            # Calculate overall confidence modifier
            evidence_count = len(counter_signals['disconfirming_evidence'])
            high_severity = sum(1 for e in counter_signals['disconfirming_evidence'] if e['severity'] == 'high')

            if high_severity > 0:
                counter_signals['overall_confidence_modifier'] = 0.5  # Significant reduction
                counter_signals['risk_assessment'] = 'high'
                counter_signals['recommendations'].append("Strong counter-evidence detected - consider reducing position size")
            elif evidence_count > 2:
                counter_signals['overall_confidence_modifier'] = 0.7
                counter_signals['risk_assessment'] = 'medium'
                counter_signals['recommendations'].append("Multiple counter-signals present - monitor closely")
            elif evidence_count > 0:
                counter_signals['overall_confidence_modifier'] = 0.9
                counter_signals['risk_assessment'] = 'low'
                counter_signals['recommendations'].append("Minor counter-signals noted - proceed with caution")
            else:
                counter_signals['risk_assessment'] = 'low'
                counter_signals['recommendations'].append("No significant counter-evidence found - confidence boost applied")

            # If no counter-evidence, this itself boosts confidence
            if not counter_signals['disconfirming_evidence']:
                counter_signals['overall_confidence_modifier'] = 1.2  # Slight boost for clean signals

        except Exception as e:
            logger.error(f"Counter-signal analysis failed: {e}")
            counter_signals['error'] = str(e)

        return counter_signals

    async def _find_opposing_trends(
        self,
        keyword: str,
        forecast_result: Dict[str, Any],
        db_session: AsyncSession
    ) -> List[Dict[str, Any]]:
        """
        Find related keywords that show opposing trends to the current bullish signal.
        """
        opposing_trends = []

        try:
            # Simple implementation: look for keywords with similar patterns but negative correlation
            # In a full implementation, this would use semantic similarity and correlation analysis

            from sqlalchemy import select, func
            from ..schema.models import TrendKeyword, TrendTimeSeries

            # Get recent trend data for the current keyword
            current_trend = forecast_result.get('metadata', {}).get('trend_direction', 'stable')

            if current_trend == 'increasing':
                # Look for related keywords that are decreasing
                # This is a simplified version - real implementation would use embeddings/clustering

                # For now, just return empty list as this requires more complex setup
                # In production, this would query for semantically related keywords
                pass

        except Exception as e:
            logger.error(f"Opposing trends analysis failed: {e}")

        return opposing_trends

    def _analyze_historical_failures(
        self,
        forecast_result: Dict[str, Any],
        time_series: List[TrendTimeSeries]
    ) -> List[Dict[str, Any]]:
        """
        Analyze historical cases where similar forecast signals led to failures.
        """
        failures = []

        try:
            if not time_series or len(time_series) < 48:  # Need at least 2 days
                return failures

            df = self._time_series_to_dataframe(time_series)
            series = df['interest_score']

            # Look for patterns where strong upward movement was followed by decline
            window_size = 24  # 24 hours
            failure_threshold = 0.2  # 20% decline after peak

            for i in range(window_size, len(series) - window_size):
                window = series.iloc[i-window_size:i+window_size]
                peak_idx = window.idxmax()
                peak_value = window.max()

                # Check if this was a significant peak
                if peak_value > series.mean() + series.std():
                    # Look ahead for decline
                    future_window = series.iloc[i:i+window_size]
                    if len(future_window) > 0:
                        min_future = future_window.min()
                        decline_pct = (peak_value - min_future) / peak_value

                        if decline_pct > failure_threshold:
                            failures.append({
                                'peak_time': peak_idx.isoformat(),
                                'peak_value': float(peak_value),
                                'decline_pct': float(decline_pct),
                                'time_to_decline': (future_window.idxmin() - peak_idx).total_seconds() / 3600
                            })

        except Exception as e:
            logger.error(f"Historical failures analysis failed: {e}")

        return failures

    def _analyze_momentum_exhaustion(
        self,
        time_series: List[TrendTimeSeries],
        forecast_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check for momentum exhaustion indicators that might signal trend reversal.
        """
        result = {
            'exhausted': False,
            'reason': '',
            'indicators': {}
        }

        try:
            if not time_series or len(time_series) < 24:
                return result

            df = self._time_series_to_dataframe(time_series)
            series = df['interest_score']

            # RSI-like indicator (simplified)
            def calculate_rsi(series, period=14):
                delta = series.diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
                rs = gain / loss
                return 100 - (100 / (1 + rs))

            rsi = calculate_rsi(series)
            current_rsi = rsi.iloc[-1] if not rsi.empty else 50

            # Check for overbought conditions
            if current_rsi > 70:
                result['exhausted'] = True
                result['reason'] = f"RSI indicates overbought conditions (RSI: {current_rsi:.1f})"
                result['indicators']['rsi'] = float(current_rsi)

            # Check for volume exhaustion (if available - simplified)
            # In real implementation, would check for declining volume during uptrend

            # Check for parabolic moves
            recent_trend = series.tail(24)
            if len(recent_trend) >= 12:
                slope = np.polyfit(range(len(recent_trend)), recent_trend.values, 1)[0]
                acceleration = np.polyfit(range(len(recent_trend)), recent_trend.values, 2)[0]

                if acceleration < -0.01:  # Decelerating upward move
                    result['exhausted'] = True
                    result['reason'] = "Parabolic upward move showing deceleration"
                    result['indicators']['acceleration'] = float(acceleration)

        except Exception as e:
            logger.error(f"Momentum exhaustion analysis failed: {e}")

        return result

    def _check_signal_persistence(
        self,
        time_series: List[TrendTimeSeries],
        forecast_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check if the current signal shows signs of persistence or is likely to decay quickly.
        """
        result = {
            'persistent': True,
            'reason': '',
            'half_life_estimate': None
        }

        try:
            if not time_series or len(time_series) < 24:
                return result

            df = self._time_series_to_dataframe(time_series)
            series = df['interest_score']

            # Analyze recent volatility
            recent_volatility = series.tail(24).std() / series.tail(24).mean()

            # Check for erratic behavior
            if recent_volatility > 0.3:  # High volatility
                result['persistent'] = False
                result['reason'] = f"High recent volatility ({recent_volatility:.2%}) suggests weak persistence"

            # Estimate half-life based on trend strength
            trend_direction = forecast_result.get('metadata', {}).get('trend_direction', 'stable')
            if trend_direction == 'increasing':
                # Simple exponential decay model
                recent_peak = series.tail(24).max()
                current_value = series.iloc[-1]
                decay_rate = (recent_peak - current_value) / recent_peak

                if decay_rate > 0.5:  # Already decayed significantly
                    result['persistent'] = False
                    result['reason'] = f"Signal already showing {decay_rate:.1%} decay from recent peak"
                    result['half_life_estimate'] = 12  # Hours
                else:
                    result['half_life_estimate'] = 48  # Assume longer persistence

        except Exception as e:
            logger.error(f"Signal persistence check failed: {e}")

        return result


class PredictionAccuracyTracker:
    """
    Track and analyze prediction accuracy over time.
    """

    def __init__(self):
        self.metrics = {}

    def record_prediction_accuracy(
        self,
        keyword: str,
        algorithm: str,
        actual_values: List[float],
        predicted_values: List[float]
    ) -> Dict[str, float]:
        """
        Record prediction accuracy metrics.

        Returns:
            Dictionary with accuracy metrics
        """
        if len(actual_values) != len(predicted_values):
            return {'error': 'Mismatched array lengths'}

        try:
            mae = mean_absolute_error(actual_values, predicted_values)
            mse = mean_squared_error(actual_values, predicted_values)
            rmse = np.sqrt(mse)

            # Mean Absolute Percentage Error
            mape = np.mean(np.abs((np.array(actual_values) - np.array(predicted_values)) / np.array(actual_values))) * 100

            metrics = {
                'mae': float(mae),
                'mse': float(mse),
                'rmse': float(rmse),
                'mape': float(mape),
                'accuracy_score': max(0, 100 - mape)  # Simple accuracy score
            }

            # Store metrics
            key = f"{keyword}_{algorithm}"
            if key not in self.metrics:
                self.metrics[key] = []
            self.metrics[key].append(metrics)

            return metrics

        except Exception as e:
            logger.error(f"Failed to calculate accuracy metrics: {e}")
            return {'error': str(e)}

    def get_algorithm_performance(self, algorithm: str) -> Dict[str, Any]:
        """Get performance statistics for an algorithm."""
        algorithm_metrics = [
            metrics for key, metric_list in self.metrics.items()
            for metrics in metric_list
            if key.endswith(f"_{algorithm}")
        ]

        if not algorithm_metrics:
            return {'error': 'No metrics available'}

        # Calculate averages
        avg_metrics = {}
        for key in algorithm_metrics[0].keys():
            if key != 'error':
                values = [m[key] for m in algorithm_metrics if key in m]
                avg_metrics[f'avg_{key}'] = np.mean(values) if values else 0

        return {
            'algorithm': algorithm,
            'total_predictions': len(algorithm_metrics),
            'average_metrics': avg_metrics
        }

    async def save_prediction_model(
        self,
        keyword: str,
        model_type: str,
        model_parameters: Dict[str, Any],
        training_results: Dict[str, Any],
        training_data_start: datetime,
        training_data_end: datetime,
        training_samples: int
    ) -> PredictionModel:
        """
        Save a trained prediction model to the database.

        Args:
            keyword: The keyword this model predicts
            model_type: Type of model (arima, exponential_smoothing, etc.)
            model_parameters: Model parameters and coefficients
            training_results: Training metrics and validation results
            training_data_start: Start of training data period
            training_data_end: End of training data period
            training_samples: Number of training samples

        Returns:
            The saved PredictionModel instance
        """
        if not self.db_session:
            raise ValueError("Database session required for saving models")

        # Get or create keyword record
        keyword_record = await self._get_or_create_keyword(keyword)

        # Create new model record
        model = PredictionModel(
            keyword_id=keyword_record.id,
            model_type=model_type,
            model_version='1.0',
            is_active=True,
            trained_at=datetime.now(timezone.utc),
            training_data_start=training_data_start,
            training_data_end=training_data_end,
            training_samples=training_samples,
            model_parameters=model_parameters,
            training_mae=training_results.get('validation_metrics', {}).get('mae'),
            training_rmse=training_results.get('validation_metrics', {}).get('rmse'),
            training_mape=training_results.get('validation_metrics', {}).get('mape'),
            validation_score=training_results.get('validation_metrics', {}).get('accuracy_score'),
            retrain_required=False
        )

        self.db_session.add(model)
        await self.db_session.commit()
        await self.db_session.refresh(model)

        logger.info(f"Saved prediction model: {model_type} for keyword '{keyword}' (ID: {model.id})")
        return model

    async def load_prediction_model(self, keyword: str, model_type: str = None) -> Optional[PredictionModel]:
        """
        Load the most recent active prediction model for a keyword.

        Args:
            keyword: The keyword to load model for
            model_type: Specific model type to load (optional)

        Returns:
            The PredictionModel instance or None if not found
        """
        if not self.db_session:
            return None

        from sqlalchemy import select, desc

        query = select(PredictionModel).join(TrendKeyword).where(
            TrendKeyword.keyword == keyword,
            PredictionModel.is_active == True
        )

        if model_type:
            query = query.where(PredictionModel.model_type == model_type)

        query = query.order_by(desc(PredictionModel.trained_at))

        result = await self.db_session.execute(query)
        model = result.scalar_one_or_none()

        if model:
            logger.info(f"Loaded prediction model: {model.model_type} for keyword '{keyword}' (ID: {model.id})")

        return model

    async def save_prediction_result(
        self,
        model_id: int,
        prediction_timestamp: datetime,
        horizon_hours: int,
        predicted_value: float,
        confidence_lower: Optional[float] = None,
        confidence_upper: Optional[float] = None
    ) -> PredictionResult:
        """
        Save a prediction result to the database.

        Args:
            model_id: ID of the model that made the prediction
            prediction_timestamp: When the prediction was made
            horizon_hours: Prediction horizon in hours
            predicted_value: The predicted value
            confidence_lower: Lower bound of confidence interval
            confidence_upper: Upper bound of confidence interval

        Returns:
            The saved PredictionResult instance
        """
        if not self.db_session:
            raise ValueError("Database session required for saving predictions")

        result = PredictionResult(
            model_id=model_id,
            prediction_timestamp=prediction_timestamp,
            horizon_hours=horizon_hours,
            predicted_value=predicted_value,
            confidence_lower=confidence_lower,
            confidence_upper=confidence_upper
        )

        self.db_session.add(result)
        await self.db_session.commit()
        await self.db_session.refresh(result)

        # Update model's prediction count and last prediction time
        await self._update_model_stats(model_id, prediction_timestamp)

        return result

    async def update_prediction_accuracy(
        self,
        prediction_result_id: int,
        actual_value: float,
        actual_timestamp: datetime
    ) -> None:
        """
        Update a prediction result with actual outcome data for accuracy tracking.

        Args:
            prediction_result_id: ID of the prediction result
            actual_value: The actual observed value
            actual_timestamp: When the actual value was observed
        """
        if not self.db_session:
            return

        from sqlalchemy import select, update

        # Get the prediction result
        query = select(PredictionResult).where(PredictionResult.id == prediction_result_id)
        result = await self.db_session.execute(query)
        prediction = result.scalar_one_or_none()

        if prediction:
            # Calculate prediction error
            prediction_error = abs(prediction.predicted_value - actual_value)
            prediction_accuracy = max(0, 100 - (prediction_error / max(actual_value, 1)) * 100)

            # Update the record
            update_stmt = (
                update(PredictionResult)
                .where(PredictionResult.id == prediction_result_id)
                .values(
                    actual_value=actual_value,
                    actual_timestamp=actual_timestamp,
                    prediction_error=prediction_error,
                    prediction_accuracy=prediction_accuracy
                )
            )
            await self.db_session.execute(update_stmt)
            await self.db_session.commit()

            logger.info(f"Updated prediction accuracy for result ID {prediction_result_id}: error={prediction_error:.2f}, accuracy={prediction_accuracy:.2f}%")

    async def get_model_performance_history(self, keyword: str, model_type: str = None, days: int = 30) -> Dict[str, Any]:
        """
        Get performance history for prediction models.

        Args:
            keyword: The keyword to get performance for
            model_type: Specific model type (optional)
            days: Number of days of history to include

        Returns:
            Dictionary with performance metrics and history
        """
        if not self.db_session:
            return {'error': 'Database session required'}

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        from sqlalchemy import select, func

        # Get models for the keyword
        query = select(PredictionModel).join(TrendKeyword).where(
            TrendKeyword.keyword == keyword,
            PredictionModel.trained_at >= cutoff_date
        )

        if model_type:
            query = query.where(PredictionModel.model_type == model_type)

        result = await self.db_session.execute(query)
        models = result.scalars().all()

        if not models:
            return {'error': 'No models found for the specified criteria'}

        performance_data = []

        for model in models:
            # Get prediction results for this model
            pred_query = select(PredictionResult).where(
                PredictionResult.model_id == model.id,
                PredictionResult.actual_value.isnot(None),
                PredictionResult.prediction_timestamp >= cutoff_date
            )

            pred_result = await self.db_session.execute(pred_query)
            predictions = pred_result.scalars().all()

            if predictions:
                avg_accuracy = sum(p.prediction_accuracy for p in predictions if p.prediction_accuracy) / len([p for p in predictions if p.prediction_accuracy])
                avg_error = sum(p.prediction_error for p in predictions if p.prediction_error) / len([p for p in predictions if p.prediction_error])

                performance_data.append({
                    'model_id': model.id,
                    'model_type': model.model_type,
                    'trained_at': model.trained_at.isoformat(),
                    'predictions_count': len(predictions),
                    'avg_accuracy': float(avg_accuracy) if avg_accuracy else None,
                    'avg_error': float(avg_error) if avg_error else None,
                    'training_mae': model.training_mae,
                    'training_mape': model.training_mape
                })

        return {
            'keyword': keyword,
            'model_type': model_type,
            'time_period_days': days,
            'models_performance': performance_data
        }

    async def _get_or_create_keyword(self, keyword: str, geo: str = 'US') -> TrendKeyword:
        """Get existing keyword record or create a new one."""
        from sqlalchemy import select

        query = select(TrendKeyword).where(
            TrendKeyword.keyword == keyword,
            TrendKeyword.geo == geo
        )

        result = await self.db_session.execute(query)
        keyword_record = result.scalar_one_or_none()

        if not keyword_record:
            keyword_record = TrendKeyword(
                keyword=keyword,
                geo=geo,
                is_active=True
            )
            self.db_session.add(keyword_record)
            await self.db_session.commit()
            await self.db_session.refresh(keyword_record)

        return keyword_record

    async def _update_model_stats(self, model_id: int, prediction_timestamp: datetime) -> None:
        """Update model's prediction count and last prediction timestamp."""
        from sqlalchemy import select, update

        # Get current model
        query = select(PredictionModel).where(PredictionModel.id == model_id)
        result = await self.db_session.execute(query)
        model = result.scalar_one_or_none()

        if model:
            update_stmt = (
                update(PredictionModel)
                .where(PredictionModel.id == model_id)
                .values(
                    prediction_count=model.prediction_count + 1,
                    last_prediction_at=prediction_timestamp
                )
            )
            await self.db_session.execute(update_stmt)
            await self.db_session.commit()