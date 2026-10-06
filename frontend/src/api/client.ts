/**
 * 门户侧的统一请求入口。
 *
 * 这段实现原先在 `Bills.vue:94-105` 与 `Dashboard.vue:87-98` 里各有一份，**逐字符相同**。
 * 抽出来之后，门户侧才和 TradeSim 侧有了同样的分层（TradeSim 侧是 `api/tradesim.ts`）。
 *
 * 行为与原实现**完全一致**，刻意不引入任何新特性：
 *   - 自动补 `/api` 前缀，调用方只传 `/bills/` 这样的相对路径；
 *   - 默认 `Content-Type: application/json`，可被 `init.headers` 覆盖；
 *   - 非 2xx 时先尝试解析后端的中文 `detail`，解析失败则退化成 `HTTP <status>`；
 *   - 204 返回 `null`（DELETE 会用到）；
 *   - 其余情况返回解析后的 JSON。
 *
 * ⚠ 泛型默认值是 `any`，这是**故意的、暂时的**：原先两个本地版本的返回类型就是隐式
 * `any`（`res.json()` 的结果），保持 `any` 才能做到"调用点一行都不用改"，从而让这次抽取
 * 可被证明是纯搬运。后续给具体调用点补上显式类型参数（如
 * `apiFetch<BillListResponse>('/bills/')`）才是收益所在，那是下一步的事。
 */
export const API_BASE = '/api'

export async function apiFetch<T = any>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    const detail = err.detail
    const message = typeof detail === 'string' ? detail
      : Array.isArray(detail) ? detail.map(issue => `${issue.loc?.slice(1).join('.') || '输入'}：${issue.msg}`).join('；')
      : `HTTP ${res.status}`
    throw new Error(message)
  }
  if (res.status === 204) return null as T
  return res.json()
}
