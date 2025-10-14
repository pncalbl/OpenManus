"""
Tests for ProgressTracker

Basic unit tests for the progress tracking functionality.
"""

import time
from datetime import datetime

import pytest

from app.progress import ProgressTracker, get_event_bus, reset_event_bus


class TestProgressTracker:
    """Test ProgressTracker functionality"""

    def setup_method(self):
        """Reset event bus before each test"""
        reset_event_bus()

    def test_basic_initialization(self):
        """Test basic tracker initialization"""
        tracker = ProgressTracker(
            total_steps=10,
            description="Test task",
        )

        assert tracker.total_steps == 10
        assert tracker.current_step == 0
        assert tracker.description == "Test task"
        assert tracker.is_running is True
        assert tracker.is_completed is False
        assert tracker.is_failed is False

    def test_progress_update(self):
        """Test progress updates"""
        tracker = ProgressTracker(total_steps=5)

        tracker.update(message="Step 1")
        assert tracker.current_step == 1

        tracker.update(message="Step 2")
        assert tracker.current_step == 2

        tracker.update(step=4, message="Jump to step 4")
        assert tracker.current_step == 4

    def test_percentage_calculation(self):
        """Test percentage calculation"""
        tracker = ProgressTracker(total_steps=10)

        assert tracker.percentage == 0.0

        tracker.update()
        assert tracker.percentage == 10.0

        tracker.update(step=5)
        assert tracker.percentage == 50.0

        tracker.update(step=10)
        assert tracker.percentage == 100.0

    def test_completion(self):
        """Test task completion"""
        tracker = ProgressTracker(total_steps=3)

        tracker.update()
        tracker.update()
        tracker.complete(message="Done")

        assert tracker.is_completed is True
        assert tracker.is_running is False
        assert tracker.current_step == 3
        assert tracker.last_message == "Done"

    def test_failure(self):
        """Test task failure"""
        tracker = ProgressTracker(total_steps=5)

        tracker.update()
        error = Exception("Test error")
        tracker.fail(error, message="Failed")

        assert tracker.is_failed is True
        assert tracker.is_running is False
        assert tracker.last_message == "Failed"

    def test_duration_tracking(self):
        """Test duration tracking"""
        tracker = ProgressTracker(total_steps=2)

        time.sleep(0.1)
        tracker.update()

        assert tracker.duration > 0.1

    def test_eta_calculation(self):
        """Test ETA calculation"""
        tracker = ProgressTracker(total_steps=4)

        # First step
        tracker.update()
        time.sleep(0.1)

        # Second step
        tracker.update()
        eta = tracker.eta

        # ETA should be calculated
        assert eta is not None
        assert eta > 0

    def test_subtask_creation(self):
        """Test subtask creation"""
        parent = ProgressTracker(total_steps=3, description="Parent task")

        subtask = parent.start_subtask("Subtask 1", total_steps=2)

        assert subtask.parent == parent
        assert subtask in parent.children
        assert subtask.description == "Subtask 1"
        assert subtask.total_steps == 2

    def test_context_manager_success(self):
        """Test context manager with successful completion"""
        with ProgressTracker(total_steps=3, description="Test") as tracker:
            tracker.update()
            tracker.update()

        assert tracker.is_completed is True

    def test_context_manager_failure(self):
        """Test context manager with exception"""
        try:
            with ProgressTracker(total_steps=3) as tracker:
                tracker.update()
                raise ValueError("Test error")
        except ValueError:
            pass

        assert tracker.is_failed is True

    def test_progress_info(self):
        """Test getting progress info"""
        tracker = ProgressTracker(
            total_steps=5,
            description="Test task",
        )
        tracker.update(message="Working", metadata={"key": "value"})

        info = tracker.get_progress_info()

        assert info["description"] == "Test task"
        assert info["current_step"] == 1
        assert info["total_steps"] == 5
        assert info["percentage"] == 20.0
        assert info["is_running"] is True
        assert info["metadata"]["key"] == "value"

    def test_set_total_steps(self):
        """Test dynamically setting total steps"""
        tracker = ProgressTracker(description="Dynamic task")

        assert tracker.total_steps is None

        tracker.set_total_steps(10)
        assert tracker.total_steps == 10

        tracker.update(step=5)
        assert tracker.percentage == 50.0

    def test_step_events(self):
        """Test step start and complete events"""
        tracker = ProgressTracker(total_steps=2)

        tracker.start_step("Step 1")
        tracker.complete_step("Step 1", result="Success")

        # Should not raise any errors
        assert True

    def test_intermediate_result(self):
        """Test showing intermediate results"""
        tracker = ProgressTracker(total_steps=2)

        tracker.show_intermediate_result(
            title="Result",
            content="Test content",
            category="result"
        )

        # Should not raise any errors
        assert True

    def test_message(self):
        """Test sending messages"""
        tracker = ProgressTracker(total_steps=2)

        tracker.message("Info message", level="info")
        tracker.message("Warning message", level="warning")
        tracker.message("Error message", level="error")

        # Should not raise any errors
        assert True
