"""
Account records and conversation repository for ResolveIQ.
"""
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from resolveiq.config import ACCOUNTS_DIR, CONVERSATIONS_DIR


class AccountRepository:
    """Manages access to customer account records and customer conversations."""

    def __init__(self, accounts_dir: Path = ACCOUNTS_DIR, convs_dir: Path = CONVERSATIONS_DIR):
        self.accounts_dir = accounts_dir
        self.convs_dir = convs_dir
        self._accounts: Dict[str, Dict[str, Any]] = {}
        self._conversations: Dict[str, Dict[str, Any]] = {}
        self.reload()

    def reload(self) -> None:
        """Reload all account records and conversations from disk."""
        self._accounts.clear()
        self._conversations.clear()

        if self.accounts_dir.exists():
            for filepath in self.accounts_dir.glob("*.json"):
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        acc_id = data.get("account_id")
                        if acc_id:
                            self._accounts[acc_id] = data
                except Exception as e:
                    print(f"Error loading account {filepath}: {e}")

        if self.convs_dir.exists():
            for filepath in self.convs_dir.glob("*.json"):
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        conv_id = data.get("conversation_id")
                        if conv_id:
                            self._conversations[conv_id] = data
                except Exception as e:
                    print(f"Error loading conversation {filepath}: {e}")

    def get_account(self, account_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve account record by Account ID."""
        return self._accounts.get(account_id)

    def list_accounts(self) -> List[Dict[str, Any]]:
        """Return list of all account records sorted by ID."""
        return sorted(list(self._accounts.values()), key=lambda x: x.get("account_id", ""))

    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve conversation record by Conversation ID."""
        return self._conversations.get(conversation_id)

    def list_conversations(self) -> List[Dict[str, Any]]:
        """Return list of all sample conversations sorted by ID."""
        return sorted(list(self._conversations.values()), key=lambda x: x.get("conversation_id", ""))


account_repo = AccountRepository()
