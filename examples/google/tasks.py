import arrow

import taskhawk


@taskhawk.task
def send_email(to: str, subject: str, from_email: str = None, metadata: taskhawk.Metadata = None) -> None:
    print(
        f"Received send email task with id: {metadata.id}, request_id: {metadata.headers['request_id']}, "
        f"to: {to}, from_email: {from_email} subject: {subject}, time: {arrow.now()}"
    )
