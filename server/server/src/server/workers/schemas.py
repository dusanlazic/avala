from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, conlist, constr, field_validator


class WorkerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    alias: str
    dev_mode: bool
    last_seen: AwareDatetime
    ip: str
    registered_exploits: list[str]

    @field_validator("registered_exploits", mode="before")
    def split_registered_exploits(cls, v):
        if isinstance(v, str):
            return [e.strip() for e in v.split(",") if e.strip()]
        return v


class WorkerRegistrationRequest(BaseModel):
    alias: str = Field(...)
    dev_mode: bool = Field(default=False)
    registered_exploits: conlist(constr(pattern=r"^[a-zA-Z0-9_]+$")) = Field(default_factory=list)  # type: ignore
