import logging

import taskhawk


def _send_email(
    to: str, subject: str, from_email: str = None, headers: dict = None, metadata: taskhawk.Metadata = None
) -> None:
    # inner fn to help w mocking
    pass


@taskhawk.task
def send_email(
    to: str, subject: str, from_email: str = None, headers: dict = None, metadata: taskhawk.Metadata = None
) -> None:
    logging.info(f"Going to send email for request: {headers['request_id']} with id: {metadata.id}")
    _send_email(to, subject, from_email=from_email, headers=headers, metadata=metadata)
    logging.info(f"Sent email to {to}, with subject: {subject}, from: {from_email or 'default@email.com'}")
