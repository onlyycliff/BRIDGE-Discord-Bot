# Excel Data Manager - Thread-safe Excel operations for Bridge 2026 feedback
import pandas as pd
from pathlib import Path
from datetime import datetime
import threading
import logging
from typing import Optional, List, Dict

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExcelDataManager:
    """Thread-safe Excel data manager for poll feedback with validation"""
    
    def __init__(self, file_path: str = "responses.xlsx"):
        self.file_path = Path(file_path)
        self.lock = threading.Lock()  # Ensures thread-safe Excel operations
        self.main_sheet = "Poll Responses"
        self._initialize_excel()
    
    def _initialize_excel(self) -> None:
        """Create Excel file with headers if it doesn't exist"""
        try:
            if not self.file_path.exists():
                # Initialize with proper columns
                df = pd.DataFrame(columns=[
                    "Timestamp", "Username", "User_ID", "Question", 
                    "Choice", "Poll_ID"
                ])
                with pd.ExcelWriter(self.file_path, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name=self.main_sheet, index=False)
                logger.info(f"Excel file created at {self.file_path}")
            else:
                logger.info(f"Excel file exists at {self.file_path}")
        except Exception as e:
            logger.error(f"Error initializing Excel: {e}")
    
    def add_vote(self, username: str, user_id: int, question: str, choice: str, poll_id: int) -> bool:
        """
        Add a vote to the Excel sheet (thread-safe)
        
        Args:
            username: Display name of voting user
            user_id: Discord user ID
            question: Poll question
            choice: User's selected option
            poll_id: Unique poll identifier
        
        Returns:
            True if successful, False otherwise
        """
        # Validate inputs
        if not all([username, user_id, question, choice, poll_id]):
            logger.error(f"Invalid vote parameters - Missing required fields")
            return False
        
        # Sanitize string inputs
        username = str(username).strip()[:100]
        question = str(question).strip()[:500]
        choice = str(choice).strip()[:200]
        
        with self.lock:
            try:
                new_vote = pd.DataFrame([{
                    "Timestamp": str(datetime.now()),
                    "Username": username,
                    "User_ID": int(user_id),
                    "Question": question,
                    "Choice": choice,
                    "Poll_ID": int(poll_id)
                }])
                
                # Read existing votes and append
                try:
                    existing = pd.read_excel(self.file_path, sheet_name=self.main_sheet)
                    df = pd.concat([existing, new_vote], ignore_index=True)
                except (ValueError, FileNotFoundError):
                    df = new_vote
                
                # Write back to Excel
                with pd.ExcelWriter(self.file_path, engine='openpyxl', mode='w') as writer:
                    df.to_excel(writer, sheet_name=self.main_sheet, index=False)
                
                logger.info(f"Vote recorded: {username} ({user_id}) -> {choice} for poll {poll_id}")
                return True
            except Exception as e:
                logger.error(f"Error adding vote: {e}")
                return False
    
    def get_poll_stats(self, poll_id: int) -> Optional[Dict]:
        """Get statistics for a specific poll"""
        with self.lock:
            try:
                df = self._read_all_data()
                if df.empty or 'Poll_ID' not in df.columns:
                    return None
                
                poll_data = df[df['Poll_ID'] == poll_id]
                
                if poll_data.empty:
                    return None
                
                # Build stats with proper type conversions
                choices = {}
                if 'Choice' in poll_data.columns:
                    choices = poll_data['Choice'].value_counts().to_dict()
                
                voters = []
                if 'Username' in poll_data.columns:
                    voters = poll_data['Username'].unique().tolist()
                
                stats = {
                    "total_votes": len(poll_data),
                    "question": poll_data.iloc[0]['Question'] if 'Question' in poll_data.columns else "Unknown",
                    "choices": choices,
                    "voters": voters
                }
                logger.info(f"Retrieved stats for poll {poll_id}: {stats['total_votes']} votes")
                return stats
            except Exception as e:
                logger.error(f"Error getting poll stats: {e}", exc_info=True)
                return None
    
    def get_all_votes(self) -> List[Dict]:
        """Get all votes from Excel"""
        with self.lock:
            try:
                df = self._read_all_data()
                if df.empty:
                    return []
                
                # Convert to dict and ensure all timestamps are strings
                records = []
                for _, row in df.iterrows():
                    record = row.to_dict()
                    # Convert pandas Timestamp to string for JSON serialization
                    if 'Timestamp' in record and pd.notna(record['Timestamp']):
                        record['Timestamp'] = str(record['Timestamp'])
                    records.append(record)
                return records
            except Exception as e:
                logger.error(f"Error reading votes: {e}", exc_info=True)
                return []
    
    def _read_all_data(self) -> pd.DataFrame:
        """Safely read all data from Excel with fallback support"""
        try:
            # Try new sheet name first
            df = pd.read_excel(self.file_path, sheet_name=self.main_sheet)
            return df
        except (ValueError, FileNotFoundError):
            # Fallback: read all sheets and combine
            try:
                all_sheets = pd.read_excel(self.file_path, sheet_name=None)
                df_list = []
                for sheet, sheet_df in all_sheets.items():
                    if not sheet_df.empty:
                        sheet_df = self._standardize_columns(sheet_df)
                        if 'Timestamp' in sheet_df.columns:
                            df_list.append(sheet_df)
                
                if df_list:
                    return pd.concat(df_list, ignore_index=True)
            except Exception as e:
                logger.error(f"Error reading all data: {e}")
            
            return pd.DataFrame()
    
    def _standardize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize column names for legacy Excel formats"""
        rename_map = {
            'User': 'Username',
            'Time': 'Timestamp',
            'Poll ID': 'Poll_ID',
            'user': 'Username',
            'time': 'Timestamp',
            'poll id': 'Poll_ID'
        }
        
        # Rename matching columns
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
        
        # Remove empty rows and columns
        df = df.dropna(how='all')
        df = df.dropna(axis=1, how='all')
        
        return df
    
    def export_to_csv(self, output_path: str = "poll_feedback.csv") -> Optional[str]:
        """Export all data to CSV for analysis"""
        with self.lock:
            try:
                df = self._read_all_data()
                if df.empty:
                    logger.warning("No data to export")
                    return None
                
                df.to_csv(output_path, index=False)
                logger.info(f"Data exported to {output_path}")
                return output_path
            except Exception as e:
                logger.error(f"Error exporting CSV: {e}")
                return None
    
    def get_summary_by_question(self) -> Dict:
        """Get summary statistics grouped by question"""
        with self.lock:
            try:
                df = self._read_all_data()
                
                if df.empty or 'Question' not in df.columns:
                    return {}
                
                # Remove empty questions
                df = df.dropna(subset=['Question'])
                
                if df.empty:
                    return {}
                
                # Build summary with proper type conversions
                summary = {}
                for question, group in df.groupby('Question'):
                    if pd.isna(question) or not str(question).strip():
                        continue
                    
                    choice_counts = {}
                    if 'Choice' in group.columns:
                        choice_counts = group['Choice'].value_counts().to_dict()
                    
                    summary[str(question)] = {
                        'Total_Votes': len(group),
                        'Choices': choice_counts
                    }
                
                logger.info(f"Generated summary with {len(summary)} questions")
                return summary
            except Exception as e:
                logger.error(f"Error generating summary: {e}", exc_info=True)
                return {}

# Initialize global manager instance
excel_manager = ExcelDataManager()
