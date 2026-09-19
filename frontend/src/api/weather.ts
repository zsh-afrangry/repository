/** 天气接口（对应后端 `routers/weather.py`，后端代理 QWeather）。 */
import { apiFetch } from './client'
import type { WeatherInfo } from '@/types/portal'

export const weatherApi = {
  /** `GET /weather/` —— 真实网络调用，依赖后端配置的 API key。 */
  current() {
    return apiFetch<WeatherInfo>('/weather/')
  },
}
