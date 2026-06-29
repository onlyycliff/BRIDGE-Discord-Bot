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
                df = pd.read_excel(self.file_path, sheet_name=self.main_sheet)
                poll_data = df[df['Poll_ID'] == poll_id]
                
                if poll_data.empty:
                    return None
                
                stats = {
                    "total_votes": len(poll_data),
                    "question": poll_data.iloc[0]['Question'],
                    "choices": poll_data['Choice'].value_counts().to_dict(),
                    "voters": poll_data['Username'].unique().tolist()
                }
                return stats
            except Exception as e:
                logger.error(f"Error getting poll stats: {e}")
                return None
    
    def get_all_votes(self):
        """Get all votes from Excel"""
        with self.lock:
            try:
                df = pd.read_excel(self.file_path, sheet_name=self.main_sheet)
                return df.to_dict('records')
            except Exception as e:
                logger.error(f"Error reading votes: {e}")
                return []
    
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
                df = pd.read_excel(self.file_path, sheet_name=self.main_sheet)
                summary = df.groupby('Question').agg({
                    'Vote_Count': 'sum',
                    'Username': 'count',
                    'Choice': lambda x: x.value_counts().to_dict()
                }).rename(columns={'Username': 'Total_Votes'})
                
                return summary.to_dict('index')
            except Exception as e:
                logger.error(f"Error generating summary: {e}")
                return {}

# Initialize global manager
excel_manager = ExcelDataManager()
