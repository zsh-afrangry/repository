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

export interface EquitySnapshot {
  date: string
  close_price: number
  net_value: number
  benchmark_value: number
  position_utilization: number
  drawdown: number
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
  equity_curve: EquitySnapshot[]
  execution_records: TradeRecord[]
}

export interface AiAnalysisRequest {
  symbol: string
  start_date: string
  end_date: string
  strategy_name: string
  strategy_params: TradeSimStrategyParams
  metrics: SimulationMetrics
}
