from __future__ import annotations

import logging
import os
from threading import Lock

logger = logging.getLogger(__name__)
_PROXY_LOCK = Lock()

# 标准化后的统一列名 —— 策略层（grid_trade / base）直接依赖这几个名字。
_REQUIRED_COLUMNS = ["日期", "开盘", "收盘", "最高", "最低"]

# 不同数据源返回的列名不一致：东财日线用中文，新浪 / 腾讯用英文，分钟源用 day / 时间。
_COLUMN_ALIASES = {
    "日期": "日期", "date": "日期", "day": "日期", "时间": "日期",
    "开盘": "开盘", "open": "开盘",
    "收盘": "收盘", "close": "收盘",
    "最高": "最高", "high": "最高",
    "最低": "最低", "low": "最低",
}


def _to_prefixed_symbol(symbol: str) -> str:
    """把裸 6 位代码补成带交易所前缀的形式（新浪 / 腾讯源需要，如 000400 -> sz000400）。"""
    code = symbol.strip().lower()
    if code.startswith(("sh", "sz", "bj")):
        return code
    if code.startswith(("5", "6", "9")):        # 沪市 A 股 / 基金
        return f"sh{code}"
    if code.startswith(("4", "8")):             # 北交所
        return f"bj{code}"
    return f"sz{code}"                          # 深市 0 / 3 开头


class DataFetcher:
    """
    负责从外部数据源（如 AkShare）获取金融数据，
    并将其标准化清洗为统一的 Polars DataFrame 格式，供后端策略引擎极速处理。
    """

    @staticmethod
    def _normalize(df_ak) -> "pl.DataFrame | None":
        """把任意数据源返回的 pandas DataFrame 规整成标准 Polars 表。"""
        import polars as pl

        if df_ak is None or df_ak.empty:
            return None

        # 逐列改名，且**不覆盖已存在的目标列**：东财分钟源同时带 "时间"，某些源也带
        # "日期"，若把 "时间" 一律改名为 "日期" 会造出两个同名列并让 pl.from_pandas 失败。
        rename_map: dict[str, str] = {}
        taken = set(df_ak.columns)
        for col in df_ak.columns:
            target = _COLUMN_ALIASES.get(col)
            if target and target != col and target not in taken:
                rename_map[col] = target
                taken.add(target)
        df_ak = df_ak.rename(columns=rename_map)
        missing_cols = [c for c in _REQUIRED_COLUMNS if c not in df_ak.columns]
        if missing_cols:
            logger.error(f"数据源返回的列不完整，缺失: {missing_cols}")
            return None

        df_pl = pl.from_pandas(df_ak)
        # 日期列统一成 "YYYY-MM-DD" 字符串。东财源本来就是字符串，新浪 / 腾讯源返回的是
        # date / datetime 对象；策略层按字符串写进净值曲线，这里抹平差异以保持落库格式一致。
        df_pl = df_pl.with_columns(pl.col("日期").cast(pl.Utf8).str.slice(0, 10))
        return df_pl.select(_REQUIRED_COLUMNS)

    @staticmethod
    def _fetch_daily(ak, symbol: str, start_date: str, end_date: str, adjust: str):
        """按可靠性依次尝试多个数据源，返回 (pandas.DataFrame, 源名)。

        东财源字段最全，但它的 push2his 主机在部分网络环境下会被远端直接断开连接
        （requests 抛 RemoteDisconnected），且与代理开关无关。因此保留新浪 / 腾讯
        两个源作为降级路径，保证回测不至于因为单一数据源被墙而整体不可用。
        """
        code = symbol.strip()
        prefixed = _to_prefixed_symbol(symbol)
        ak_start = start_date.replace("-", "")
        ak_end = end_date.replace("-", "")

        attempts = (
            ("东财", lambda: ak.stock_zh_a_hist(
                symbol=code, period="daily",
                start_date=ak_start, end_date=ak_end, adjust=adjust)),
            ("新浪", lambda: ak.stock_zh_a_daily(
                symbol=prefixed,
                start_date=ak_start, end_date=ak_end, adjust=adjust)),
            ("腾讯", lambda: ak.stock_zh_a_hist_tx(
                symbol=prefixed,
                start_date=ak_start, end_date=ak_end, adjust=adjust)),
        )

        for name, call in attempts:
            try:
                df = call()
            except Exception as exc:
                logger.warning(f"[{name}] 源获取 [{symbol}] 失败，降级到下一个数据源: {exc}")
                continue
            if df is None or df.empty:
                logger.warning(f"[{name}] 源未返回 [{symbol}] 的数据，降级到下一个数据源。")
                continue
            logger.info(f"[{name}] 源返回 {len(df)} 行原始数据。")
            return df, name

        logger.error(f"全部数据源均无法获取 [{symbol}] 在 {start_date}--{end_date} 的日线数据。")
        return None, None

    @staticmethod
    def _clip_to_range(df, start_date: str, end_date: str):
        """把返回的数据按 [start_date, end_date] 裁剪（含两端）。

        为什么必须有这一步：**新浪的分钟接口不接受日期区间**，它只返回最近约 1970 根
        的固定窗口。若不裁剪，用户请求 2024 年的区间会拿到 2026 年的数据并"成功"跑出
        一份看起来正常、实际完全错位的回测——这比直接报错危险得多。
        """
        if df is None or df.empty:
            return df

        for col in ("day", "时间", "日期", "date"):
            if col in df.columns:
                # 取前 10 位是为了同时兼容 "2026-09-18 14:55:00"、datetime 对象和
                # "2026-09-18" 三种形态，与 _normalize 的口径保持一致。
                stamps = df[col].astype(str).str.slice(0, 10)
                return df[(stamps >= start_date) & (stamps <= end_date)]

        # 找不到时间列就原样返回，交给 _normalize 报"列不完整"，避免在这里静默吞掉。
        return df

    @staticmethod
    def _fetch_intraday(ak, symbol: str, start_date: str, end_date: str,
                        frequency: str, adjust: str):
        """按可靠性依次尝试多个分钟级数据源，返回 (pandas.DataFrame, 源名)。

        与日线同样的降级思路：东财的 K 线主机在部分网络环境下会被远端直接断开
        （见 _fetch_daily 的说明），所以分钟级也不能只挂一条路径，否则前端
        `data_frequency` 选 1min/5min 会直接失败。
        """
        prefixed = _to_prefixed_symbol(symbol)
        period = frequency.replace("min", "")           # "1min" -> "1"，"5min" -> "5"
        ak_start = f"{start_date} 09:30:00"
        ak_end = f"{end_date} 15:00:00"

        # 第二个元素表示"该源是否会自己按区间过滤"：东财会，新浪不会（需本地裁剪）。
        attempts = (
            ("东财", False, lambda: ak.stock_zh_a_hist_min_em(
                symbol=symbol.strip(), start_date=ak_start, end_date=ak_end,
                period=period, adjust=adjust)),
            ("新浪", True, lambda: ak.stock_zh_a_minute(
                symbol=prefixed, period=period, adjust=adjust)),
        )

        for name, needs_clip, call in attempts:
            try:
                df = call()
            except Exception as exc:
                logger.warning(
                    f"[{name}] 源获取 [{symbol}] 的 {frequency} 数据失败，降级到下一个数据源: {exc}"
                )
                continue
            if df is None or df.empty:
                logger.warning(f"[{name}] 源未返回 [{symbol}] 的 {frequency} 数据，降级到下一个数据源。")
                continue

            if needs_clip:
                before = len(df)
                df = DataFetcher._clip_to_range(df, start_date, end_date)
                logger.info(f"[{name}] 源返回 {before} 行，按区间裁剪后剩 {len(df)} 行。")
                if df is None or df.empty:
                    logger.warning(
                        f"[{name}] 源的数据不在 {start_date}--{end_date} 区间内"
                        f"（该源只提供最近一段固定窗口），降级到下一个数据源。"
                    )
                    continue

            logger.info(f"[{name}] 源返回 {len(df)} 行分钟级数据。")
            return df, name

        logger.error(
            f"全部数据源均无法获取 [{symbol}] 在 {start_date}--{end_date} 的 {frequency} 数据。"
        )
        return None, None

    @staticmethod
    def fetch_a_share_data(symbol: str, start_date: str, end_date: str, frequency: str = "daily", adjust: str = "qfq") -> pl.DataFrame | None:
        """
        根据指定频率 (daily/5min/1min) 获取 A 股历史数据并转换为标准化的 Polars DataFrame。
        """
        logger.info(f"正在通过 AkShare 获取 [{symbol}] 的 [{frequency}] 级别数据 ({start_date} -- {end_date})...")

        try:
            # 这里的 import 同时充当依赖门禁：缺包时给出可操作的提示而不是堆栈。
            import akshare as ak
            import polars as pl  # noqa: F401
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "TradeSim 行情依赖未安装，请安装 backend/requirements.txt 中的 akshare、polars 和相关依赖。"
            ) from exc

        # AkShare reads proxy environment variables globally.  Serialize this
        # small critical section so concurrent portal requests cannot race while
        # one request temporarily removes the proxy variables.
        with _PROXY_LOCK:
            _proxy_keys = ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy")
            _saved_proxies = {k: os.environ.pop(k, None) for k in _proxy_keys}

            try:
                if frequency == "daily":
                    df_ak, source_name = DataFetcher._fetch_daily(
                        ak, symbol, start_date, end_date, adjust
                    )
                    if df_ak is None:
                        return None
                    logger.info(f"日线数据命中数据源: {source_name}")
                elif frequency in ("1min", "5min"):
                    # 分钟级改为与日线一致的降级链（东财 → 新浪）。原先这里只有东财一条
                    # 路径，而东财的 K 线主机在本机不可用，等于前端 data_frequency 一选
                    # 1min/5min 就必然失败。
                    df_ak, source_name = DataFetcher._fetch_intraday(
                        ak, symbol, start_date, end_date, frequency, adjust
                    )
                    if df_ak is None:
                        return None
                    logger.info(f"分钟级数据命中数据源: {source_name}")
                else:
                    logger.error(f"不支持的 frequency 参数: {frequency}")
                    return None

                if df_ak.empty:
                    logger.warning(f"数据源返回为空：未能找到股票 '{symbol}' 在此区间的数据。")
                    return None

                df_pl = DataFetcher._normalize(df_ak)
                if df_pl is None or df_pl.is_empty():
                    return None

                logger.info(f"成功获取并转换数据: 共 {df_pl.height} 行。")
                return df_pl

            except Exception as e:
                logger.error(f"获取股票 [{symbol}] 数据时发生异常: {str(e)}", exc_info=True)
                return None
            finally:
                for k, v in _saved_proxies.items():
                    if v is not None:
                        os.environ[k] = v
