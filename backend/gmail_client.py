"""
Optional Gmail client stub for LinkedIn alerts.

If you plan to use Gmail API, configure OAuth and implement list_messages() to
return raw email payloads that can be fed to linkedin_email_ingest.parse_eml.
"""

def list_messages(config: dict):
    raise NotImplementedError("Gmail API is not configured in this project.")
