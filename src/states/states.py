from typing import Any
from enum import StrEnum

from pydantic import BaseModel
from pydantic.fields import Field


class STATES_NAMES(StrEnum):
    UNDEFINED = "UNDEFINED"
    HAVE_PROFILE = "HAVE_PROFILE"
    NO_PROFILE = "NO_PROFILE"
    PING_ON = "PING_ON"
    PING_OFF = "PING_OFF"
    SELECT_DISTRICT = "SELECT_DISTRICT"
    SELECT_LPU = "SELECT_LPU"
    SELECT_SPECIALTY = "SELECT_SPECIALTY"
    SELECT_DOCTOR = "SELECT_DOCTOR"


class MiState(BaseModel):
    name: STATES_NAMES
    payload: dict[str, Any] = Field(default_factory=dict)


class StateManager:
    USERS_STATE: dict[int, MiState] = {}

    @classmethod
    def get_state(cls, user_id: int):
        return cls.USERS_STATE.get(
            user_id,
            MiState(name=STATES_NAMES.UNDEFINED),
        )

    @classmethod
    def set_state(
        cls,
        user_id: int,
        state_name: STATES_NAMES,
        payload: dict[str, Any] | None = None,
    ):
        if payload is None:
            cls.USERS_STATE[user_id] = MiState(name=state_name)
        else:
            cls.USERS_STATE[user_id] = MiState(name=state_name, payload=payload)
