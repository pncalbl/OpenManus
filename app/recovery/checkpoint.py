"""
Checkpoint and rollback mechanism for state recovery.
"""

import copy
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.logger import logger
from app.schema import Memory


class Checkpoint:
    """Represents a saved state checkpoint."""

    def __init__(
        self,
        checkpoint_id: str,
        timestamp: datetime,
        state: Dict[str, Any],
        memory_snapshot: Optional[Memory] = None,
        description: Optional[str] = None,
    ):
        self.checkpoint_id = checkpoint_id
        self.timestamp = timestamp
        self.state = state
        self.memory_snapshot = memory_snapshot
        self.description = description or "Auto-saved checkpoint"

    def to_dict(self) -> Dict:
        """Convert checkpoint to dictionary for serialization."""
        return {
            "checkpoint_id": self.checkpoint_id,
            "timestamp": self.timestamp.isoformat(),
            "state": self.state,
            "description": self.description,
            "has_memory": self.memory_snapshot is not None,
        }


class CheckpointManager:
    """Manage checkpoints for state recovery."""

    def __init__(self, storage_dir: Optional[Path] = None, max_checkpoints: int = 10):
        """
        Initialize checkpoint manager.

        Args:
            storage_dir: Directory to store checkpoints
            max_checkpoints: Maximum number of checkpoints to keep
        """
        self.storage_dir = storage_dir or Path("workspace/checkpoints")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.max_checkpoints = max_checkpoints
        self.checkpoints: List[Checkpoint] = []

    def save_checkpoint(
        self,
        state: Dict[str, Any],
        memory: Optional[Memory] = None,
        description: Optional[str] = None,
    ) -> str:
        """
        Save a checkpoint.

        Args:
            state: State dictionary to save
            memory: Optional memory snapshot
            description: Optional description

        Returns:
            Checkpoint ID
        """
        checkpoint_id = self._generate_checkpoint_id()

        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            timestamp=datetime.now(),
            state=copy.deepcopy(state),
            memory_snapshot=copy.deepcopy(memory) if memory else None,
            description=description,
        )

        # Save to disk
        self._save_to_disk(checkpoint)

        # Add to in-memory list
        self.checkpoints.append(checkpoint)

        # Cleanup old checkpoints if exceeded max
        self._cleanup_old_checkpoints()

        logger.info(f"Checkpoint saved: {checkpoint_id}")
        return checkpoint_id

    def restore_checkpoint(
        self, checkpoint_id: str
    ) -> Tuple[Dict[str, Any], Optional[Memory]]:
        """
        Restore a checkpoint.

        Args:
            checkpoint_id: ID of checkpoint to restore

        Returns:
            Tuple of (state, memory)

        Raises:
            ValueError if checkpoint not found
        """
        checkpoint = self._find_checkpoint(checkpoint_id)

        if not checkpoint:
            raise ValueError(f"Checkpoint not found: {checkpoint_id}")

        logger.info(f"Restored checkpoint: {checkpoint_id}")
        return checkpoint.state, checkpoint.memory_snapshot

    def list_checkpoints(self) -> List[Dict]:
        """
        List all checkpoints.

        Returns:
            List of checkpoint info dictionaries
        """
        return [cp.to_dict() for cp in sorted(self.checkpoints, key=lambda x: x.timestamp, reverse=True)]

    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """
        Delete a specific checkpoint.

        Args:
            checkpoint_id: ID of checkpoint to delete

        Returns:
            True if deleted successfully
        """
        checkpoint = self._find_checkpoint(checkpoint_id)

        if not checkpoint:
            return False

        # Remove from disk
        checkpoint_file = self.storage_dir / f"{checkpoint_id}.json"
        if checkpoint_file.exists():
            checkpoint_file.unlink()

        # Remove from memory
        self.checkpoints = [cp for cp in self.checkpoints if cp.checkpoint_id != checkpoint_id]

        logger.info(f"Checkpoint deleted: {checkpoint_id}")
        return True

    def get_latest_checkpoint(self) -> Optional[Checkpoint]:
        """Get the most recent checkpoint."""
        if not self.checkpoints:
            return None
        return max(self.checkpoints, key=lambda x: x.timestamp)

    def rollback_to_latest(self) -> Tuple[Dict[str, Any], Optional[Memory]]:
        """
        Rollback to the latest checkpoint.

        Returns:
            Tuple of (state, memory)

        Raises:
            ValueError if no checkpoints available
        """
        latest = self.get_latest_checkpoint()

        if not latest:
            raise ValueError("No checkpoints available for rollback")

        return self.restore_checkpoint(latest.checkpoint_id)

    def _generate_checkpoint_id(self) -> str:
        """Generate a unique checkpoint ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        short_uuid = uuid.uuid4().hex[:8]
        return f"checkpoint_{timestamp}_{short_uuid}"

    def _find_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """Find a checkpoint by ID."""
        for cp in self.checkpoints:
            if cp.checkpoint_id == checkpoint_id:
                return cp
        return None

    def _save_to_disk(self, checkpoint: Checkpoint):
        """Save checkpoint to disk."""
        file_path = self.storage_dir / f"{checkpoint.checkpoint_id}.json"

        checkpoint_data = checkpoint.to_dict()

        # Save memory separately if present
        if checkpoint.memory_snapshot:
            memory_data = [msg.to_dict() for msg in checkpoint.memory_snapshot.messages]
            checkpoint_data["memory_messages"] = memory_data

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)

    def _cleanup_old_checkpoints(self):
        """Remove old checkpoints if exceeded max count."""
        if len(self.checkpoints) <= self.max_checkpoints:
            return

        # Sort by timestamp
        sorted_checkpoints = sorted(self.checkpoints, key=lambda x: x.timestamp)

        # Keep only the newest max_checkpoints
        to_remove = sorted_checkpoints[: -self.max_checkpoints]

        for checkpoint in to_remove:
            self.delete_checkpoint(checkpoint.checkpoint_id)
