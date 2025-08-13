from pydantic import BaseModel
from typing import Optional, List

class Priority(BaseModel):
    priority_id: str
    name: str
    description: str
    owner: str
    status: str

class Objective(BaseModel):
    objective_id: str
    type: str
    name: str
    description: str
    status: str
    progress: float
    target_date: str
    created_at: str

class KPI(BaseModel):
    kpi_id: str
    name: str
    category: str
    measure: str
    baseline: float
    target: float
    actual: float
    status: str
    unit: str

class Risk(BaseModel):
    risk_id: str
    name: str
    category: str
    treatments: List[str]
    impact: str
    rating: int
    status: str

class Strategy(BaseModel):
    strategy_id: str
    name: str
    type: str
    focus_area: str
    description: str

class Project(BaseModel):
    project_id: str
    name: str
    description: str
    status: str
    start_date: str
    end_date: str
    progress: float
    budget: float
    owner: str

class BU(BaseModel):
    bu_id: str
    name: str
    type: str
    level: int
    head: str

class Budget(BaseModel):
    budget_id: str
    planned: float
    actual: float
    gap: float
    fy: str
    project_id: str
    currency: str

class Output(BaseModel):
    output_id: str
    name: str
    description: str
    value: float
    status: str

class Benchmark(BaseModel):
    benchmark_id: str
    kpi_id: str
    standard: float
    comparison_result: str