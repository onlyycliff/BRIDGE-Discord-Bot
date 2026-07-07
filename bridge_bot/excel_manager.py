import json
import pandas as pd
from pathlib import Path
from datetime import datetime
import threading
import logging
import shutil
import atexit
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)


class ExcelDataManager:
    """Thread-safe Excel data manager with in-memory cache and batched writes"""

    def __init__(self, file_path: str = None):
        if file_path is None:
            file_path = str(Path(__file__).resolve().parent.parent / "responses.xlsx")
        self.file_path = Path(file_path)
        self.lock = threading.RLock()
        self.main_sheet = "Poll Responses"
        self.meta_sheet = "Poll Metadata"
        self._cache: Optional[pd.DataFrame] = None
        self._meta_cache: Dict[int, Dict] = {}
        self._meta_dirty = False
        self._dirty = False
        self._flush_interval = 30
        self._backup_interval = 50
        self._vote_count = 0
        self._flush_timer: Optional[threading.Timer] = None
        self._initialize_excel()
        self._initialize_meta_sheet()
        self._load_cache()
        self._load_meta_cache()
        self._start_flush_loop()
        atexit.register(self._final_flush)

    def _initialize_excel(self) -> None:
        try:
            if not self.file_path.exists():
                df = pd.DataFrame(columns=[
                    "Timestamp", "Username", "User_ID", "Question",
                    "Choice", "Poll_ID"
                ])
                with pd.ExcelWriter(self.file_path, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name=self.main_sheet, index=False)
                logger.info(f"Excel file created at {self.file_path}")
        except Exception as e:
            logger.error(f"Error initializing Excel: {e}")

    def _initialize_meta_sheet(self) -> None:
        try:
            with pd.ExcelWriter(self.file_path, engine='openpyxl', mode='a') as writer:
                if self.meta_sheet not in writer.book.sheetnames:
                    meta_df = pd.DataFrame(columns=[
                        "Poll_ID", "Question", "Description", "Options",
                        "Channel_ID", "Message_ID", "Timestamp"
                    ])
                    meta_df.to_excel(writer, sheet_name=self.meta_sheet, index=False)
                    logger.info(f"Poll Metadata sheet created in {self.file_path}")
        except Exception:
            try:
                existing_main = pd.DataFrame()
                try:
                    existing_main = pd.read_excel(self.file_path, sheet_name=self.main_sheet)
                except Exception:
                    pass
                meta_df = pd.DataFrame(columns=[
                    "Poll_ID", "Question", "Description", "Options",
                    "Channel_ID", "Message_ID", "Timestamp"
                ])
                with pd.ExcelWriter(self.file_path, engine='openpyxl') as writer:
                    if not existing_main.empty:
                        existing_main.to_excel(writer, sheet_name=self.main_sheet, index=False)
                    meta_df.to_excel(writer, sheet_name=self.meta_sheet, index=False)
                logger.info(f"Poll Metadata sheet created (fallback mode) in {self.file_path}")
            except Exception as e:
                logger.error(f"Error initializing metadata sheet (fallback): {e}")

    def _load_meta_cache(self) -> None:
        with self.lock:
            self._meta_cache = {}
            try:
                df = pd.read_excel(self.file_path, sheet_name=self.meta_sheet)
                if not df.empty:
                    for _, row in df.iterrows():
                        raw_pid = row.get('Poll_ID')
                        if pd.isna(raw_pid):
                            continue
                        pid = int(raw_pid)
                        if pid:
                            opts_raw = row.get('Options', '[]')
                            try:
                                options = json.loads(opts_raw) if isinstance(opts_raw, str) else []
                            except (json.JSONDecodeError, TypeError):
                                options = []
                            self._meta_cache[pid] = {
                                'poll_id': pid,
                                'question': str(row.get('Question', '')) if pd.notna(row.get('Question')) else '',
                                'description': str(row.get('Description', '')) if pd.notna(row.get('Description')) else '',
                                'options': options,
                                'channel_id': int(row.get('Channel_ID', 0)) if pd.notna(row.get('Channel_ID')) else None,
                                'message_id': int(row.get('Message_ID', 0)) if pd.notna(row.get('Message_ID')) else None,
                                'timestamp': str(row.get('Timestamp', '')) if pd.notna(row.get('Timestamp')) else ''
                            }
                logger.info(f"Loaded {len(self._meta_cache)} poll metadata records")
            except Exception:
                logger.info("No existing poll metadata found, starting fresh")

    def add_poll_metadata(self, poll_id: int, question: str, options: List[str],
                          channel_id: int, message_id: int,
                          description: str = '') -> bool:
        with self.lock:
            try:
                self._meta_cache[poll_id] = {
                    'poll_id': poll_id,
                    'question': str(question),
                    'description': str(description),
                    'options': list(options),
                    'channel_id': channel_id,
                    'message_id': message_id,
                    'timestamp': str(datetime.now())
                }
                self._meta_dirty = True
                logger.info(f"Poll metadata saved for poll {poll_id}")
                return True
            except Exception as e:
                logger.error(f"Error saving poll metadata: {e}")
                return False

    def get_poll_metadata(self, poll_id: int) -> Optional[Dict]:
        with self.lock:
            return self._meta_cache.get(poll_id)

    def _load_cache(self) -> None:
        with self.lock:
            self._cache = self._read_all_data()
            logger.info(f"Loaded {len(self._cache)} records into memory cache")

    def _start_flush_loop(self) -> None:
        self._flush_timer = threading.Timer(self._flush_interval, self._flush_loop)
        self._flush_timer.daemon = True
        self._flush_timer.start()

    def _flush_all(self) -> None:
        needs_write = (self._dirty and self._cache is not None) or self._meta_dirty
        if not needs_write:
            return
        try:
            with pd.ExcelWriter(self.file_path, engine='openpyxl') as writer:
                if self._cache is not None:
                    self._cache.to_excel(writer, sheet_name=self.main_sheet, index=False)
                if self._meta_dirty and self._meta_cache:
                    meta_rows = []
                    for pid, meta in self._meta_cache.items():
                        meta_rows.append({
                            'Poll_ID': pid,
                            'Question': meta.get('question', ''),
                            'Description': meta.get('description', ''),
                            'Options': json.dumps(meta.get('options', [])),
                            'Channel_ID': meta.get('channel_id', ''),
                            'Message_ID': meta.get('message_id', ''),
                            'Timestamp': meta.get('timestamp', '')
                        })
                    meta_df = pd.DataFrame(meta_rows)
                    meta_df.to_excel(writer, sheet_name=self.meta_sheet, index=False)
            if self._dirty:
                logger.info(f"Cache flushed to Excel ({len(self._cache)} records)")
                self._dirty = False
            if self._meta_dirty:
                self._meta_dirty = False
        except Exception as e:
            logger.error(f"Error flushing to Excel: {e}")

    def _flush_loop(self) -> None:
        with self.lock:
            self._flush_all()
        self._start_flush_loop()

    def flush_now(self) -> None:
        with self.lock:
            self._flush_all()

    def _final_flush(self):
        try:
            if self._flush_timer:
                self._flush_timer.cancel()
            self.flush_now()
            logger.info("Final cache flush on shutdown")
        except Exception as e:
            logger.error(f"Error during final flush: {e}")

    def _maybe_backup(self) -> None:
        self._vote_count += 1
        if self._vote_count % self._backup_interval == 0:
            try:
                backup_path = self.file_path.with_suffix('.xlsx.bak')
                shutil.copy2(self.file_path, backup_path)
                logger.info(f"Backup created at {backup_path}")
            except Exception as e:
                logger.error(f"Error creating backup: {e}")

    def add_vote(self, username: str, user_id: int, question: str, choice: str, poll_id: int) -> bool:
        if not all([username, user_id, question, choice, poll_id]):
            logger.error("Invalid vote parameters - Missing required fields")
            return False

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

                if self._cache is not None and not self._cache.empty:
                    self._cache = pd.concat([self._cache, new_vote], ignore_index=True)
                else:
                    self._cache = new_vote

                self._dirty = True
                self._maybe_backup()
                logger.info(f"Vote recorded (cached): {username} -> {choice} for poll {poll_id}")
                return True
            except Exception as e:
                logger.error(f"Error adding vote: {e}")
                return False

    def get_poll_stats(self, poll_id: int) -> Optional[Dict]:
        with self.lock:
            try:
                if self._cache is None or self._cache.empty:
                    df = self._read_all_data()
                else:
                    df = self._cache

                if df.empty or 'Poll_ID' not in df.columns:
                    return None

                poll_data = df[df['Poll_ID'] == poll_id]
                if poll_data.empty:
                    return None

                choices = {}
                if 'Choice' in poll_data.columns:
                    choices = poll_data['Choice'].value_counts().to_dict()

                voters_by_choice = {}
                if 'Choice' in poll_data.columns and 'Username' in poll_data.columns:
                    for choice_val, group in poll_data.groupby('Choice'):
                        voters_by_choice[str(choice_val)] = group['Username'].unique().tolist()

                stats = {
                    "total_votes": len(poll_data),
                    "question": str(poll_data.iloc[0]['Question']) if 'Question' in poll_data.columns else "Unknown",
                    "choices": {str(k): int(v) for k, v in choices.items()},
                    "voters_by_choice": voters_by_choice
                }
                return stats
            except Exception as e:
                logger.error(f"Error getting poll stats: {e}", exc_info=True)
                return None

    def get_all_votes(self) -> List[Dict]:
        with self.lock:
            try:
                df = self._cache if self._cache is not None else self._read_all_data()
                if df.empty:
                    return []
                records = []
                for _, row in df.iterrows():
                    record = row.to_dict()
                    if 'Timestamp' in record and pd.notna(record['Timestamp']):
                        record['Timestamp'] = str(record['Timestamp'])
                    records.append(record)
                return records
            except Exception as e:
                logger.error(f"Error reading votes: {e}", exc_info=True)
                return []

    def _read_all_data(self) -> pd.DataFrame:
        try:
            df = pd.read_excel(self.file_path, sheet_name=self.main_sheet)
            return df
        except (ValueError, FileNotFoundError):
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
        rename_map = {
            'User': 'Username', 'Time': 'Timestamp', 'Poll ID': 'Poll_ID',
            'user': 'Username', 'time': 'Timestamp', 'poll id': 'Poll_ID'
        }
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
        df = df.dropna(how='all')
        df = df.dropna(axis=1, how='all')
        return df

    def export_to_csv(self, output_path: str = "poll_feedback.csv") -> Optional[str]:
        with self.lock:
            try:
                df = self._cache if self._cache is not None else self._read_all_data()
                if df.empty:
                    logger.warning("No data to export")
                    return None
                df.to_csv(output_path, index=False)
                logger.info(f"Data exported to {output_path}")
                return output_path
            except Exception as e:
                logger.error(f"Error exporting CSV: {e}")
                return None

    def get_all_polls(self) -> List[Dict]:
        with self.lock:
            try:
                df = self._cache if self._cache is not None else self._read_all_data()
                if df.empty or 'Poll_ID' not in df.columns:
                    return []

                polls = {}
                for _, row in df.iterrows():
                    pid = row.get('Poll_ID')
                    question = row.get('Question', 'Unknown')
                    choice = row.get('Choice', '')
                    timestamp = str(row.get('Timestamp', '')) if pd.notna(row.get('Timestamp')) else ''

                    if pd.isna(pid):
                        continue
                    pid = int(pid)

                    if pid not in polls:
                        polls[pid] = {
                            'poll_id': pid,
                            'question': str(question) if pd.notna(question) else 'Unknown',
                            'options': {},
                            'timestamp': timestamp
                        }

                    if pd.notna(choice):
                        choice_str = str(choice)
                        polls[pid]['options'][choice_str] = polls[pid]['options'].get(choice_str, 0) + 1

                result = []
                for pid, data in polls.items():
                    options_list = [
                        {'name': name, 'votes': count}
                        for name, count in data['options'].items()
                    ]
                    total_votes = sum(data['options'].values())
                    result.append({
                        'poll_id': data['poll_id'],
                        'question': data['question'],
                        'options': options_list,
                        'total_votes': total_votes,
                        'timestamp': data['timestamp']
                    })

                result.sort(key=lambda p: p['poll_id'], reverse=True)
                return result
            except Exception as e:
                logger.error(f"Error getting all polls: {e}", exc_info=True)
                return []

    def get_summary_by_question(self) -> Dict:
        with self.lock:
            try:
                df = self._cache if self._cache is not None else self._read_all_data()
                if df.empty or 'Question' not in df.columns:
                    return {}
                df = df.dropna(subset=['Question'])
                if df.empty:
                    return {}
                summary = {}
                for question, group in df.groupby('Question'):
                    if pd.isna(question) or not str(question).strip():
                        continue
                    choice_counts = {}
                    if 'Choice' in group.columns:
                        choice_counts = group['Choice'].value_counts().to_dict()
                    summary[str(question)] = {
                        'Total_Votes': len(group),
                        'choices': choice_counts
                    }
                return summary
            except Exception as e:
                logger.error(f"Error generating summary: {e}", exc_info=True)
                return {}


excel_manager = ExcelDataManager()

