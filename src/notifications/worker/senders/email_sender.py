import aiosmtplib
from email.mime.text import MIMEText

class EmailSender:
    def __init__(self, host: str, port: int, sender: str):
        self.host = host
        self.port = port
        self.sender = sender

    async def send(self, to: str, subject: str, body: str) -> None:
        """Send an email via local SMTP (Mailpit)."""

        msg = MIMEText(body, "html")
        msg["Subject"] = subject
        msg["From"] = self.sender
        msg["To"] = to

        await aiosmtplib.send(
            msg,
            hostname=self.host,
            port=self.port,
            sender=self.sender,
            recipients=[to],
        )
