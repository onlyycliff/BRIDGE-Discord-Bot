# Google Colab Integration Module
# Handles secure data sync and analysis without exposing credentials

import json
import logging
from pathlib import Path
from datetime import datetime
from .excel_manager import excel_manager

try:
    import requests
except ImportError:
    requests = None

logger = logging.getLogger(__name__)

class ColabIntegration:
    """Google Colab integration for Bridge 2026 data analysis"""
    
    def __init__(self, colab_notebook_url=None, api_key=None):
        """
        Initialize Colab integration
        Args:
            colab_notebook_url: Shareable link to Colab notebook
            api_key: API key for secure communication (optional)
        """
        self.colab_url = colab_notebook_url
        self.api_key = api_key
        self.is_configured = bool(colab_notebook_url)
    
    def prepare_data_for_colab(self):
        """
        Prepare Excel data in format suitable for Colab
        Returns JSON-serializable data structure
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
            return None
    
    def save_data_snapshot(self, filename="colab_snapshot.json"):
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
    
    def create_colab_script(self):
        """Generate a Colab notebook script template for analysis"""
        script = '''
# Bridge 2026 Data Analysis Notebook
# This notebook analyzes feedback data from Bridge 2026 Discord bot

import pandas as pd
import json
from collections import Counter
import matplotlib.pyplot as plt

# Load data (replace with actual file path or API endpoint)
# Option 1: From JSON file
# with open('colab_snapshot.json') as f:
#     data = json.load(f)

# Option 2: From API endpoint
# response = requests.get('http://localhost:5000/api/excel/stats')
# data = response.json()

# Data Analysis Functions

def analyze_poll_results(votes_data):
    """Analyze poll results by choice and question"""
    df = pd.DataFrame(votes_data)
    
    # Group by question and choice
    results = df.groupby(['Question', 'Choice']).size().unstack(fill_value=0)
    return results

def identify_trends(votes_data):
    """Identify voting trends and patterns"""
    df = pd.DataFrame(votes_data)
    
    # Most popular choice
    choice_counts = Counter(df['Choice'])
    popular = choice_counts.most_common(1)
    
    # Voter participation
    unique_voters = df['User_ID'].nunique()
    total_votes = len(df)
    
    return {
        'most_popular': popular[0] if popular else None,
        'unique_voters': unique_voters,
        'total_votes': total_votes,
        'engagement_rate': unique_voters / total_votes if total_votes > 0 else 0
    }

def generate_report(summary_data):
    """Generate formatted report of feedback summary"""
    print("=" * 60)
    print("Bridge 2026 Feedback Analysis Report")
    print("=" * 60)
    
    for question, stats in summary_data.items():
        print(f"\\nQuestion: {question}")
        print(f"  Total Votes: {stats.get('Total_Votes', 0)}")
        choices = stats.get('Choice', {})
        for choice, count in choices.items():
            print(f"    - {choice}: {count}")

# Run analysis
# Uncomment the functions below to perform analysis

# analyze_results = analyze_poll_results(data['votes'])
# print(analyze_results)

# trends = identify_trends(data['votes'])
# print("\\nTrends:", trends)

# generate_report(data['summary'])

# Visualization (optional)
# plt.figure(figsize=(12, 6))
# analyze_results.T.plot(kind='bar')
# plt.title('Bridge 2026 Poll Results')
# plt.xlabel('Choice')
# plt.ylabel('Number of Votes')
# plt.legend(title='Question')
# plt.tight_layout()
# plt.show()
'''
        return script
    
    def get_setup_instructions(self):
        """Get setup instructions for Colab integration"""
        instructions = {
            'step_1': 'Create a Google Colab notebook at https://colab.research.google.com',
            'step_2': 'Install required packages: pandas, matplotlib, requests',
            'step_3': 'Set up authentication for Bridge 2026 API (TBD)',
            'step_4': 'Use the provided script template to analyze data',
            'step_5': 'Schedule notebook to run on intervals or trigger manually',
            'security_note': 'Never hardcode credentials in the notebook. Use environment variables or API keys.',
            'data_sync_options': [
                'Option A: Download CSV from dashboard export button',
                'Option B: Call API endpoint /api/excel/stats from Colab',
                'Option C: Mount Google Drive and sync data files'
            ]
        }
        return instructions

# Initialize global Colab integration (configure when ready)
colab_integration = ColabIntegration()

# Example usage:
# colab_integration.save_data_snapshot()
# print(colab_integration.get_setup_instructions())
