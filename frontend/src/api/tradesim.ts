import axios from 'axios'
import type {
  AiAnalysisRequest,
  RecordBrief,
  RecordDetail,
  SimulationRequest,
  SimulationResponse,
} from '@/types/tradesim'

export const TRADESIM_API_BASE = '/api/tradesim/v1'

const client = axios.create({
  baseURL: TRADESIM_API_BASE,
  headers: { 'Content-Type': 'application/json' },
})

export const tradesimApi = {
  listRecords() {
    return client.get<RecordBrief[]>('/records/list')
  },

  getRecord(recordId: string | number) {
    return client.get<RecordDetail>(`/records/detail/${recordId}`)
  },

  runSimulation(request: SimulationRequest) {
    return client.post<SimulationResponse>('/simulate/run', request)
  },

  saveFavorite(request: SimulationRequest, response: SimulationResponse) {
    return client.post('/records/save-favorite', { request, response })
  },

  analyzeStream(payload: AiAnalysisRequest) {
    return fetch(`${TRADESIM_API_BASE}/ai/analyze-stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).then(async (response) => {
      if (response.ok) return response

      const detail = await response.text().catch(() => '')
      throw new Error(detail || `AI 分析请求失败（HTTP ${response.status}）`)
    })
  },
}
