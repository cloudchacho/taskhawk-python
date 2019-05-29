import os


os.environ.setdefault("SETTINGS_MODULE", "example_settings")


import tasks  # noqa
from taskhawk import consumer, Priority  # noqa


def main():
    print("Starting Google PubSub consumer")
    consumer.listen_for_messages(Priority.default)


if __name__ == "__main__":
    main()
