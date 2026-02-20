"""Stock manager for handling stock data operations."""

import pandas as pd
from typing import Optional


class StockManager:
    """Manages stock data with operations for getting and setting values."""
    
    def __init__(self, stock_file: str):
        """
        Initialize the stock manager.
        
        Args:
            stock_file: Path to the stock CSV file
        """
        self.df_stock = pd.read_csv(stock_file)
        self.df_stock.set_index(["naam", "jaar", "zone"], inplace=True)
        self.df_stock = self.df_stock.sort_index()
    
    def get_aantal(self, naam: str, jaar: int, zone: str) -> float:
        """
        Get the value of a stock for a specific name, year, and zone.
        
        Args:
            naam: Stock name
            jaar: Year
            zone: Zone identifier
            
        Returns:
            The stock value
        """
        return self.df_stock.loc[(naam, jaar, zone), "aantal"]
    
    def set_aantal(self, naam: str, jaar: int, zone: str, aantal: float) -> None:
        """
        Set the value of a stock for a specific name, year, and zone.
        
        Args:
            naam: Stock name
            jaar: Year
            zone: Zone identifier
            aantal: Value to set
        """
        self.df_stock.loc[(naam, jaar, zone), "aantal"] = aantal
        self.df_stock.sort_index(inplace=True)
    
    def save(self, output_file: str) -> None:
        """
        Save the stock data to a CSV file.
        
        Args:
            output_file: Path to save the CSV file
        """
        self.df_stock.to_csv(output_file)
    
    def get_dataframe(self) -> pd.DataFrame:
        """
        Get the underlying DataFrame.
        
        Returns:
            The stock DataFrame
        """
        return self.df_stock.copy()
