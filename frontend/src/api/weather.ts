/** 天气接口（对应后端 `routers/weather.py`，后端代理 QWeather）。 */
import { apiFetch } from './client'
import type { WeatherInfo, WeatherLocation } from '@/types/portal'

export const weatherApi = {
  /**
   * `GET /weather/` —— 真实网络调用，依赖后端配置的 API key。
   * `locationId` 省略时后端用自己的默认城市（广州天河）。
   */
  current(locationId?: string) {
    const query = locationId ? `?location=${encodeURIComponent(locationId)}` : ''
    return apiFetch<WeatherInfo>(`/weather/${query}`)
  },
  /**
   * `GET /weather/locations?q=` —— 城市搜索，返回 QWeather 的 Location ID 与经纬度。
   * 每次调用会消耗后端配额（含一次 geo 查询），因此调用方应做去抖并只在用户明确搜索时触发。
   */
  searchLocations(q: string) {
    return apiFetch<{ query: string; locations: WeatherLocation[] }>(
      `/weather/locations?q=${encodeURIComponent(q)}`,
    )
  },
}
