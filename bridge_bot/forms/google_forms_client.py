"""Google Forms client — creates tour feedback forms via the Google Forms API."""

import base64
import json
import logging
import os

from google.oauth2 import service_account
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/forms.body",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]


def _get_credentials():
    """Load service account credentials from the GOOGLE_SERVICE_ACCOUNT_JSON env var."""
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not raw:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON env var is not set")
    try:
        info = json.loads(base64.b64decode(raw))
    except Exception as e:
        raise RuntimeError(f"Failed to decode GOOGLE_SERVICE_ACCOUNT_JSON: {e}") from e
    return service_account.Credentials.from_service_account_info(info, scopes=SCOPES)


async def create_tour_feedback_form(tour_name: str) -> dict:
    """Create a Google Form for tour feedback and return its metadata.

    Returns a dict with keys: form_url, form_edit_url, sheet_id.
    Raises RuntimeError on any Google API failure.
    """
    folder_id = os.environ.get("GOOGLE_DRIVE_FOLDER_ID")
    if not folder_id:
        raise RuntimeError("GOOGLE_DRIVE_FOLDER_ID env var is not set")

    creds = _get_credentials()

    try:
        forms_service = build("forms", "v1", credentials=creds)
        sheets_service = build("sheets", "v4", credentials=creds)
        drive_service = build("drive", "v3", credentials=creds)

        # 1. Create the form
        form_title = f"{tour_name} \u2014 Industry Tour Feedback"
        form = forms_service.forms().create(
            body={"info": {"title": form_title}}
        ).execute()
        form_id = form["formId"]
        logger.info(f"Google Form created: {form_id} ({form_title})")

        # 2. Add the four questions via batchUpdate
        requests_body = [
            {
                "createItem": {
                    "item": {
                        "title": "What industry tour did you go on?",
                        "questionItem": {
                            "question": {
                                "textQuestion": {},
                            }
                        },
                    },
                    "location": {"index": 0},
                }
            },
            {
                "updateItem": {
                    "location": {"index": 0},
                    "updateMask": "questionItem.question.textQuestion.paragraph",
                    "item": {
                        "title": "What industry tour did you go on?",
                        "questionItem": {
                            "question": {
                                "textQuestion": {
                                    "paragraph": False,
                                },
                            }
                        },
                    },
                }
            },
            {
                "createItem": {
                    "item": {
                        "title": "Rate the industry tour out of 5",
                        "questionItem": {
                            "question": {
                                "scaleQuestion": {
                                    "low": 1,
                                    "high": 5,
                                    "lowLabel": "Poor",
                                    "highLabel": "Excellent",
                                },
                            }
                        },
                    },
                    "location": {"index": 1},
                }
            },
            {
                "createItem": {
                    "item": {
                        "title": "What did you like about the tour?",
                        "questionItem": {
                            "question": {
                                "textQuestion": {
                                    "paragraph": True,
                                },
                            }
                        },
                    },
                    "location": {"index": 2},
                }
            },
            {
                "createItem": {
                    "item": {
                        "title": "What is one thing you learned about the industry?",
                        "questionItem": {
                            "question": {
                                "textQuestion": {
                                    "paragraph": True,
                                },
                            }
                        },
                    },
                    "location": {"index": 3},
                }
            },
        ]

        forms_service.forms().batchUpdate(
            formId=form_id,
            body={"requests": requests_body},
        ).execute()

        # 3. Move form to the shared folder
        drive_service.files().update(
            fileId=form_id,
            addParents=folder_id,
            removeParents="root",
            fields="id, parents",
        ).execute()

        # 4. Create a response spreadsheet
        sheet = sheets_service.spreadsheets().create(
            body={
                "properties": {"title": f"{tour_name} \u2014 Feedback Responses"},
            }
        ).execute()
        sheet_id = sheet["spreadsheetId"]

        # Move the sheet to the same folder
        drive_service.files().update(
            fileId=sheet_id,
            addParents=folder_id,
            removeParents="root",
            fields="id, parents",
        ).execute()

        form_url = f"https://docs.google.com/forms/d/{form_id}/viewform"
        form_edit_url = f"https://docs.google.com/forms/d/{form_id}/edit"

        logger.info(
            f"Tour feedback form ready: form={form_id} sheet={sheet_id} "
            f"url={form_url}"
        )

        return {
            "form_url": form_url,
            "form_edit_url": form_edit_url,
            "sheet_id": sheet_id,
        }

    except Exception as e:
        logger.error(f"Failed to create Google Form for '{tour_name}': {e}")
        raise RuntimeError(f"Google Forms API error: {e}") from e
