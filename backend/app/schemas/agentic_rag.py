from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class AgentStep(BaseModel):
    step_index: int
    action: str
    thought: str
    query: Optional[str] = None
    retrieved_chunk_ids: List[str] = []
    evaluation_score: Optional[float] = None
    latency_ms: int

class AgenticRAGResult(BaseModel):
    agent_enabled: bool
    total_steps: int
    steps: List[AgentStep]
    reasoning_path: str
    merged_context_chunks_count: int
    loop_prevented: bool
    metadata: Dict[str, Any] = {}
