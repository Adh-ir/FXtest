
from typing import List, Dict, Tuple

class ConfigManager:
    """
    The Configuration Manager (Input Parser)
    Parses user input string into a list of base currencies.ket, and generates valid currency pairs
    with inversion flags.
    """
    
    # Priority list for standard base currencies (Standard Forex Convention)
    STANDARD_BASES = ['EUR', 'GBP', 'AUD', 'NZD', 'USD', 'CAD', 'CHF']
    
    TARGET_BASKET = ["USD", "EUR", "GBP", "BWP", "MWK", "ZAR"]

    @staticmethod
    def parse_input(base_currencies_str: str) -> List[str]:
        """Parses a comma-separated string of base currencies into a list."""
        if not base_currencies_str:
            return []
        
        bases = [b.strip().upper() for b in base_currencies_str.split(',')]
        return [b for b in bases if b]

    @classmethod
    def generate_pairs(cls, base_currencies: List[str]) -> List[Dict]:
        """
        Generates a list of dictionaries containing pair configuration.
        """
        pairs_config = []
        
        for user_base in base_currencies:
            for user_target in cls.TARGET_BASKET:
                if user_base == user_target:
                    continue
                
                # Check for Exotic-Exotic case
                is_base_exotic = cls._is_exotic(user_base)
                is_target_exotic = cls._is_exotic(user_target)
                
                if is_base_exotic and is_target_exotic:
                    # Both exotic (e.g. ZAR -> BWP)
                    # We request USD/Target (e.g. USD/BWP)
                    # And signal Cross Calculation
                    api_symbol = f"USD/{user_target}"
                    # Note: We rely on the fact that USD/Base (USD/ZAR) will be fetched 
                    # because USD is in TARGET_BASKET.
                    pairs_config.append({
                        'api_symbol': api_symbol,
                        'invert': False,
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
    def _is_exotic(cls, currency: str) -> bool:
        return currency not in cls.STANDARD_BASES

    @classmethod
    def _determine_standard_pair(cls, currency_a: str, currency_b: str) -> Tuple[str, bool]:
        """
        Determines the standard API symbol and inversion.
        """
        def get_priority(curr):
            try:
                return cls.STANDARD_BASES.index(curr)
            except ValueError:
                return 999
        
        p_a = get_priority(currency_a)
        p_b = get_priority(currency_b)
        
        if p_a < p_b:
            # A/B
            return f"{currency_a}/{currency_b}", False
        elif p_b < p_a:
            # B/A, Invert
            return f"{currency_b}/{currency_a}", True
        else:
            # Should not happen if we handle Exotics separately, 
            # but failsafe to alphabetical if both standard (unlikely overlap)
            if currency_a < currency_b:
                return f"{currency_a}/{currency_b}", False
            else:
                return f"{currency_b}/{currency_a}", True
