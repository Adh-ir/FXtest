"""
Data Processor Module

Handles data processing, including configuration generation and DataFrame creation.
"""

import logging
from datetime import datetime

import pandas as pd

logger = logging.getLogger(__name__)


class DataProcessor:
    """
    Handles data processing, including configuration generation and DataFrame creation.
    """

    STANDARD_BASES = ["EUR", "GBP", "AUD", "NZD", "USD", "CAD", "CHF"]

    # Currency Presets
    TARGET_BASKET = ["USD", "EUR", "GBP", "BWP", "MWK", "ZAR"]  # Default
    MAJOR_BASKET = ["USD", "EUR", "GBP", "CHF", "JPY", "CAD", "AUD", "NZD"]
    AFRICAN_BASKET = ["BWP", "MWK", "NAD", "SZL", "LSL", "ZAR", "NGN", "KES", "EGP"]

    @staticmethod
    def parse_targets(input_str: str, base_currency: str = None, api_client=None) -> list[str]:
        """
        Parses user input for target currencies.

        Supports:
            - Comma-separated: "USD, EUR, GBP"
            - Keywords: [ALL], [MAJOR], [AFRICAN], [DEFAULT]
            - Empty/blank: Returns default basket

        Args:
            input_str: User input string
            base_currency: Base currency code (needed for [ALL])
            api_client: TwelveDataClient instance (needed for [ALL])

        Returns:
            List of currency codes
        """
        if not input_str or not input_str.strip():
            return DataProcessor.TARGET_BASKET.copy()

        cleaned = input_str.strip().upper()

        # Handle keywords
        if cleaned == "[DEFAULT]" or cleaned == "DEFAULT":
            return DataProcessor.TARGET_BASKET.copy()

        if cleaned == "[MAJOR]" or cleaned == "MAJOR":
            return DataProcessor.MAJOR_BASKET.copy()

        if cleaned == "[AFRICAN]" or cleaned == "AFRICAN":
            return DataProcessor.AFRICAN_BASKET.copy()

        if cleaned == "[ALL]" or cleaned == "ALL":
            if api_client and base_currency:
                all_pairs = api_client.fetch_available_pairs(base_currency)
                if all_pairs:
                    return all_pairs
            # Fallback if API call fails
            logger.warning("[ALL] requested but no API client provided or API failed. Using defaults.")
            return DataProcessor.TARGET_BASKET.copy()

        # Parse comma-separated input
        currencies = [c.strip().upper() for c in cleaned.split(",")]
        # Filter out empty strings and base currency itself
        currencies = [c for c in currencies if c and c != (base_currency.upper() if base_currency else "")]

        return currencies if currencies else DataProcessor.TARGET_BASKET.copy()

    @staticmethod
    def parse_input_bases(base_currencies_str: str) -> list[str]:
        """Parses a comma-separated string of base currencies into a list."""
        if not base_currencies_str:
            return []
        bases = [b.strip().upper() for b in base_currencies_str.split(",")]
        return [b for b in bases if b]

    @classmethod
    def generate_pairs_config(cls, base_currencies: list[str], target_currencies: list[str] = None) -> list[dict]:
        """
        Generates a list of dictionaries containing pair configuration.
        Preserves the legacy logic for Exotic-Exotic cross rates via USD.

        Args:
            base_currencies: List of base currency codes
            target_currencies: Optional list of target currencies. Defaults to TARGET_BASKET.
        """
        if target_currencies is None:
            target_currencies = cls.TARGET_BASKET

        pairs_config = []

        for user_base in base_currencies:
            for user_target in target_currencies:
                if user_base == user_target:
                    continue

                # Check for Exotic-Exotic case
                is_base_exotic = user_base not in cls.STANDARD_BASES
                is_target_exotic = user_target not in cls.STANDARD_BASES

                if is_base_exotic and is_target_exotic:
                    # Both exotic (e.g. ZAR -> BWP) -> Cross via USD
                    api_symbol = f"USD/{user_target}"

                    pairs_config.append(
                        {
                            "api_symbol": api_symbol,
                            "invert": False,
                            "user_base": user_base,
                            "user_target": user_target,
                            "calculation_mode": "cross_via_usd",
                        }
                    )
                else:
                    # Standard logic
                    api_symbol, invert = cls._determine_standard_pair(user_base, user_target)
                    pairs_config.append(
                        {
                            "api_symbol": api_symbol,
                            "invert": invert,
                            "user_base": user_base,
                            "user_target": user_target,
                            "calculation_mode": "direct",
                        }
                    )

        return pairs_config

    @classmethod
    def _determine_standard_pair(cls, currency_a: str, currency_b: str) -> tuple[str, bool]:
        """
        Determines the standard API symbol and inversion based on standard priority.
        """

        def get_priority(curr):
            try:
                return cls.STANDARD_BASES.index(curr)
            except ValueError:
                return 999

        p_a = get_priority(currency_a)
        p_b = get_priority(currency_b)

        if p_a < p_b:
            return f"{currency_a}/{currency_b}", False
        elif p_b < p_a:
            return f"{currency_b}/{currency_a}", True
        else:
            if currency_a < currency_b:
                return f"{currency_a}/{currency_b}", False
            else:
                return f"{currency_b}/{currency_a}", True

    @classmethod
    def process_results(cls, fetcher_results: list[dict], start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        Processes fetch results into a single clean DataFrame.
        Applies forward fill if dates are provided.
        """
        all_dfs = []
        rate_cache = {}

        # Determine filling range if dates provided
        fill_index = None
        if start_date and end_date:
            try:
                # Cap end_date at YESTERDAY to prevent forward-filling into today
                # Today's rate should either be fetched directly or show as unavailable
                req_end = pd.to_datetime(end_date)
                today = pd.to_datetime(datetime.now().date())
                yesterday = today - pd.Timedelta(days=1)

                # Use the earlier of: requested end, or yesterday (never include today in ffill)
                final_end = min(req_end, yesterday)
                start_dt = pd.to_datetime(start_date)

                if start_dt <= final_end:
                    fill_index = pd.date_range(start=start_dt, end=final_end, freq="D")
            except Exception as e:
                logger.warning(f"Could not create fill index: {e}")

        # 1. Build Cache
        for item in fetcher_results:
            api_data = item["api_data"]
            config = item["config"]
            symbol = config["api_symbol"]

            df = cls._parse_api_response(api_data)

            if df is not None and not df.empty and fill_index is not None:
                # Apply Forward Fill
                df["Date"] = pd.to_datetime(df["Date"])
                df.set_index("Date", inplace=True)

                # Reindex and Forward Fill with limit 3
                df = df.reindex(fill_index)
                df = df.ffill(limit=3)

                # Reset index to restore Date column
                df.reset_index(inplace=True)
                df.rename(columns={"index": "Date"}, inplace=True)
                df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")

                # Drop rows that are still NaN (gaps > 3 days)
                df.dropna(subset=["Exchange Rate"], inplace=True)

            if df is not None and not df.empty:
                rate_cache[symbol] = df

        # 2. Calculate Rates
        for item in fetcher_results:
            config = item["config"]
            user_base = config["user_base"]
            user_target = config["user_target"]
            mode = config.get("calculation_mode", "direct")

            try:
                result_df = None

                if mode == "direct":
                    api_symbol = config["api_symbol"]
                    base_df = rate_cache.get(api_symbol)

                    if base_df is not None:
                        result_df = base_df.copy()
                        if config["invert"]:
                            result_df["Exchange Rate"] = 1.0 / result_df["Exchange Rate"]

                elif mode == "cross_via_usd":
                    # Rate(Base->Target) = (1 / Rate(USD->Base)) * Rate(USD->Target)
                    usd_base_symbol = f"USD/{user_base}"
                    usd_target_symbol = f"USD/{user_target}"

                    df_base = rate_cache.get(usd_base_symbol)
                    df_target = rate_cache.get(usd_target_symbol)

                    if df_base is not None and df_target is not None:
                        merged = pd.merge(df_base, df_target, on="Date", suffixes=("_b", "_t"))
                        # (1 / USD->Base) * USD->Target
                        merged["Exchange Rate"] = (1.0 / merged["Exchange Rate_b"]) * merged["Exchange Rate_t"]
                        result_df = merged[["Date", "Exchange Rate"]].copy()

                if result_df is not None and not result_df.empty:
                    result_df["Currency Base"] = user_base
                    result_df["Currency Source"] = user_target
                    all_dfs.append(result_df)
                else:
                    logger.warning(f"Could not calculate rate for {user_base}/{user_target}")

            except Exception as e:
                logger.error(f"Error processing {user_base}/{user_target}: {e}")

        if not all_dfs:
            return pd.DataFrame(columns=["Currency Base", "Currency Source", "Date", "Exchange Rate"])

        final_df = pd.concat(all_dfs, ignore_index=True)

        # Rounding
        final_df["Exchange Rate"] = final_df["Exchange Rate"].round(6)

        # Strict Column Ordering
        final_df = final_df[["Currency Base", "Currency Source", "Date", "Exchange Rate"]]

        # Sorting
        final_df.sort_values(
            by=["Currency Base", "Currency Source", "Date"],
            ascending=[True, True, False],
            inplace=True,
        )

        return final_df

    @classmethod
    def _parse_api_response(cls, api_data: dict) -> pd.DataFrame | None:
        """
        Parses API response into a standardized DataFrame.
        """
        try:
            if "values" in api_data:
                # Time Series
                df = pd.DataFrame(api_data["values"])
                df["Exchange Rate"] = pd.to_numeric(df["close"])
                df["Date"] = pd.to_datetime(df["datetime"]).dt.strftime("%Y-%m-%d")
                return df[["Date", "Exchange Rate"]]

            elif "rate" in api_data:
                # Real-time
                rate = float(api_data["rate"])
                timestamp = api_data.get("timestamp", int(datetime.now().timestamp()))
                date_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
                return pd.DataFrame([{"Date": date_str, "Exchange Rate": rate}])

            return None
        except Exception as e:
            logger.error(f"Error parsing API data: {e}")
            return None
