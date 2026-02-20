"""Flow manager for handling flow data and measure selections."""

import pandas as pd
from typing import Tuple


class FlowManager:
    """Manages flow data and measure applications."""
    
    def __init__(self, flow_file: str, beschrijving_file: str):
        """
        Initialize the flow manager.
        
        Args:
            flow_file: Path to the flow CSV file
            beschrijving_file: Path to the measure description CSV file
        """
        self.df_flow = pd.read_csv(flow_file)
        self.df_beschrijving_maatregelen = pd.read_csv(beschrijving_file)
        
        self.df_flow = self.df_flow.set_index(
            ["naam", "zone"], verify_integrity=True
        ).sort_index()
        self.df_beschrijving_maatregelen = self.df_beschrijving_maatregelen.set_index(
            ["naam"], verify_integrity=True
        )
    
    def get_flow(self, naam: str, zone: str) -> float:
        """
        Get the flow value for a measure, considering whether it's applied.
        
        Args:
            naam: Measure name
            zone: Zone identifier
            
        Returns:
            The flow value (either normal or after measure)
        """
        maatregel_toepassen = self.df_flow.loc[(naam, zone), "maatregel_toepassen"]
        
        if maatregel_toepassen:
            return self.df_flow.loc[(naam, zone), "waarde_na_maatregel"]
        else:
            return self.df_flow.loc[(naam, zone), "waarde_normaal"]
    
    def get_selected_zones(self, maatregel_naam: str) -> Tuple[str, ...]:
        """
        Get zones where a measure is currently applied.
        
        Args:
            maatregel_naam: Measure name
            
        Returns:
            Tuple of zone identifiers where measure is applied
        """
        subset = self.df_flow.loc[maatregel_naam]
        return tuple(subset.index[subset["maatregel_toepassen"]])
    
    def set_selected_zones(self, maatregel_naam: str, selected_zones: Tuple[str, ...]) -> None:
        """
        Set which zones a measure is applied to.
        
        Args:
            maatregel_naam: Measure name
            selected_zones: Tuple of zone identifiers to apply the measure to
        """
        idx = pd.IndexSlice
        self.df_flow.loc[idx[maatregel_naam, :], "maatregel_toepassen"] = (
            self.df_flow.loc[idx[maatregel_naam, :]]
            .index.get_level_values("zone")
            .isin(selected_zones)
        )
    
    def get_total_cost(self) -> float:
        """
        Get the total cost of all applied measures.
        
        Returns:
            Total cost
        """
        return self.df_flow.loc[self.df_flow["maatregel_toepassen"], "kost_maatregel"].sum()
    
    def get_measure_descriptions(self) -> pd.DataFrame:
        """
        Get the measure descriptions DataFrame.
        
        Returns:
            DataFrame with measure descriptions
        """
        return self.df_beschrijving_maatregelen.copy()
    
    def is_measure_applied(self, naam: str, zone: str) -> bool:
        """
        Check if a measure is applied in a specific zone.
        
        Args:
            naam: Measure name
            zone: Zone identifier
            
        Returns:
            True if measure is applied, False otherwise
        """
        return self.df_flow.loc[(naam, zone), "maatregel_toepassen"]
