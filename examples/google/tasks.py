import arrow

import taskhawk


@taskhawk.task
def send_email(to: str, subject: str, from_email: str = None, metadata: taskhawk.Metadata = None) -> None:
    latency_s = (arrow.now() - metadata.provider_metadata.publish_time).total_seconds()
    print(
        f"Received send email task with id: {metadata.id}, request_id: {metadata.headers['request_id']}, "
        f"to: {to}, from_email: {from_email} subject: {subject}, time: {arrow.now()}, "
        f'publish time: {metadata.provider_metadata.publish_time}, '
        f'latency seconds: {latency_s} delivery_attempt: {metadata.provider_metadata.delivery_attempt}'
    )
