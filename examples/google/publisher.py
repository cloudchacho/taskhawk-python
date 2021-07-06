import os
import uuid

import arrow

os.environ.setdefault("SETTINGS_MODULE", "example_settings")


from tasks import send_email  # noqa


def main():
    request_id = str(uuid.uuid4())
    to = 'hello@example.com'
    send_email.with_headers(request_id=request_id).dispatch(to, 'Hi there!', from_email='example@spammer.com')
    print(f"Dispatched task {send_email.task.name} with to: {to}, request id: {request_id}, time: {arrow.now()}")


if __name__ == "__main__":
    main()
