from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from app.tradesim.schemas.simulate import (
    EquitySnapshot,
    SimulationRequest,
    SimulationResponse,
    TradeRecord,
)


class SaveRecordRequest(BaseModel):
    """
    保存记录时的入参。
    它巧妙地包含了当初用户调用的配置参数（request）以及我们算出来的结果参数（response）。
    将两块打包发给后端进行 MySQL 和 MongoDB 存证。
    """
    request: SimulationRequest
    response: SimulationResponse


class RecordBriefResponse(BaseModel):
    """返回给前端的列表页轻数据对象 (不用渲染曲线图)

    注意这里**没有** `annualized_return`：`simulation_records` 表里存了它、`simulate/run`
    也会返回它，但列表与详情这两个读接口都没有把它暴露出去（`RecordDetailResponse` 继承本
    类，所以同样没有）。前端 `types/tradesim.ts` 却声明了它 —— 属于"声明比现实更严格"。
    补上它等于**给接口新增字段**，不在本次"整理"范围内，已记录在 历史记录兼容约定。
    """
    id: int
    symbol: str
    strategy_name: str
    total_return: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    created_at: str
    data_frequency: str = "daily"

    class Config:
        from_attributes = True  # 允许读取 SQLAlchemy 对象属性


class StoredEquitySnapshot(EquitySnapshot):
    """
    从 MongoDB 读回的**历史**净值点（读路径专用）。

    为什么不能直接用 `EquitySnapshot`：`close_price` / `benchmark_value` /
    `position_utilization` 是后来才加进引擎的三个字段，而**早期存档里没有它们**。实测：

    | 记录            | 净值点数   | 缺这三个字段的点数 |
    |-----------------|-----------|------------------|
    | id=1（000400）  | 242       | **242（全部）**   |
    | id=2（000400）  | 2676      | **2676（全部）**  |
    | id=3~6（600585）| 2431~2652 | 0                |

    读路径若也用严格模型，那两条老记录的详情页会直接抛 `ResponseValidationError` 变成
    500 —— 而它们**不允许删除**（2026-09-20 的决策是"宁可放宽读路径的类型，也不动数据"）。

    ⚠ 副作用（已记录在 历史记录兼容约定）：对 id=1/id=2 来说，响应里会**多出这三个键且值为
    `null`**（此前是键根本不存在）。前端以 `p.close_price` 取用时 `null` 与 `undefined`
    表现一致（都是假值），ECharts 也把两者同样当作空点，因此不会画坏图表；但这是响应体的
    **实际变化**，值得知道。

    写路径 `simulate/run` 继续使用严格的 `EquitySnapshot`：那是我们自己刚算出来的，必须齐全
    —— 不放宽写路径，"引擎漏算了某个字段"这类问题才能继续暴露出来。
    """
    close_price: Optional[float] = None
    benchmark_value: Optional[float] = None
    position_utilization: Optional[float] = None


class RecordDetailResponse(RecordBriefResponse):
    """
    返回给详情页的全量数据结构
    继承了 Brief 中的所有指标，外加 MongoDB 中的深层数组
    """
    start_date: str
    end_date: str
    strategy_params: Dict[str, Any]

    # 以下是从 MongoDB 取回的。
    # `execution_records` 用的是**严格**的 TradeRecord：实测 6 条记录的成交明细全部齐备
    # timestamp / action / price / volume / amount / commission / slippage_cost 这 7 个
    # 字段，没有任何一条缺项，所以这里不需要放宽（与 equity_curve 的情况不同）。
    equity_curve: List[StoredEquitySnapshot]
    execution_records: List[TradeRecord]
