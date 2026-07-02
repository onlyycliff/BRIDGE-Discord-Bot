# Google Colab & Google Sheets Integration Module
# Handles secure data sync and analysis without exposing credentials

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
from .excel_manager import excel_manager

try:
    import gspread
    from google.colab import auth
    HAS_COLAB = True
except ImportError:
    HAS_COLAB = False

logger = logging.getLogger(__name__)

class ColabIntegration:
    """Google Sheets & Colab integration for Bridge 2026 data analysis"""
    
    def __init__(self, sheets_url: Optional[str] = None):
        """
        Initialize Colab/Sheets integration
        
        Args:
            sheets_url: URL or ID of Google Sheet for data sync
        """
        self.sheets_url = sheets_url
        self.is_configured = bool(sheets_url)
        self.gs = None
        self.worksheet = None
        
        if self.is_configured:
            self._initialize_sheets()
    
    def _initialize_sheets(self) -> bool:
        """Authenticate and initialize Google Sheets connection"""
        try:
            if not HAS_COLAB:
                logger.warning("gspread not installed. Sheets integration unavailable.")
                logger.info("Install with: pip install gspread google-auth-oauthlib")
                return False
            
            # Authenticate (use service account or OAuth)
            try:
                auth.authenticate_user()
                self.gs = gspread.authorize(None)  # Will use authenticated session
                logger.info("Google Sheets authenticated")
                return True
            except Exception as e:
                logger.error(f"Google authentication failed: {e}")
                logger.info("For local use, set GOOGLE_APPLICATION_CREDENTIALS environment variable")
                return False
                
        except Exception as e:
            logger.error(f"Error initializing Sheets: {e}")
            return False
    
    def sync_to_sheets(self, sheet_id: str) -> bool:
        """
        Sync poll data to Google Sheet
        
        Args:
            sheet_id: Google Sheet ID or URL
        
        Returns:
            True if sync successful
        """
        try:
            if not self.gs or not HAS_COLAB:
                logger.warning("Sheets not configured or gspread unavailable")
                return False
            
            # Get all votes from Excel
            votes = excel_manager.get_all_votes()
            if not votes:
                logger.warning("No votes to sync")
                return False
            
            # Open sheet
            sheet = self.gs.open_by_key(sheet_id)
            worksheet = sheet.get_worksheet(0)
            
            # Prepare headers
            headers = ["Timestamp", "Username", "User_ID", "Question", "Choice", "Poll_ID"]
            
            # Convert votes to list format
            data = [headers]
            for vote in votes:
                row = [
                    vote.get('Timestamp', ''),
                    vote.get('Username', ''),
                    vote.get('User_ID', ''),
                    vote.get('Question', ''),
                    vote.get('Choice', ''),
                    vote.get('Poll_ID', '')
                ]
                data.append(row)
            
            # Clear and update worksheet
            worksheet.clear()
            worksheet.update(data)
            
            logger.info(f"Synced {len(votes)} votes to Google Sheet")
            return True
            
        except Exception as e:
            logger.error(f"Error syncing to Sheets: {e}")
            return False
    
    def create_summary_sheet(self, sheet_id: str) -> bool:
        """Create a summary sheet with poll statistics"""
        try:
            if not self.gs or not HAS_COLAB:
                return False
            
            sheet = self.gs.open_by_key(sheet_id)
            
            # Add summary worksheet if not exists
            try:
                summary_ws = sheet.worksheet("Summary")
            except gspread.exceptions.WorksheetNotFound:
                summary_ws = sheet.add_worksheet(title="Summary", rows=100, cols=5)
            
            # Get summary data
            summary = excel_manager.get_summary_by_question()
            
            if not summary:
                logger.warning("No summary data available")
                return False
            
            # Build summary data
            data = [["Question", "Total Votes", "Choice", "Count", "Percentage"]]
            
            for question, stats in summary.items():
                choices = stats.get('Choice', {})
                total = stats.get('Total_Votes', 0)
                
                first_choice = True
                for choice, count in choices.items():
                    percentage = (count / total * 100) if total > 0 else 0
                    data.append([
                        question if first_choice else "",
                        total if first_choice else "",
                        choice,
                        count,
                        f"{percentage:.1f}%"
                    ])
                    first_choice = False
            
            # Update summary sheet
            summary_ws.clear()
            summary_ws.update(data)
            
            logger.info("Summary sheet created/updated")
            return True
            
        except Exception as e:
            logger.error(f"Error creating summary sheet: {e}")
            return False
    
    def prepare_data_for_colab(self) -> Dict:
        """
        Prepare Excel data in format suitable for Colab
        
        Returns:
            JSON-serializable data structure
        """
        try:
            all_votes = excel_manager.get_all_votes()
            summary = excel_manager.get_summary_by_question()
            
            prepared_data = {
                'timestamp': datetime.now().isoformat(),
                'total_votes': len(all_votes),
                'votes': all_votes,
                'summary': summary,
                'export_format': 'json'
            }
            
            logger.info(f"Data prepared for Colab: {len(all_votes)} votes")
            return prepared_data
        except Exception as e:
            logger.error(f"Error preparing data for Colab: {e}")
            return {}
    
    def save_data_snapshot(self, filename: str = "colab_snapshot.json") -> Optional[str]:
        """Save current data as JSON snapshot for Colab"""
        try:
            data = self.prepare_data_for_colab()
            
            if not data:
                return None
            
            snapshot_path = Path(filename)
            with open(snapshot_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.info(f"Data snapshot saved to {snapshot_path}")
            return str(snapshot_path)
        except Exception as e:
            logger.error(f"Error saving snapshot: {e}")
            return None
    
    def create_colab_script(self) -> str:
        """Generate a Colab notebook script template for analysis"""
        script = '''
# Bridge 2026 Data Analysis Notebook
# This notebook analyzes feedback data from Bridge 2026 Discord bot

import pandas as pd
import json
from collections import Counter
import matplotlib.pyplot as plt
import numpy as np

# =============================================================================
# DATA LOADING
# =============================================================================

# Option 1: From JSON file
# with open('colab_snapshot.json') as f:
#     data = json.load(f)

# Option 2: From API endpoint (if running locally)
# import requests
# response = requests.get('http://localhost:5000/api/votes/all')
# data = {'votes': response.json()['votes']}

# Option 3: Mount Google Drive and sync files
# from google.colab import drive
# drive.mount('/content/drive')
# df = pd.read_csv('/content/drive/MyDrive/responses.xlsx')

# =============================================================================
# DATA ANALYSIS FUNCTIONS
# =============================================================================

def analyze_poll_results(votes_data):
    """Analyze poll results by choice and question"""
    if not votes_data:
        print("No vote data available")
        return None
    
    df = pd.DataFrame(votes_data)
    
    # Group by question and choice
    results = df.groupby(['Question', 'Choice']).size().unstack(fill_value=0)
    return results

def identify_trends(votes_data):
    """Identify voting trends and patterns"""
    if not votes_data:
        return {}
    
    df = pd.DataFrame(votes_data)
    
    # Most popular choice
    choice_counts = Counter(df['Choice'])
    popular = choice_counts.most_common(3)
    
    # Voter participation
    unique_voters = df['User_ID'].nunique()
    total_votes = len(df)
    
    return {
        'most_popular': popular,
        'unique_voters': unique_voters,
        'total_votes': total_votes,
        'engagement_rate': (unique_voters / total_votes * 100) if total_votes > 0 else 0
    }

def generate_report(summary_data):
    """Generate formatted report of feedback summary"""
    print("=" * 70)
    print("Bridge 2026 Feedback Analysis Report")
    print("=" * 70)
    
    if not summary_data:
        print("No summary data available")
        return
    
    for question, stats in summary_data.items():
        print(f"\\nQuestion: {question}")
        print(f"  Total Votes: {stats.get('Total_Votes', 0)}")
        choices = stats.get('Choice', {})
        for choice, count in sorted(choices.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / stats.get('Total_Votes', 1) * 100)
            print(f"    - {choice}: {count} ({percentage:.1f}%)")

def create_visualizations(votes_data):
    """Create charts and visualizations"""
    if not votes_data:
        print("No data to visualize")
        return
    
    df = pd.DataFrame(votes_data)
    
    # Group votes by question
    questions = df['Question'].unique()
    
    fig, axes = plt.subplots(len(questions), 1, figsize=(12, 4*len(questions)))
    if len(questions) == 1:
        axes = [axes]
    
    for idx, question in enumerate(questions):
        question_data = df[df['Question'] == question]
        choice_counts = question_data['Choice'].value_counts()
        
        axes[idx].bar(choice_counts.index, choice_counts.values, color='skyblue', edgecolor='navy')
        axes[idx].set_title(f'Poll: {question}')
        axes[idx].set_ylabel('Number of Votes')
        axes[idx].set_xlabel('Choice')
        axes[idx].grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.show()

# =============================================================================
# MAIN ANALYSIS
# =============================================================================

# Uncomment and modify the functions below to perform analysis

# if 'data' in locals() and 'votes' in data:
#     print("\\n1. POLL RESULTS")
#     results = analyze_poll_results(data['votes'])
#     print(results)
#     
#     print("\\n2. VOTING TRENDS")
#     trends = identify_trends(data['votes'])
#     print(f"Total Votes: {trends['total_votes']}")
#     print(f"Unique Voters: {trends['unique_voters']}")
#     print(f"Engagement Rate: {trends['engagement_rate']:.1f}%")
#     print(f"Most Popular: {trends['most_popular']}")
#     
#     print("\\n3. DETAILED REPORT")
#     if 'summary' in data:
#         generate_report(data['summary'])
#     
#     print("\\n4. VISUALIZATIONS")
#     create_visualizations(data['votes'])
'''
        return script
    
    def get_setup_instructions(self) -> Dict:
        """Get setup instructions for Colab integration"""
        return {
            'step_1': 'Create a Google Colab notebook at https://colab.research.google.com',
            'step_2': 'Install required packages: pip install gspread google-auth-oauthlib',
            'step_3': 'Authenticate with Google: from google.colab import auth; auth.authenticate_user()',
            'step_4': 'Download colab_snapshot.json or set up API endpoint',
            'step_5': 'Use the provided script template to analyze data',
            'data_sync_options': [
                'Option A: Download CSV from dashboard export',
                'Option B: Call API endpoint from Colab',
                'Option C: Mount Google Drive and sync files',
                'Option D: Direct Google Sheets sync'
            ],
            'security_note': 'Never hardcode credentials in notebooks. Use Google Auth.',
            'sheets_integration': 'Set GOOGLE_SHEETS_ID environment variable for auto-sync'
        }

# Initialize global Colab integration
colab_integration = ColabIntegration()
