from typing import List
import tabulate
from decimal import Decimal

from prompt_toolkit.formatted_text import to_formatted_text

from hummingbot.strategy.script_strategy_base import ScriptStrategyBase
from hummingbot.data_feed.candles_feed.candles_factory import CandlesFactory, CandlesConfig

import pandas as pd
from hummingbot.client.ui.interface_utils import format_df_for_printout


class Dev(ScriptStrategyBase):
    # current available paper trader exchanges
    markets = {
        # "binance_paper_trade": {"ETH-USDT", "BTC-USDT"},
        # "kucoin_paper_trade": {"ETH-USDT", "BTC-USDT"},
        # "kraken_paper_trade": {"ETH-USDT", "BTC-USDT"},
        "gate_io_paper_trade": {"ETH-USDT", "BTC-USDT"},
    }
    # markets = {
    #     "binance": {"ETH-USDT", "BTC-USDT"},
    # }

    # Candles params
    candle_exchange = "binance"
    candles_interval = "1m"
    trading_pair = "ETH-USDT"
    candles_length = 30
    max_records = 1000

    # Initializes candles
    candles = CandlesFactory.get_candle(CandlesConfig(connector=candle_exchange,
                                                      trading_pair=trading_pair,
                                                      interval=candles_interval,
                                                      max_records=max_records))

    def format_status(self) -> str:
        """
        Returns status of the current strategy on user balances and current active orders. This function is called
        when status command is issued. Override this function to create custom status display output.
        """
        if not self.ready_to_trade:
            return "Market connectors are not ready."
        lines = []

        # balance lines
        balance_df = self.get_balance_df()
        # lines.extend(["", "  Balances:"] + ["\t" + line for line in balance_df.to_string(index=False).split("\n")])
        lines.extend(["", "  Balances:"] + [format_df_for_printout(balance_df, table_format="grid")])

        market_status_df = self.get_market_status_df_with_depth()
        # lines.extend(["", "  Markets:"] + ["\t" + line for line in
        #                                                     market_status_df.to_string(index=False).split("\n")])

        lines.extend(["", "  Markets:"] + [format_df_for_printout(market_status_df, table_format="grid")])

        # candle lines
        candles_df = self.get_candles_with_features()
        lines.extend(["", f"  Candles: {self.candles.name} | Interval: {self.candles.interval}", ""])
        lines.extend([format_df_for_printout(candles_df, table_format="grid")])
        # lines.extend(["    " + line for line in
        #               candles_df.tail(self.candles_length).iloc[::-1].to_string(index=False).split("\n")])

        # warning lines
        warning_lines = []
        warning_lines.extend(self.balance_warning(self.get_market_trading_pair_tuples()))
        if len(warning_lines) > 0:
            lines.extend(["", "*** WARNINGS ***"] + warning_lines)
        return "\n".join(lines)

    def get_market_status_df_with_depth(self):
        market_status_df = self.market_status_data_frame(self.get_market_trading_pair_tuples())
        market_status_df["Exchange"] = market_status_df.apply(
            lambda x: x["Exchange"].strip("PaperTrade") + "paper_trade", axis=1)
        market_status_df["Vol (+5 bps)"] = market_status_df.apply(
            lambda x: self.get_volume_for_percentage_from_mid_price(x, 0.0005), axis=1)
        market_status_df["Vol (-5 bps)"] = market_status_df.apply(
            lambda x: self.get_volume_for_percentage_from_mid_price(x, -0.0005), axis=1)
        market_status_df["Vol (+1%)"] = market_status_df.apply(
            lambda x: self.get_volume_for_percentage_from_mid_price(x, 0.01), axis=1)
        market_status_df["Vol (-1%)"] = market_status_df.apply(
            lambda x: self.get_volume_for_percentage_from_mid_price(x, -0.01), axis=1)

        return market_status_df

    def get_volume_for_percentage_from_mid_price(self, row, percentage):
        price = row["Mid Price"] * (1 + percentage)
        is_buy = percentage > 0
        result = self.connectors[row["Exchange"]].get_volume_for_price(row["Market"], is_buy, price)
        return Decimal(result.result_volume).quantize(Decimal("0.000"))

    def get_candles_with_features(self):
        candles_df = self.candles.candles_df
        candles_df.ta.rsi(length=self.candles_length, append=True)
        return candles_df
