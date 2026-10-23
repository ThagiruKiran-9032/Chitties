import uuid
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    user_name: Optional[str] = None
    action: str
    entity_type: str
    entity_id: uuid.UUID
    changes_json: Optional[Any] = None
    ip_address: Optional[str] = None
    timestamp: datetime
