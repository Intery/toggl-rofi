import asyncio
import logging
import toml
import os
from client import RofiTrackClient
from menus import TrackMenu
from rofi import Menu
from platformdirs import PlatformDirs


logging.getLogger(__name__).setLevel(logging.DEBUG)

DEFAULTCONFIG = """
[toggl]
apikey = ""
"""


async def main():
    dirs = PlatformDirs('togglpy', 'Interitio')
    configdir = dirs.user_config_dir
    configpath = os.path.join(configdir, 'config.toml')
    if not os.path.exists(configpath):
        os.makedirs(configdir)
        with open(configpath, 'w') as f:
            f.write(DEFAULTCONFIG)
        
    config = toml.load(configpath)

    if not config['toggl']['apikey']:
        error_menu = Menu(message=f"No API key set!\nPlease add your toggl API key to the configuration file:\n{configpath}")
        await error_menu.display()
        return
    try:
        client = RofiTrackClient()
        await client.login(APIKey=config['toggl']['apikey'])
        await client.sync()
    except Exception as e:
        error_menu = Menu(message=f"Could not login!\n{e}")
        await error_menu.display()
        raise

    logging.info(f"Logged in as {client.profile.id} in {client.profile.timezone}")
    logging.info(f"{len(client.state.projects)} Projects, {len(client.state.time_entries)} Time Entries")
    # print(f"Longest project: {max((len(p.name) for p in client.state.projects.values()), default=0)}")
    # print(f"Longest entry: {max((len(e.description) for e in client.state.time_entries.values()), default=0)}")

    menu = TrackMenu(client)
    await menu.run()


    await client.http.session.close()


if __name__ == '__main__':
    asyncio.run(main())
