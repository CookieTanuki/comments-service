from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def send_comment_event(data):
    channel_layer = get_channel_layer()

    async_to_sync(channel_layer.group_send)(
        "comments",
        {
            "type": "comment_event",
            "data": data,
        }
    )
