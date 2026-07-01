"""Alerta por email no on_failure_callback das DAGs.

Usa smtplib direto (stdlib) lendo SMTP_* do ambiente — sem acoplar a
configuracao de email do Airflow, para o callback ser reusavel entre projetos.
"""
from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from typing import Any

from include.observability import get_logger

log = get_logger("alerting")


def _send_email(subject: str, body: str) -> None:
    host = os.environ.get("SMTP_HOST")
    to_addr = os.environ.get("ALERT_EMAIL_TO")
    if not host or not to_addr:
        log.warning("SMTP_HOST/ALERT_EMAIL_TO ausentes — alerta nao enviado.")
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = os.environ.get("ALERT_EMAIL_FROM", os.environ.get("SMTP_USER", ""))
    msg["To"] = to_addr
    msg.set_content(body)

    port = int(os.environ.get("SMTP_PORT", "587"))
    with smtplib.SMTP(host, port, timeout=20) as server:
        server.starttls()
        user = os.environ.get("SMTP_USER")
        password = os.environ.get("SMTP_PASSWORD")
        if user and password:
            server.login(user, password)
        server.send_message(msg)


def email_on_failure(context: dict[str, Any]) -> None:
    """on_failure_callback do Airflow: notifica falha de task/DAG por email."""
    ti = context.get("task_instance")
    dag_id = getattr(ti, "dag_id", "?")
    task_id = getattr(ti, "task_id", "?")
    log_url = getattr(ti, "log_url", "")
    subject = f"[dbt-platform] FALHA: {dag_id}.{task_id}"
    body = (
        f"DAG: {dag_id}\nTask: {task_id}\n"
        f"Run: {context.get('run_id', '?')}\n"
        f"Exception: {context.get('exception')}\n"
        f"Logs: {log_url}\n"
    )
    try:
        _send_email(subject, body)
    except Exception:  # noqa: BLE001 — alerta nunca pode derrubar a task
        log.exception("Falha ao enviar email de alerta.")
