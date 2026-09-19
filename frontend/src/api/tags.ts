/**
 * 标签接口（对应后端 `routers/tag.py`）。
 *
 * 只有两个查询：树形与扁平全量。**不要**再按 `?tag_type=` 逐类拉取——实测客户端分组的
 * 结果与服务端过滤**完全等价**（docs/5 §2.18），逐类拉取只会多花往返。
 */
import { apiFetch } from './client'
import type { TagOut } from '@/types/portal'

export const tagsApi = {
  /**
   * `GET /tags/` —— 树形：根标签带 `children`。
   *
   * ⚠ 返回的根标签**不只含 category**（还有 payment_platform / payment_channel /
   * fund_type），用之前请按 `type` 过滤。
   */
  tree() {
    return apiFetch<TagOut[]>('/tags/')
  },

  /**
   * `GET /tags/all` —— 全量成员列表（实测 39 条 = 25 个根 + 14 个小类）。
   *
   * 注意它**不是**纯扁平结构：category 项同样带 `children`。按 `type` 分组即可，无需
   * 逐类请求 `?tag_type=`。
   */
  all() {
    return apiFetch<TagOut[]>('/tags/all')
  },
}
