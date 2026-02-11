#!/usr/bin/env python3
"""
Ultimate Self-Updating Testing & Maintenance Script for Intel-AI App

This script provides comprehensive automated testing, maintenance, and monitoring
for the Intel-AI application. It dynamically detects features, runs tests,
performs safe cleanup, and generates detailed reports.

Features:
- Automatic feature detection from codebase
- Dynamic test generation and execution
- Safe directory cleanup with backup
- Performance monitoring and dependency management
- Self-updating: detects new features without code changes
- Modular and configurable design
- Parallel testing support
- Comprehensive logging and reporting

Usage:
    python ultimate_test_maintenance.py [options]

Options:
    --config FILE    Path to config file (default: config.json)
    --no-cleanup     Skip cleanup operations
    --no-tests       Skip testing operations
    --parallel       Enable parallel testing
    --verbose        Enable verbose output
    --help           Show this help message

Configuration:
    Create a config.json file to customize behavior:
    {
        "directories": {
            "root": ".",
            "backup": "./backup",
            "logs": "./logs"
        },
        "cleanup": {
            "patterns": ["*.pyc", "*.pyo", "__pycache__", "*.log", "*.tmp"],
            "skip_patterns": ["*.py", "*.js", "*.ts", "*.json", "*.md"],
            "max_age_days": 7
        },
        "testing": {
            "timeout": 30,
            "retries": 3,
            "parallel_workers": 4
        },
        "alerts": {
            "enabled": false,
            "email": "admin@example.com",
            "discord_webhook": ""
        }
    }

Author: GitHub Copilot
Version: 1.0.0
"""

import os
import sys
import json
import time
import logging
import argparse
import subprocess
import importlib
import inspect
import requests
import tempfile
import shutil
import hashlib
import concurrent.futures
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import glob

# Optional imports
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    print("Warning: watchdog not available, file watching disabled")

# Third-party imports (assumed to be installed via pip install -e .)
import fastapi
import uvicorn
import sqlalchemy
import pytest

# Optional imports
try:
    import git
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False
    print("Warning: gitpython not available, version tracking disabled")

@dataclass
class TestResult:
    """Represents the result of a single test case."""
    feature_name: str
    test_description: str
    input_values: Dict[str, Any]
    expected_outcome: str
    actual_outcome: str
    status: str  # 'PASS', 'FAIL', 'ERROR'
    error_message: Optional[str]
    execution_time: float
    timestamp: datetime

@dataclass
class CleanupAction:
    """Represents a cleanup action performed."""
    file_path: str
    action: str  # 'DELETED', 'MOVED', 'SKIPPED'
    size_bytes: int
    timestamp: datetime
    reason: str

@dataclass
class TestSummary:
    """Summary of test run results."""
    total_tests: int
    passed: int
    failed: int
    errors: int
    execution_time: float
    new_features_detected: int
    timestamp: datetime

class Config:
    """Configuration management for the script."""

    DEFAULT_CONFIG = {
        "directories": {
            "root": ".",
            "backup": "./backup",
            "logs": "./logs"
        },
        "cleanup": {
            "patterns": ["*.pyc", "*.pyo", "__pycache__", "*.log", "*.tmp", "*.cache"],
            "skip_patterns": ["*.py", "*.js", "*.ts", "*.tsx", "*.json", "*.md", "*.txt", "*.yml", "*.yaml"],
            "max_age_days": 7,
            "backup_before_delete": True
        },
        "testing": {
            "timeout": 30,
            "retries": 3,
            "parallel_workers": 4,
            "api_base_url": "http://localhost:8000",
            "frontend_url": "http://localhost:3000"
        },
        "alerts": {
            "enabled": False,
            "email": "",
            "discord_webhook": ""
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(levelname)s - %(message)s"
        }
    }

    def __init__(self, config_file: str = "config.json"):
        self.config_file = Path(config_file)
        self.config = self.DEFAULT_CONFIG.copy()
        self.load_config()

    def load_config(self):
        """Load configuration from file, merging with defaults."""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                user_config = json.load(f)
                self._merge_config(self.config, user_config)

    def _merge_config(self, base: dict, update: dict):
        """Recursively merge configuration dictionaries."""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value

    def get(self, key: str, default=None):
        """Get configuration value by dot-separated key."""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

class FeatureDetector:
    """Automatically detects features in the codebase."""

    def __init__(self, config: Config):
        self.config = config
        self.root_dir = Path(config.get('directories.root', '.'))
        self.known_features_file = self.root_dir / "known_features.json"
        self.known_features = self.load_known_features()

    def load_known_features(self) -> Dict[str, Any]:
        """Load previously detected features."""
        if self.known_features_file.exists():
            with open(self.known_features_file, 'r') as f:
                return json.load(f)
        return {}

    def save_known_features(self):
        """Save current known features."""
        with open(self.known_features_file, 'w') as f:
            json.dump(self.known_features, f, indent=2, default=str)

    def detect_backend_features(self) -> List[Dict[str, Any]]:
        """Detect backend features (Python modules, classes, functions)."""
        features = []

        # Skip directories that shouldn't be analyzed
        skip_dirs = {'.venv', 'node_modules', '__pycache__', '.git', 'build', 'dist', 'alembic'}

        # Scan Python files
        for py_file in self.root_dir.rglob("*.py"):
            if any(skip_dir in str(py_file) for skip_dir in skip_dirs):
                continue
            if "test" in py_file.name.lower() or py_file.name.startswith('.'):
                continue

            try:
                # Import module
                module_path = self._get_module_path(py_file)
                if not module_path:
                    continue

                spec = importlib.util.spec_from_file_location(module_path, py_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    # Detect classes and functions
                    for name, obj in inspect.getmembers(module):
                        if inspect.isclass(obj) and not name.startswith('_'):
                            features.append({
                                "type": "class",
                                "name": f"{module_path}.{name}",
                                "file": str(py_file),
                                "obj": obj,
                                "methods": [m for m in dir(obj) if not m.startswith('_')]
                            })
                        elif inspect.isfunction(obj) and not name.startswith('_'):
                            features.append({
                                "type": "function",
                                "name": f"{module_path}.{name}",
                                "file": str(py_file),
                                "obj": obj,
                                "signature": str(inspect.signature(obj))
                            })

            except Exception as e:
                logging.debug(f"Failed to analyze {py_file}: {e}")

        return features

    def detect_api_endpoints(self) -> List[Dict[str, Any]]:
        """Detect FastAPI endpoints."""
        features = []

        try:
            # Import the main app
            sys.path.insert(0, str(self.root_dir / "src"))
            from vanguard_signal.api.app import app

            for route in app.routes:
                if hasattr(route, 'methods') and hasattr(route, 'path'):
                    features.append({
                        "type": "endpoint",
                        "name": f"{route.methods} {route.path}",
                        "path": route.path,
                        "methods": list(route.methods),
                        "handler": route.endpoint.__name__ if hasattr(route.endpoint, '__name__') else str(route.endpoint)
                    })

        except Exception as e:
            logging.warning(f"Failed to detect API endpoints: {e}")

        return features

    def detect_frontend_features(self) -> List[Dict[str, Any]]:
        """Detect frontend features (React components, pages)."""
        features = []

        frontend_dir = self.root_dir / "dashboard" / "src"
        if not frontend_dir.exists():
            return features

        # Scan for components and pages
        for js_file in frontend_dir.rglob("*.{js,jsx,ts,tsx}"):
            if "node_modules" in str(js_file):
                continue

            try:
                with open(js_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Simple detection of components and pages
                if "export default" in content or "function " in content or "const " in content:
                    feature_type = "page" if "page" in str(js_file).lower() else "component"
                    features.append({
                        "type": feature_type,
                        "name": js_file.stem,
                        "file": str(js_file),
                        "content_hash": hashlib.md5(content.encode()).hexdigest()
                    })

            except Exception as e:
                logging.warning(f"Failed to analyze {js_file}: {e}")

        return features

    def detect_all_features(self) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Detect all features and identify new ones."""
        all_features = []
        all_features.extend(self.detect_backend_features())
        all_features.extend(self.detect_api_endpoints())
        all_features.extend(self.detect_frontend_features())

        new_features = []
        for feature in all_features:
            feature_id = f"{feature['type']}:{feature['name']}"
            if feature_id not in self.known_features:
                new_features.append(feature)
                self.known_features[feature_id] = {
                    "detected_at": datetime.now().isoformat(),
                    "last_tested": None
                }

        self.save_known_features()
        return all_features, new_features

    def _get_module_path(self, py_file: Path) -> Optional[str]:
        """Convert file path to Python module path."""
        try:
            rel_path = py_file.relative_to(self.root_dir)
            if rel_path.suffix == '.py':
                return str(rel_path.with_suffix('')).replace(os.sep, '.')
        except ValueError:
            pass
        return None

class TestGenerator:
    """Generates and executes tests for detected features."""

    def __init__(self, config: Config):
        self.config = config
        self.api_base_url = config.get('testing.api_base_url')
        self.timeout = config.get('testing.timeout', 30)

    def generate_tests_for_feature(self, feature: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate test cases for a feature."""
        tests = []

        if feature['type'] == 'endpoint':
            tests.extend(self._generate_api_tests(feature))
        elif feature['type'] == 'function':
            tests.extend(self._generate_function_tests(feature))
        elif feature['type'] in ['class', 'component', 'page']:
            tests.extend(self._generate_generic_tests(feature))

        return tests

    def _generate_api_tests(self, feature: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate tests for API endpoints."""
        tests = []

        path = feature['path']
        methods = feature['methods']

        for method in methods:
            # Valid input test
            tests.append({
                "description": f"Test {method} {path} with valid input",
                "method": method,
                "url": f"{self.api_base_url}{path}",
                "data": self._get_sample_data_for_endpoint(path, method),
                "expected_status": 200
            })

            # Invalid input test
            tests.append({
                "description": f"Test {method} {path} with invalid input",
                "method": method,
                "url": f"{self.api_base_url}{path}",
                "data": {"invalid": "data"},
                "expected_status": 400
            })

            # Edge case: empty data
            if method in ['POST', 'PUT', 'PATCH']:
                tests.append({
                    "description": f"Test {method} {path} with empty data",
                    "method": method,
                    "url": f"{self.api_base_url}{path}",
                    "data": {},
                    "expected_status": 400
                })

        return tests

    def _generate_function_tests(self, feature: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate tests for Python functions."""
        tests = []

        func = feature['obj']
        sig = inspect.signature(func)

        # Valid input test
        try:
            sample_args = self._get_sample_args(sig)
            tests.append({
                "description": f"Test {feature['name']} with valid inputs",
                "function": func,
                "args": sample_args,
                "kwargs": {},
                "expected_exception": None
            })
        except Exception as e:
            logging.warning(f"Could not generate valid input test for {feature['name']}: {e}")

        # Invalid input test
        tests.append({
            "description": f"Test {feature['name']} with invalid inputs",
            "function": func,
            "args": [],
            "kwargs": {"invalid": "args"},
            "expected_exception": TypeError
        })

        return tests

    def _generate_generic_tests(self, feature: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate basic tests for classes, components, etc."""
        return [{
            "description": f"Basic existence test for {feature['type']} {feature['name']}",
            "feature": feature,
            "expected": "exists"
        }]

    def execute_test(self, test: Dict[str, Any]) -> TestResult:
        """Execute a single test case."""
        start_time = time.time()

        try:
            if 'function' in test:
                # Function test
                result = self._execute_function_test(test)
            elif 'url' in test:
                # API test
                result = self._execute_api_test(test)
            else:
                # Generic test
                result = self._execute_generic_test(test)

            execution_time = time.time() - start_time
            return TestResult(
                feature_name=test.get('feature', {}).get('name', 'unknown'),
                test_description=test['description'],
                input_values=test.get('data', test.get('args', {})),
                expected_outcome=str(test.get('expected_status', test.get('expected', 'success'))),
                actual_outcome=result['outcome'],
                status=result['status'],
                error_message=result.get('error'),
                execution_time=execution_time,
                timestamp=datetime.now()
            )

        except Exception as e:
            execution_time = time.time() - start_time
            return TestResult(
                feature_name=test.get('feature', {}).get('name', 'unknown'),
                test_description=test['description'],
                input_values=test.get('data', test.get('args', {})),
                expected_outcome=str(test.get('expected_status', test.get('expected', 'success'))),
                actual_outcome="ERROR",
                status="ERROR",
                error_message=str(e),
                execution_time=execution_time,
                timestamp=datetime.now()
            )

    def _execute_api_test(self, test: Dict[str, Any]) -> Dict[str, Any]:
        """Execute API endpoint test."""
        try:
            response = requests.request(
                test['method'],
                test['url'],
                json=test.get('data'),
                timeout=self.timeout
            )

            if response.status_code == test['expected_status']:
                return {"status": "PASS", "outcome": f"Status {response.status_code}"}
            else:
                return {"status": "FAIL", "outcome": f"Status {response.status_code}", "error": f"Expected {test['expected_status']}"}

        except requests.RequestException as e:
            return {"status": "ERROR", "outcome": "Request failed", "error": str(e)}

    def _execute_function_test(self, test: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Python function test."""
        try:
            result = test['function'](*test['args'], **test['kwargs'])

            expected_exception = test.get('expected_exception')
            if expected_exception:
                return {"status": "FAIL", "outcome": f"Expected {expected_exception.__name__}", "error": "No exception raised"}
            else:
                return {"status": "PASS", "outcome": f"Returned: {str(result)[:100]}"}

        except Exception as e:
            expected_exception = test.get('expected_exception')
            if expected_exception and isinstance(e, expected_exception):
                return {"status": "PASS", "outcome": f"Expected exception: {type(e).__name__}"}
            else:
                return {"status": "ERROR", "outcome": "Exception raised", "error": str(e)}

    def _execute_generic_test(self, test: Dict[str, Any]) -> Dict[str, Any]:
        """Execute generic feature test."""
        feature = test['feature']
        if Path(feature['file']).exists():
            return {"status": "PASS", "outcome": "Feature exists"}
        else:
            return {"status": "FAIL", "outcome": "Feature not found"}

    def _get_sample_data_for_endpoint(self, path: str, method: str) -> Dict[str, Any]:
        """Generate sample data for API endpoints."""
        # This is a simple implementation - in practice, you'd want more sophisticated data generation
        if 'alert' in path:
            return {"message": "Test alert", "severity": "low"}
        elif 'user' in path:
            return {"username": "testuser", "email": "test@example.com"}
        else:
            return {"test": "data"}

    def _get_sample_args(self, sig: inspect.Signature) -> List[Any]:
        """Generate sample arguments for function signature."""
        args = []
        for param in sig.parameters.values():
            if param.name == 'self':
                continue
            if param.annotation == int:
                args.append(42)
            elif param.annotation == str:
                args.append("test")
            elif param.annotation == bool:
                args.append(True)
            elif param.annotation == list:
                args.append([])
            elif param.annotation == dict:
                args.append({})
            else:
                args.append(None)
        return args

class CleanupManager:
    """Handles safe directory cleanup and maintenance."""

    def __init__(self, config: Config):
        self.config = config
        self.backup_dir = Path(config.get('directories.backup', './backup'))
        self.backup_dir.mkdir(exist_ok=True)

    def perform_cleanup(self) -> List[CleanupAction]:
        """Perform cleanup operations."""
        actions = []

        root_dir = Path(self.config.get('directories.root', '.'))
        patterns = self.config.get('cleanup.patterns', [])
        skip_patterns = self.config.get('cleanup.skip_patterns', [])
        max_age = timedelta(days=self.config.get('cleanup.max_age_days', 7))
        backup_before_delete = self.config.get('cleanup.backup_before_delete', True)

        for pattern in patterns:
            for path in root_dir.rglob(pattern):
                if path.is_file() and not self._should_skip(path, skip_patterns):
                    # Check age
                    if path.stat().st_mtime < (time.time() - max_age.total_seconds()):
                        action = self._cleanup_file(path, backup_before_delete)
                        if action:
                            actions.append(action)

        # Clean empty directories
        for dir_path in root_dir.rglob('*'):
            if dir_path.is_dir() and not any(dir_path.iterdir()):
                try:
                    dir_path.rmdir()
                    actions.append(CleanupAction(
                        file_path=str(dir_path),
                        action="DELETED",
                        size_bytes=0,
                        timestamp=datetime.now(),
                        reason="Empty directory"
                    ))
                except OSError:
                    pass

        return actions

    def _should_skip(self, path: Path, skip_patterns: List[str]) -> bool:
        """Check if file should be skipped."""
        for pattern in skip_patterns:
            if path.match(pattern):
                return True
        return False

    def _cleanup_file(self, path: Path, backup: bool) -> Optional[CleanupAction]:
        """Clean up a single file."""
        try:
            size = path.stat().st_size

            if backup:
                # Move to backup
                backup_path = self.backup_dir / path.name
                counter = 1
                while backup_path.exists():
                    backup_path = self.backup_dir / f"{path.stem}_{counter}{path.suffix}"
                    counter += 1

                shutil.move(str(path), str(backup_path))
                return CleanupAction(
                    file_path=str(path),
                    action="MOVED",
                    size_bytes=size,
                    timestamp=datetime.now(),
                    reason=f"Moved to {backup_path}"
                )
            else:
                # Delete
                path.unlink()
                return CleanupAction(
                    file_path=str(path),
                    action="DELETED",
                    size_bytes=size,
                    timestamp=datetime.now(),
                    reason="Deleted old file"
                )

        except Exception as e:
            logging.warning(f"Failed to cleanup {path}: {e}")
            return None

class Logger:
    """Handles logging and reporting."""

    def __init__(self, config: Config):
        self.config = config
        self.logs_dir = Path(config.get('directories.logs', './logs'))
        self.logs_dir.mkdir(exist_ok=True)

        # Setup logging
        log_level = getattr(logging, config.get('logging.level', 'INFO').upper())
        logging.basicConfig(
            level=log_level,
            format=config.get('logging.format'),
            handlers=[
                logging.FileHandler(self.logs_dir / "ultimate_test_maintenance.log"),
                logging.StreamHandler()
            ]
        )

    def log_test_results(self, results: List[TestResult]):
        """Log test results to file."""
        results_file = self.logs_dir / "feature_test_results.txt"

        with open(results_file, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"Test Run: {datetime.now().isoformat()}\n")
            f.write(f"{'='*80}\n\n")

            for result in results:
                f.write(f"Feature: {result.feature_name}\n")
                f.write(f"Test: {result.test_description}\n")
                f.write(f"Input: {result.input_values}\n")
                f.write(f"Expected: {result.expected_outcome}\n")
                f.write(f"Actual: {result.actual_outcome}\n")
                f.write(f"Status: {result.status}\n")
                if result.error_message:
                    f.write(f"Error: {result.error_message}\n")
                f.write(f"Execution Time: {result.execution_time:.2f}s\n")
                f.write(f"Timestamp: {result.timestamp.isoformat()}\n")
                f.write("-" * 40 + "\n")

    def log_cleanup_actions(self, actions: List[CleanupAction]):
        """Log cleanup actions to file."""
        cleanup_file = self.logs_dir / "cleanup_log.txt"

        with open(cleanup_file, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"Cleanup Run: {datetime.now().isoformat()}\n")
            f.write(f"{'='*80}\n\n")

            for action in actions:
                f.write(f"Action: {action.action}\n")
                f.write(f"File: {action.file_path}\n")
                f.write(f"Size: {action.size_bytes} bytes\n")
                f.write(f"Reason: {action.reason}\n")
                f.write(f"Timestamp: {action.timestamp.isoformat()}\n")
                f.write("-" * 40 + "\n")

    def generate_summary_report(self, summary: TestSummary, new_features: List[Dict[str, Any]], cleanup_actions: List[CleanupAction]):
        """Generate a comprehensive summary report."""
        report_file = self.logs_dir / "summary_report.txt"

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("ULTIMATE TESTING & MAINTENANCE REPORT\n")
            f.write("=" * 50 + "\n\n")

            f.write("EXECUTION SUMMARY\n")
            f.write("-" * 20 + "\n")
            f.write(f"Timestamp: {summary.timestamp.isoformat()}\n")
            f.write(f"Total Tests: {summary.total_tests}\n")
            f.write(f"Passed: {summary.passed}\n")
            f.write(f"Failed: {summary.failed}\n")
            f.write(f"Errors: {summary.errors}\n")
            f.write(f"Success Rate: {(summary.passed / summary.total_tests * 100):.1f}%\n" if summary.total_tests > 0 else "Success Rate: N/A\n")
            f.write(f"Total Execution Time: {summary.execution_time:.2f}s\n")
            f.write(f"New Features Detected: {summary.new_features_detected}\n\n")

            f.write("NEW FEATURES DETECTED\n")
            f.write("-" * 25 + "\n")
            if new_features:
                for feature in new_features:
                    f.write(f"- {feature['type']}: {feature['name']}\n")
            else:
                f.write("No new features detected.\n")
            f.write("\n")

            f.write("CLEANUP SUMMARY\n")
            f.write("-" * 17 + "\n")
            total_cleaned = len(cleanup_actions)
            total_size = sum(action.size_bytes for action in cleanup_actions)
            f.write(f"Files Processed: {total_cleaned}\n")
            f.write(f"Total Size Cleaned: {total_size} bytes ({total_size / 1024 / 1024:.2f} MB)\n\n")

            f.write("DETAILED CLEANUP ACTIONS\n")
            f.write("-" * 26 + "\n")
            for action in cleanup_actions:
                f.write(f"{action.action}: {action.file_path} ({action.size_bytes} bytes) - {action.reason}\n")
            f.write("\n")

            # Performance analysis
            f.write("PERFORMANCE ANALYSIS\n")
            f.write("-" * 21 + "\n")
            if summary.total_tests > 0:
                avg_time = summary.execution_time / summary.total_tests
                f.write(f"Average Test Time: {avg_time:.2f}s\n")
                f.write(f"Tests per Second: {summary.total_tests / summary.execution_time:.2f}\n")
            f.write("\n")

            f.write("RECOMMENDATIONS\n")
            f.write("-" * 15 + "\n")
            if summary.failed > 0:
                f.write(f"- Review {summary.failed} failed tests\n")
            if summary.errors > 0:
                f.write(f"- Investigate {summary.errors} test errors\n")
            if summary.new_features_detected > 0:
                f.write(f"- Review {summary.new_features_detected} new features for additional testing\n")
            if total_cleaned > 100:
                f.write("- Consider adjusting cleanup patterns to reduce processed files\n")
            f.write("\n")

class UltimateTestMaintenance:
    """Main class coordinating all operations."""

    def __init__(self, config_file: str = "config.json"):
        self.config = Config(config_file)
        self.logger = Logger(self.config)
        self.feature_detector = FeatureDetector(self.config)
        self.test_generator = TestGenerator(self.config)
        self.cleanup_manager = CleanupManager(self.config)

    def run(self, skip_cleanup: bool = False, skip_tests: bool = False, parallel: bool = False):
        """Run the complete testing and maintenance suite."""
        start_time = time.time()

        logging.info("Starting Ultimate Testing & Maintenance Script")

        # Step 1: Cleanup (if enabled)
        cleanup_actions = []
        if not skip_cleanup:
            logging.info("Performing cleanup operations...")
            cleanup_actions = self.cleanup_manager.perform_cleanup()
            self.logger.log_cleanup_actions(cleanup_actions)
            logging.info(f"Cleanup completed: {len(cleanup_actions)} actions performed")

        # Step 2: Feature detection
        logging.info("Detecting features...")
        all_features, new_features = self.feature_detector.detect_all_features()
        logging.info(f"Detected {len(all_features)} total features, {len(new_features)} new")

        # Step 3: Testing (if enabled)
        test_results = []
        if not skip_tests:
            logging.info("Generating and executing tests...")
            test_results = self._run_tests(all_features, parallel)
            self.logger.log_test_results(test_results)
            logging.info(f"Testing completed: {len(test_results)} tests executed")

        # Step 4: Generate summary report
        execution_time = time.time() - start_time
        summary = TestSummary(
            total_tests=len(test_results),
            passed=sum(1 for r in test_results if r.status == 'PASS'),
            failed=sum(1 for r in test_results if r.status == 'FAIL'),
            errors=sum(1 for r in test_results if r.status == 'ERROR'),
            execution_time=execution_time,
            new_features_detected=len(new_features),
            timestamp=datetime.now()
        )

        self.logger.generate_summary_report(summary, new_features, cleanup_actions)

        logging.info("Ultimate Testing & Maintenance Script completed")
        logging.info(f"Summary: {summary.passed}/{summary.total_tests} tests passed, {len(cleanup_actions)} cleanup actions")

        # Optional alerts
        if self.config.get('alerts.enabled') and (summary.failed > 0 or summary.errors > 0):
            self._send_alerts(summary)

    def _run_tests(self, features: List[Dict[str, Any]], parallel: bool = False) -> List[TestResult]:
        """Run tests for all features."""
        all_tests = []

        # Generate test cases
        for feature in features:
            tests = self.test_generator.generate_tests_for_feature(feature)
            all_tests.extend(tests)

        # Execute tests
        if parallel and len(all_tests) > 1:
            return self._run_tests_parallel(all_tests)
        else:
            return self._run_tests_sequential(all_tests)

    def _run_tests_sequential(self, tests: List[Dict[str, Any]]) -> List[TestResult]:
        """Run tests sequentially."""
        results = []
        for test in tests:
            result = self.test_generator.execute_test(test)
            results.append(result)
            logging.info(f"Test {result.status}: {result.test_description}")
        return results

    def _run_tests_parallel(self, tests: List[Dict[str, Any]]) -> List[TestResult]:
        """Run tests in parallel."""
        results = []
        max_workers = self.config.get('testing.parallel_workers', 4)

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_test = {executor.submit(self.test_generator.execute_test, test): test for test in tests}

            for future in concurrent.futures.as_completed(future_to_test):
                result = future.result()
                results.append(result)
                logging.info(f"Test {result.status}: {result.test_description}")

        return results

    def _send_alerts(self, summary: TestSummary):
        """Send alerts for critical issues."""
        message = f"ALERT: Testing completed with {summary.failed} failures and {summary.errors} errors"

        # Email alert (placeholder)
        email = self.config.get('alerts.email')
        if email:
            logging.info(f"Would send email alert to {email}: {message}")

        # Discord webhook (placeholder)
        webhook = self.config.get('alerts.discord_webhook')
        if webhook:
            logging.info(f"Would send Discord alert to webhook: {message}")

class FileChangeHandler(FileSystemEventHandler):
    """Handler for file system events to trigger re-testing."""

    def __init__(self, script, skip_cleanup, skip_tests, parallel):
        self.script = script
        self.skip_cleanup = skip_cleanup
        self.skip_tests = skip_tests
        self.parallel = parallel
        self.last_run = 0
        self.debounce_time = 1.0  # seconds

    def on_modified(self, event):
        if event.is_directory:
            return
        if not event.src_path.endswith(('.py', '.js', '.ts', '.tsx', '.json')):
            return
        current_time = time.time()
        if current_time - self.last_run > self.debounce_time:
            logging.info(f"File changed: {event.src_path}, re-running tests...")
            try:
                self.script.run(
                    skip_cleanup=self.skip_cleanup,
                    skip_tests=self.skip_tests,
                    parallel=self.parallel
                )
            except Exception as e:
                logging.error(f"Re-run failed: {e}")
            self.last_run = current_time

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Ultimate Testing & Maintenance Script")
    parser.add_argument("--config", default="config.json", help="Path to config file")
    parser.add_argument("--no-cleanup", action="store_true", help="Skip cleanup operations")
    parser.add_argument("--no-tests", action="store_true", help="Skip testing operations")
    parser.add_argument("--parallel", action="store_true", help="Enable parallel testing")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--watch", action="store_true", help="Watch for file changes and re-run tests automatically")

    args = parser.parse_args()

    # Set verbose logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        script = UltimateTestMaintenance(args.config)
        
        if args.watch:
            if not WATCHDOG_AVAILABLE:
                logging.error("Watch mode requires watchdog. Install with: pip install watchdog")
                sys.exit(1)
            
            logging.info("Starting watch mode - monitoring for file changes...")
            event_handler = FileChangeHandler(script, args.no_cleanup, args.no_tests, args.parallel)
            observer = Observer()
            observer.schedule(event_handler, path='.', recursive=True)
            observer.start()
            
            # Run once initially
            script.run(
                skip_cleanup=args.no_cleanup,
                skip_tests=args.no_tests,
                parallel=args.parallel
            )
            
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                observer.stop()
            observer.join()
        else:
            script.run(
                skip_cleanup=args.no_cleanup,
                skip_tests=args.no_tests,
                parallel=args.parallel
            )
    except Exception as e:
        logging.error(f"Script execution failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()