import asyncio
import logging
import toml
from client import RofiTrackClient
from menus import TrackMenu


logging.getLogger(__name__).setLevel(logging.DEBUG)


async def main():
    config = toml.load('tests/config.toml')
    client = RofiTrackClient()
    await client.login(APIKey=config['toggl']['apikey'])
    await client.sync()
    logging.info(f"Logged in as {client.profile.id} in {client.profile.timezone}")
    logging.info(f"{len(client.state.projects)} Projects, {len(client.state.time_entries)} Time Entries")
    print(f"Longest project: {max((len(p.name) for p in client.state.projects.values()), default=0)}")
    print(f"Longest entry: {max((len(e.description) for e in client.state.time_entries.values()), default=0)}")

    menu = TrackMenu(client)
    await menu.run()


    await client.http.session.close()


if __name__ == '__main__':
    asyncio.run(main())
