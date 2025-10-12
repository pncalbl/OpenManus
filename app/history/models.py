"""
Data models for conversation history.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SessionMetadata(BaseModel):
    """Metadata for a conversation session."""

    session_id: str = Field(..., description="Unique session identifier")
    created_at: datetime = Field(..., description="Session creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    agent_name: str = Field(..., description="Name of the agent")
    agent_type: str = Field(..., description="Type of agent (e.g., Manus, MCPAgent)")
    message_count: int = Field(0, description="Number of messages in session")
    task_summary: Optional[str] = Field(None, description="Brief summary of the task")
    workspace_path: Optional[str] = Field(None, description="Workspace path at session time")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class SessionData(BaseModel):
    """Complete session data for serialization."""

    metadata: SessionMetadata
    messages: list  # List of Message dicts

    class Config:
        arbitrary_types_allowed = True
