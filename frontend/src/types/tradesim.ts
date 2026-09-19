/**
 * TradeSim 的前后端数据契约。
 *
 * ⚠ 这个文件曾经反复出现同一个毛病：**声明得比现实更严格**。已知两次：
 *   1. `EquitySnapshot` 的三个较新字段对早期存档其实是缺失的（见下方 StoredEquitySnapshot）；
 *   2. 旧记录的 `close_price` / `benchmark_value` / `position_utilization` 同理。
 * 2026-09-20 的决策是**改类型、不动数据**（那两条老记录不删除），所以这里按后端
 * `app/tradesim/schemas/record.py` 的做法拆成"写路径严格 / 读路径宽容"两套。
 * 后端 OpenAPI 是判断依据，别凭印象改这里。
 */

export type TradeSimStrategyParams = Record<string, unknown>

export interface SimulationRequest {
  symbol: string
  start_date: string
  end_date: string
  data_frequency: string
  initial_capital: number
  commission_rate: number
  slippage: number
  strategy_name: string
  strategy_params: TradeSimStrategyParams
}

/** `POST /simulate/run` 刚算出来的净值点：这是我们自己引擎的产物，六个字段必然齐全。 */
export interface EquitySnapshot {
  date: string
  close_price: number
  net_value: number
  benchmark_value: number
  position_utilization: number
  drawdown: number
}

/**
 * `GET /records/detail/{id}` 里从 MongoDB 读回的**历史**净值点。
 *
 * `close_price` / `benchmark_value` / `position_utilization` 是后来才加进引擎的，早期存档
 * 里没有它们：实测 id=1（000400）的 242 个点、id=2（000400）的 2676 个点**全部缺失**，而
 * id=3~6（600585）六字段齐全。后端读路径用 `StoredEquitySnapshot` 把这三个字段放宽为可选
 * 并以 `null` 返回，这里必须一一对应——否则图表代码会以为自己拿到的一定是数字。
 *
 * 用 `Omit` 而不是手抄一遍，是为了将来 `EquitySnapshot` 新增字段时能自动继承过来。
 */
export interface StoredEquitySnapshot
  extends Omit<
    EquitySnapshot,
    'close_price' | 'benchmark_value' | 'position_utilization'
  > {
  close_price: number | null
  benchmark_value: number | null
  position_utilization: number | null
}

export interface TradeRecord {
  timestamp: string
  action: string
  price: number
  volume: number
  amount: number
  commission: number
  slippage_cost: number
}

/** `simulate/run` 返回的五个指标（含年化收益）。 */
export interface SimulationMetrics {
  total_return: number
  annualized_return: number
  max_drawdown: number
  win_rate: number
  total_trades: number
}

export interface SimulationResponse {
  metrics: SimulationMetrics
  equity_curve: EquitySnapshot[]
  execution_records: TradeRecord[]
}

/**
 * 列表页的轻对象。
 *
 * 注意这里**没有** `annualized_return`：MySQL 的 `simulation_records` 表存了它，
 * 但 `/records/list` 与 `/records/detail` 都没有把它暴露出来（后端 `RecordBriefResponse`
 * 里也没有）。补上它属于给接口新增字段，不在"整理"范围内。
 */
export interface RecordBrief {
  id: number
  symbol: string
  strategy_name: string
  total_return: number
  max_drawdown: number
  win_rate: number
  total_trades: number
  created_at: string
  data_frequency: string
}

export interface RecordDetail extends RecordBrief {
  start_date: string
  end_date: string
  strategy_params: TradeSimStrategyParams
  equity_curve: StoredEquitySnapshot[]
  execution_records: TradeRecord[]
}

export interface AiAnalysisRequest {
  symbol: string
  start_date: string
  end_date: string
  strategy_name: string
  strategy_params: TradeSimStrategyParams
  /**
   * 用 `Partial` 是因为后端**不要求**指标齐全：`AIAnalyzeRequest.metrics` 是
   * `Dict[str, Any]`，提示词里也一律以 `m.get(key, 0)` 取值。真实调用方
   * （`TradeSimDetail.vue`）就只送 4 个指标、不含 `annualized_return`，所以这里声明成
   * 必需五项是错的——那正是给该视图加 `lang="ts"` 时报 TS2741 的原因。
   */
  metrics: Partial<SimulationMetrics>
}
