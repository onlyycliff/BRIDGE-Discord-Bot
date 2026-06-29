# Excel Data Manager - Thread-safe Excel operations for Bridge 2026 feedback
import pandas as pd
from pathlib import Path
from datetime import datetime
import threading
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExcelDataManager:
    """Thread-safe Excel data manager for poll feedback"""
    
    def __init__(self, file_path="responses.xlsx"):
        self.file_path = Path(file_path)
        self.lock = threading.Lock()  # Ensure thread-safe Excel operations
        self.main_sheet = "Poll Responses"
        self._initialize_excel()
    
    def _initialize_excel(self):
        """Create Excel file with headers if it doesn't exist"""
        try:
            if not self.file_path.exists():
                df = pd.DataFrame(columns=[
                    "Timestamp", "Username", "User_ID", "Question", 
                    "Choice", "Poll_ID", "Vote_Count"
                ])
                with pd.ExcelWriter(self.file_path, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name=self.main_sheet, index=False)
                logger.info(f"Excel file created at {self.file_path}")
            else:
                logger.info(f"Excel file exists at {self.file_path}")
        except Exception as e:
            logger.error(f"Error initializing Excel: {e}")
    
    def add_vote(self, username, user_id, question, choice, poll_id):
        """Add a vote to the Excel sheet (thread-safe)"""
        with self.lock:
            try:
                new_vote = pd.DataFrame([{
                    "Timestamp": datetime.now(),
                    "Username": username,
                    "User_ID": user_id,
                    "Question": question,
                    "Choice": choice,
                    "Poll_ID": poll_id,
                    "Vote_Count": 1
                }])
                
                existing = pd.read_excel(self.file_path, sheet_name=self.main_sheet)
                df = pd.concat([existing, new_vote], ignore_index=True)
                
                with pd.ExcelWriter(self.file_path, engine='openpyxl', mode='w') as writer:
                    df.to_excel(writer, sheet_name=self.main_sheet, index=False)
                
                logger.info(f"Vote recorded: {username} -> {choice}")
                return True
            except Exception as e:
                logger.error(f"Error adding vote: {e}")
                return False
    
    def get_poll_stats(self, poll_id):
        """Get statistics for a specific poll"""
        with self.lock:
            try:
                # Try new sheet first, then fallback
                try:
                    df = pd.read_excel(self.file_path, sheet_name=self.main_sheet)
                except ValueError:
                    # Read all sheets and combine
                    all_sheets = pd.read_excel(self.file_path, sheet_name=None)
                    df_list = []
                    for sheet, sheet_df in all_sheets.items():
                        if not sheet_df.empty and 'Timestamp' in sheet_df.columns:
                            df_list.append(sheet_df)
                    
                    if not df_list:
                        return None
                    df = pd.concat(df_list, ignore_index=True)
                
                # Try matching by poll_id, or by sheet name if no poll_id column
                poll_data = None
                if 'Poll_ID' in df.columns:
                    poll_data = df[df['Poll_ID'] == poll_id]
                
                if poll_data is None or poll_data.empty:
                    return None
                
                stats = {
                    "total_votes": len(poll_data),
                    "question": poll_data.iloc[0]['Question'] if 'Question' in poll_data.columns else "Unknown",
                    "choices": poll_data['Choice'].value_counts().to_dict() if 'Choice' in poll_data.columns else {},
                    "voters": poll_data['Username'].unique().tolist() if 'Username' in poll_data.columns else []
                }
                return stats
            except Exception as e:
                logger.error(f"Error getting poll stats: {e}")
                return None
    
    def get_all_votes(self):
        """Get all votes from Excel - handles both new and legacy formats"""
        with self.lock:
            try:
                # Try new sheet name first, then fallback to existing sheets
                sheet_name = self.main_sheet
                df_list = []
                
                try:
                    df = pd.read_excel(self.file_path, sheet_name=sheet_name)
                    return df.to_dict('records')
                except ValueError:
                    # Sheet doesn't exist, try reading all sheets and combine
                    all_sheets = pd.read_excel(self.file_path, sheet_name=None)
                    for sheet, df in all_sheets.items():
                        if df.empty:
                            continue
                        
                        # Standardize legacy column names
                        df = self._standardize_columns(df)
                        if 'Timestamp' in df.columns and 'Question' in df.columns:
                            df_list.append(df)
                    
                    if df_list:
                        combined = pd.concat(df_list, ignore_index=True)
                        return combined.to_dict('records')
                    return []
            except Exception as e:
                logger.error(f"Error reading votes: {e}")
                return []
    
    def _standardize_columns(self, df):
        """Standardize column names for legacy Excel formats"""
        rename_map = {
            'User': 'Username',
            'Time': 'Timestamp',
            'Poll ID': 'Poll_ID',
            'user': 'Username',
            'time': 'Timestamp',
            'poll id': 'Poll_ID'
        }
        
        # Rename columns that exist
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
        
        # Filter out completely empty rows and columns with all NaN
        df = df.dropna(how='all')
        df = df.dropna(axis=1, how='all')
        
        return df
    
    def export_to_csv(self, output_path="poll_feedback.csv"):
        """Export all data to CSV for analysis"""
        with self.lock:
            try:
                df = pd.read_excel(self.file_path, sheet_name=self.main_sheet)
                df.to_csv(output_path, index=False)
                logger.info(f"Data exported to {output_path}")
                return output_path
            except Exception as e:
                logger.error(f"Error exporting CSV: {e}")
                return None
    
    def get_summary_by_question(self):
        """Get summary statistics grouped by question"""
        with self.lock:
            try:
                # Try new sheet name first, then fallback
                try:
                    df = pd.read_excel(self.file_path, sheet_name=self.main_sheet)
                except ValueError:
                    # Sheet doesn't exist, read all sheets and combine
                    all_sheets = pd.read_excel(self.file_path, sheet_name=None)
                    df_list = []
                    for sheet, sheet_df in all_sheets.items():
                        if not sheet_df.empty:
                            sheet_df = self._standardize_columns(sheet_df)
                            if 'Question' in sheet_df.columns and not sheet_df['Question'].isna().all():
                                df_list.append(sheet_df)
                    
                    if not df_list:
                        return {}
                    df = pd.concat(df_list, ignore_index=True)
                
                if df.empty or 'Question' not in df.columns:
                    return {}
                
                # Remove rows where Question is NaN
                df = df.dropna(subset=['Question'])
                
                if df.empty:
                    return {}
                
                summary = df.groupby('Question').agg({
                    'Username': 'count' if 'Username' in df.columns else lambda x: len(x),
                    'Choice': lambda x: x.value_counts().to_dict() if 'Choice' in df.columns else {}
                }).rename(columns={'Username': 'Total_Votes'})
                
                return summary.to_dict('index')
            except Exception as e:
                logger.error(f"Error generating summary: {e}")
                return {}

# Initialize global manager
excel_manager = ExcelDataManager()
