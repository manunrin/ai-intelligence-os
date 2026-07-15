from notion_client import Client
import os

notion = Client(
    auth=os.environ["NOTION_TOKEN"]
)

me = notion.users.me()

print(me)
