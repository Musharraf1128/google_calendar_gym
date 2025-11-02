"""
Gym Environment HTTP Bridge.

Provides HTTP endpoints for interacting with the Google Calendar Gym environment,
enabling remote agents to train and interact with the environment via REST API.
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
import tempfile
import os

from app.gym.google_calendar_env import GoogleCalendarEnv

router = APIRouter()

# Global environment instances (in production, use proper session management)
_environments: Dict[str, GoogleCalendarEnv] = {}


class ResetRequest(BaseModel):
    """Request model for environment reset."""

    seed: Optional[int] = Field(None, description="Random seed for reproducibility")
    env_id: Optional[str] = Field("default", description="Environment instance ID")


class ResetResponse(BaseModel):
    """Response model for environment reset."""

    observation: Dict[str, Any] = Field(..., description="Initial observation")
    env_id: str = Field(..., description="Environment instance ID")
    info: Dict[str, Any] = Field(default_factory=dict, description="Additional info")


class StepRequest(BaseModel):
    """Request model for environment step."""

    env_id: Optional[str] = Field("default", description="Environment instance ID")
    action: Dict[str, Any] = Field(..., description="Action to execute")


class StepResponse(BaseModel):
    """Response model for environment step."""

    observation: Dict[str, Any] = Field(..., description="New observation")
    reward: float = Field(..., description="Reward received")
    done: bool = Field(..., description="Whether episode is done")
    info: Dict[str, Any] = Field(..., description="Additional info")


class EnvironmentInfo(BaseModel):
    """Information about the environment."""

    observation_space: Dict[str, Any]
    action_space: Dict[str, Any]
    max_steps: int
    description: str


class RenderResponse(BaseModel):
    """Response model for environment rendering."""

    render: str = Field(..., description="String representation of environment state")
    observation: Dict[str, Any] = Field(..., description="Current observation")


def _get_or_create_env(env_id: str) -> GoogleCalendarEnv:
    """
    Get or create an environment instance.

    Args:
        env_id: Environment instance ID

    Returns:
        GoogleCalendarEnv instance
    """
    if env_id not in _environments:
        # Create a temporary database file for this environment
        db_fd, db_path = tempfile.mkstemp(suffix=".db", prefix=f"gym_env_{env_id}_")
        os.close(db_fd)
        _environments[env_id] = GoogleCalendarEnv(db_path=db_path)

    return _environments[env_id]


@router.post("/gym/reset", response_model=ResetResponse)
async def reset_environment(request: ResetRequest):
    """
    Reset the Gym environment to initial state.

    This endpoint creates or resets an environment instance and returns
    the initial observation. Use this to start a new episode.

    Args:
        request: Reset request with optional seed and env_id

    Returns:
        Initial observation and environment info

    Example:
        POST /gym/reset
        {
            "seed": 42,
            "env_id": "agent_1"
        }
    """
    env_id = request.env_id or "default"

    try:
        env = _get_or_create_env(env_id)
        observation = env.reset(seed=request.seed)

        return ResetResponse(
            observation=observation,
            env_id=env_id,
            info={"step": 0, "episode_reward": 0.0, "max_steps": env.max_steps},
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error resetting environment: {str(e)}",
        )


@router.post("/gym/step", response_model=StepResponse)
async def step_environment(request: StepRequest):
    """
    Execute an action in the Gym environment.

    This endpoint executes an action and returns the resulting observation,
    reward, done flag, and additional info.

    Args:
        request: Step request with action and env_id

    Returns:
        Observation, reward, done, and info

    Example:
        POST /gym/step
        {
            "env_id": "agent_1",
            "action": {
                "type": "create_event",
                "params": {
                    "organizer_email": "alice@example.com",
                    "calendar_id": "uuid-here",
                    "summary": "Team Meeting",
                    "start_offset_hours": 2,
                    "duration_hours": 1,
                    "attendees": ["bob@example.com"]
                }
            }
        }
    """
    env_id = request.env_id or "default"

    if env_id not in _environments:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Environment '{env_id}' not found. Call /gym/reset first.",
        )

    try:
        env = _environments[env_id]
        observation, reward, done, info = env.step(request.action)

        return StepResponse(
            observation=observation, reward=reward, done=done, info=info
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing step: {str(e)}",
        )


@router.get("/gym/info", response_model=EnvironmentInfo)
async def get_environment_info():
    """
    Get information about the Gym environment.

    Returns:
        Environment metadata including observation/action spaces

    Example:
        GET /gym/info
    """
    # Create a temporary environment to get metadata
    temp_env = GoogleCalendarEnv()

    info = EnvironmentInfo(
        observation_space=temp_env.observation_space,
        action_space=temp_env.action_space,
        max_steps=temp_env.max_steps,
        description="Google Calendar Gym Environment for RL agents",
    )

    temp_env.close()

    return info


@router.get("/gym/render/{env_id}", response_model=RenderResponse)
async def render_environment(env_id: str = "default"):
    """
    Render the current state of the environment.

    Args:
        env_id: Environment instance ID

    Returns:
        String representation and current observation

    Example:
        GET /gym/render/agent_1
    """
    if env_id not in _environments:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Environment '{env_id}' not found. Call /gym/reset first.",
        )

    env = _environments[env_id]

    render_output = env.render(mode="ansi")
    observation = env._get_observation()

    return RenderResponse(render=render_output, observation=observation)


@router.delete("/gym/close/{env_id}")
async def close_environment(env_id: str):
    """
    Close and cleanup an environment instance.

    Args:
        env_id: Environment instance ID

    Returns:
        Success message

    Example:
        DELETE /gym/close/agent_1
    """
    if env_id not in _environments:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Environment '{env_id}' not found",
        )

    env = _environments[env_id]
    env.close()
    del _environments[env_id]

    return {"message": f"Environment '{env_id}' closed successfully"}


@router.get("/gym/list")
async def list_environments():
    """
    List all active environment instances.

    Returns:
        List of environment IDs and their states

    Example:
        GET /gym/list
    """
    env_list = []

    for env_id, env in _environments.items():
        obs = env._get_observation()
        env_list.append(
            {
                "env_id": env_id,
                "step": env.step_count,
                "max_steps": env.max_steps,
                "episode_reward": env.episode_reward,
                "num_events": len(obs["events"]),
                "num_users": len(obs["users"]),
                "num_calendars": len(obs["calendars"]),
            }
        )

    return {"environments": env_list}
