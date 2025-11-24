import pandas as pd
from typing import Union, Optional, List
import numpy as np


class DataImporter:
    """
    Import, validate, and process data from spreadsheet files.
    Follows import → validate → select columns workflow.
    """
    
    def __init__(self, file_path: str, columns: Optional[List[str]] = None, 
                 validate_columns: Optional[List[str]] = None) -> None:
        """
        Initialize data importer.
        
        Args:
            file_path: Path to the spreadsheet file
            columns: List of columns to extract. If None, all columns are returned.
            validate_columns: List of columns that must be present in the data
        """
        self.file_path = file_path
        self.columns = columns
        self.validate_columns = validate_columns or []
        self.data_frame = self._import_validate_select()
    
    def _import_spreadsheet(self) -> Union[pd.DataFrame, List]:
        """
        STEP 1: Import .csv, .xls, or .xlsx file into a pandas DataFrame.
        Returns empty list if import fails.
        """
        try:
            file_path_lower = self.file_path.lower()
            
            if file_path_lower.endswith('.csv'):
                df = pd.read_csv(self.file_path)
            elif file_path_lower.endswith(('.xls', '.xlsx')):
                df = pd.read_excel(self.file_path)
            else:
                print(f"Unsupported file format: {self.file_path}")
                return []
            
            # Replace NaN/NA with None
            df = df.replace({np.nan: None})
            return df
            
        except Exception as e:
            print(f"Error importing file '{self.file_path}': {e}")
            return []
    
    def _validate_columns(self, df: pd.DataFrame) -> None:
        """
        STEP 2: Validate that all required columns are present in the DataFrame.
        """
        if self.validate_columns:
            missing_columns = [
                col for col in self.validate_columns 
                if col not in df.columns
            ]
            if missing_columns:
                raise ValueError(
                    f"Expected columns {missing_columns} not found in data. "
                    f"Available columns: {list(df.columns)}"
                )
    
    def _select_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        STEP 3: Select and return specified columns from DataFrame.
        """
        if self.columns:
            return df[self.columns]
        return df
    
    def _import_validate_select(self) -> pd.DataFrame:
        """
        Execute the complete workflow: import → validate → select columns.
        """
        # STEP 1: Import
        df = self._import_spreadsheet()
        
        if not isinstance(df, pd.DataFrame) or df.empty:
            raise ValueError(f"Failed to import TikTok data from: {self.file_path}")
        
        # STEP 2: Validate
        self._validate_columns(df)
        
        # STEP 3: Select columns
        processed_df = self._select_columns(df)
        
        return processed_df
    
    def get_data(self) -> pd.DataFrame:
        """Return the imported and processed DataFrame."""
        return self.data_frame.copy()
    
    def get_summary(self) -> dict:
        """Return summary statistics about the imported data."""
        if self.data_frame.empty:
            return {}
        
        return {
            'rows': len(self.data_frame),
            'columns': len(self.data_frame.columns),
            'memory_usage': self.data_frame.memory_usage(deep=True).sum(),
            'column_names': list(self.data_frame.columns),
            'missing_values': self.data_frame.isnull().sum().to_dict()
        }

