"""Purpose: local operator sign-in gate using a salted password hash.

Inputs: operator username/password entered by the user.
Outputs: access approval or a first-run local account in the user app-data folder.
Connection: main.py shows this dialog before constructing the mission dashboard.
This is a local UI gate; it does not encrypt mission files or protect the PC.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from pathlib import Path

from PySide6.QtCore import Qt, QStandardPaths
from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QVBoxLayout,
)

ITERATIONS = 310_000


def _credential_path() -> Path:
    """Resolve the OS-specific app-data location without storing passwords in the project."""
    app_data = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppLocalDataLocation
    )
    if not app_data:
        raise OSError("The operating system did not provide an application data directory.")
    path = Path(app_data)
    path.mkdir(parents=True, exist_ok=True)
    return path / "operator.json"


def _derive_hash(password: str, salt: bytes) -> str:
    """Derive a slow one-way password hash suitable for local credential storage."""
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS).hex()


class AuthDialog(QDialog):
    """Create the first local operator account or verify an existing one."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("HyperMesh AI | Operator Access")
        self.setModal(True)
        self.setMinimumWidth(440)
        self._path = _credential_path()
        self._first_run = not self._path.exists()
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        title = QLabel("CREATE OPERATOR PROFILE" if self._first_run else "OPERATOR SIGN IN")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size:20px; font-weight:800; letter-spacing:1px; color:#00FFFF;")
        layout.addWidget(title)
        message = QLabel(
            "Create a local account for this Windows user."
            if self._first_run else "Sign in to open the local mission-control workspace."
        )
        message.setWordWrap(True)
        message.setStyleSheet("color:#A9BAD0;")
        layout.addWidget(message)
        form = QFormLayout()
        self.username = QLineEdit()
        self.username.setPlaceholderText("Operator name")
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText("Password")
        form.addRow("Username", self.username)
        form.addRow("Password", self.password)
        if self._first_run:
            self.confirm = QLineEdit()
            self.confirm.setEchoMode(QLineEdit.EchoMode.Password)
            self.confirm.setPlaceholderText("Enter password again")
            form.addRow("Confirm", self.confirm)
        layout.addLayout(form)
        self.status = QLabel("")
        self.status.setStyleSheet("color:#FF9F43;")
        layout.addWidget(self.status)
        submit = QPushButton("CREATE LOCAL ACCOUNT" if self._first_run else "SIGN IN")
        submit.clicked.connect(self._submit)
        layout.addWidget(submit)
        self.password.returnPressed.connect(self._submit)
        self.setStyleSheet(
            "QDialog { background:#091326; } QLabel { background:transparent; }"
        )

    def _submit(self) -> None:
        username = self.username.text().strip()
        password = self.password.text()
        if not username or not password:
            self.status.setText("Enter both a username and password.")
            return
        if self._first_run:
            if len(password) < 10:
                self.status.setText("Use at least 10 characters for the local password.")
                return
            if password != self.confirm.text():
                self.status.setText("The passwords do not match.")
                return
            salt = secrets.token_bytes(16)
            credentials = {
                "username": username,
                "salt": salt.hex(),
                "password_hash": _derive_hash(password, salt),
                "iterations": ITERATIONS,
            }
            temporary = self._path.with_suffix(".tmp")
            temporary.write_text(json.dumps(credentials), encoding="utf-8")
            os.replace(temporary, self._path)
            self.accept()
            return

        try:
            credentials = json.loads(self._path.read_text(encoding="utf-8"))
            salt = bytes.fromhex(credentials["salt"])
            expected_hash = str(credentials["password_hash"])
            iterations = int(credentials["iterations"])
            actual_hash = hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"), salt, iterations
            ).hex()
        except (OSError, ValueError, KeyError, TypeError) as exc:
            QMessageBox.critical(self, "Credential file error", f"Could not read the local account: {exc}")
            return
        if hmac.compare_digest(actual_hash, expected_hash) and hmac.compare_digest(
            username.casefold(), str(credentials.get("username", "")).casefold()
        ):
            self.accept()
        else:
            self.status.setText("Username or password is incorrect.")
