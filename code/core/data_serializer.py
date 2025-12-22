import pandas as pd
from datetime import datetime
import logging

class DataSerializer:
    """
    The Data Serializer (Excel Builder)
    Processes JSON responses (both single rate and time series), 
    handles inversions/cross-rates via Pandas, and exports to Excel.
    """
    
    def serialize(self, fetcher_results: list, output_dir: str = "."):
        """
        Main method to process data and save Excel.
        """
        all_dfs = []
        
        # 1. Build a cache of available rates (Symbol -> DataFrame)
        # We need this for cross calculations.
        rate_cache = {}
        
        print("Building Rate Cache...")
        for item in fetcher_results:
            api_data = item['api_data']
            config = item['config']
            symbol = config['api_symbol']
            
            df = self._parse_api_response(api_data)
            if df is not None and not df.empty:
                rate_cache[symbol] = df

        # 2. Process each request manifest based on config
        print("Processing calculations...")
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
                        # Copy to avoid mutating cache
                        result_df = base_df.copy()
                        
                        if config['invert']:
                            result_df['Rate'] = 1.0 / result_df['Rate']
                            
                elif mode == 'cross_via_usd':
                    # Logic: Rate(Base->Target) = (1 / Rate(USD->Base)) * Rate(USD->Target)
                    usd_base_symbol = f"USD/{user_base}"
                    usd_target_symbol = f"USD/{user_target}"
                    
                    df_base = rate_cache.get(usd_base_symbol)
                    df_target = rate_cache.get(usd_target_symbol)
                    
                    if df_base is not None and df_target is not None:
                        # Join on Date using merge (inner join to ensure matching dates)
                        # Suffixes: _b (USD/Base), _t (USD/Target)
                        merged = pd.merge(df_base, df_target, on='Rate Date', suffixes=('_b', '_t'))
                        
                        # Calculate Cross Rate: (1 / USD/Base) * USD/Target
                        # merged['Rate_b'] is USD/Base
                        # merged['Rate_t'] is USD/Target
                        merged['Rate'] = (1.0 / merged['Rate_b']) * merged['Rate_t']
                        
                        result_df = merged[['Rate Date', 'Rate']].copy()
                
                if result_df is not None and not result_df.empty:
                    result_df['Base Currency'] = user_base
                    result_df['Target Currency'] = user_target
                    
                    # Ensure column order
                    result_df = result_df[['Rate Date', 'Base Currency', 'Target Currency', 'Rate']]
                    all_dfs.append(result_df)
                else:
                    print(f"Warning: Could not calculate rate for {user_base}/{user_target}")

            except Exception as e:
                print(f"Error processing {user_base}/{user_target}: {e}")

        # 3. Create Final DataFrame
        if not all_dfs:
            print("No data to save.")
            return

        final_df = pd.concat(all_dfs, ignore_index=True)
        
        # Round rates
        final_df['Rate'] = final_df['Rate'].round(6)
        
        # Sort by Base Currency, then Target Currency (Ticker), then Date (descending)
        final_df.sort_values(by=['Base Currency', 'Target Currency', 'Rate Date'], ascending=[True, True, False], inplace=True)

        # 4. Export to Excel
        filename = f"{output_dir}/Forex_Output.xlsx"
        try:
            final_df.to_excel(filename, index=False)
            print(f"Update Complete. Data saved to {filename}")
            print(final_df.head()) # Print preview
        except Exception as e:
            print(f"Error saving Excel file: {e}")

    def _parse_api_response(self, api_data: dict) -> pd.DataFrame:
        """
        Parses API response (either 'rate' or 'values') into a standardized DataFrame.
        Columns: ['Rate Date', 'Rate']
        """
        try:
            if 'values' in api_data:
                # Time Series
                # Values: [{'datetime': '2024-12-01', 'close': '18.5'}, ...]
                df = pd.DataFrame(api_data['values'])
                df['Rate'] = pd.to_numeric(df['close'])
                df['Rate Date'] = pd.to_datetime(df['datetime']).dt.strftime('%Y-%m-%d')
                return df[['Rate Date', 'Rate']]
            
            elif 'rate' in api_data:
                # Single Point
                rate = float(api_data['rate'])
                timestamp = api_data.get('timestamp', int(datetime.now().timestamp()))
                date_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
                
                return pd.DataFrame([{'Rate Date': date_str, 'Rate': rate}])
            
            return None
        except Exception as e:
            print(f"Error parsing API data: {e}")
            return None
