import pandas as pd
from typing import List, Dict, Optional, Tuple
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class DataProcessor:
    """
    Handles data processing, including configuration generation and DataFrame creation.
    """
    
    STANDARD_BASES = ['EUR', 'GBP', 'AUD', 'NZD', 'USD', 'CAD', 'CHF']
    TARGET_BASKET = ["USD", "EUR", "GBP", "BWP", "MWK", "ZAR"]

    @staticmethod
    def parse_input_bases(base_currencies_str: str) -> List[str]:
        """Parses a comma-separated string of base currencies into a list."""
        if not base_currencies_str:
            return []
        bases = [b.strip().upper() for b in base_currencies_str.split(',')]
        return [b for b in bases if b]
    
    @classmethod
    def generate_pairs_config(cls, base_currencies: List[str]) -> List[Dict]:
        """
        Generates a list of dictionaries containing pair configuration.
        Preserves the legacy logic for Exotic-Exotic cross rates via USD.
        """
        pairs_config = []
        
        for user_base in base_currencies:
            for user_target in cls.TARGET_BASKET:
                if user_base == user_target:
                    continue
                
                # Check for Exotic-Exotic case
                is_base_exotic = user_base not in cls.STANDARD_BASES
                is_target_exotic = user_target not in cls.STANDARD_BASES
                
                if is_base_exotic and is_target_exotic:
                    # Both exotic (e.g. ZAR -> BWP) -> Cross via USD
                    api_symbol = f"USD/{user_target}" # Request USD/Target
                    # We assume USD/Base (USD/ZAR) will be fetched because USD is in TARGET_BASKET
                    # if user_base was processed as a target for USD? 
                    # WAIT: The legacy logic assumes if we are processing ZAR, we need USD/ZAR separate?
                    # Actually, if user requests ZAR, we iterate TARGET_BASKET which includes USD.
                    # So USD/ZAR (or ZAR/USD) will be generated as a direct pair in the loop.
                    # BUT, cross calc needs USD/ZAR availability.
                    # If user_base is ZAR, we get ZAR->USD.
                    
                    pairs_config.append({
                        'api_symbol': api_symbol,
                        'invert': False, # Not used for cross logic directly but good to have
                        'user_base': user_base,
                        'user_target': user_target,
                        'calculation_mode': 'cross_via_usd'
                    })
                else:
                    # Standard logic
                    api_symbol, invert = cls._determine_standard_pair(user_base, user_target)
                    pairs_config.append({
                        'api_symbol': api_symbol,
                        'invert': invert,
                        'user_base': user_base,
                        'user_target': user_target,
                        'calculation_mode': 'direct'
                    })
        
        return pairs_config

    @classmethod
    def _determine_standard_pair(cls, currency_a: str, currency_b: str) -> Tuple[str, bool]:
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
    def process_results(cls, fetcher_results: List[Dict]) -> pd.DataFrame:
        """
        Processes fetch results into a single clean DataFrame.
        """
        all_dfs = []
        rate_cache = {}
        
        # 1. Build Cache
        for item in fetcher_results:
            api_data = item['api_data']
            config = item['config']
            symbol = config['api_symbol']
            
            df = cls._parse_api_response(api_data)
            if df is not None and not df.empty:
                rate_cache[symbol] = df
        
        # 2. Calculate Rates
        for item in fetcher_results:
            config = item['config']
            user_base = config['user_base']
            user_target = config['user_target']
            mode = config.get('calculation_mode', 'direct')
            
            try:
                result_df = None
                
                if mode == 'direct':
                    api_symbol = config['api_symbol']
                    base_df = rate_cache.get(api_symbol)
                    
                    if base_df is not None:
                        result_df = base_df.copy()
                        if config['invert']:
                            result_df['Exchange Rate'] = 1.0 / result_df['Exchange Rate']
                            
                elif mode == 'cross_via_usd':
                    # Rate(Base->Target) = (1 / Rate(USD->Base)) * Rate(USD->Target)
                    # We need USD/Base and USD/Target
                    
                    # NOTE: We need to find the correct API symbols for these components.
                    # The legacy logic constructed them as f"USD/{user_base}" and f"USD/{user_target}".
                    # This implies USD is always base in the cache for these exotics.
                    # Since both are exotic (not in standard list), _determine_standard_pair(USD, Exotic)
                    # should give USD/Exotic because USD in standard list (priority < 999).
                    
                    usd_base_symbol = f"USD/{user_base}"
                    usd_target_symbol = f"USD/{user_target}"
                    
                    df_base = rate_cache.get(usd_base_symbol)
                    df_target = rate_cache.get(usd_target_symbol)
                    
                    if df_base is not None and df_target is not None:
                         merged = pd.merge(df_base, df_target, on='Date', suffixes=('_b', '_t'))
                         # (1 / USD->Base) * USD->Target
                         merged['Exchange Rate'] = (1.0 / merged['Exchange Rate_b']) * merged['Exchange Rate_t']
                         result_df = merged[['Date', 'Exchange Rate']].copy()

                if result_df is not None and not result_df.empty:
                    result_df['Currency Base'] = user_base
                    result_df['Currency Source'] = user_target
                    all_dfs.append(result_df)
                else:
                    logger.warning(f"Could not calculate rate for {user_base}/{user_target}")

            except Exception as e:
                logger.error(f"Error processing {user_base}/{user_target}: {e}")

        if not all_dfs:
            return pd.DataFrame(columns=['Currency Base', 'Currency Source', 'Date', 'Exchange Rate'])
            
        final_df = pd.concat(all_dfs, ignore_index=True)
        
        # Rounding
        final_df['Exchange Rate'] = final_df['Exchange Rate'].round(6)
        
        # Strict Column Ordering
        final_df = final_df[['Currency Base', 'Currency Source', 'Date', 'Exchange Rate']]
        
        # Sorting
        final_df.sort_values(by=['Currency Base', 'Currency Source', 'Date'], ascending=[True, True, False], inplace=True)
        
        return final_df

    @classmethod
    def _parse_api_response(cls, api_data: Dict) -> Optional[pd.DataFrame]:
        """
        Parses API response into a standardized DataFrame.
        """
        try:
            if 'values' in api_data:
                # Time Series
                df = pd.DataFrame(api_data['values'])
                df['Exchange Rate'] = pd.to_numeric(df['close'])
                df['Date'] = pd.to_datetime(df['datetime']).dt.strftime('%Y-%m-%d')
                return df[['Date', 'Exchange Rate']]
            
            elif 'rate' in api_data:
                # Real-time
                rate = float(api_data['rate'])
                timestamp = api_data.get('timestamp', int(datetime.now().timestamp()))
                date_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
                return pd.DataFrame([{'Date': date_str, 'Exchange Rate': rate}])
            
            return None
        except Exception as e:
            logger.error(f"Error parsing API data: {e}")
            return None
