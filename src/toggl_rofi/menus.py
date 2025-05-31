from collections import defaultdict, namedtuple
from dataclasses import dataclass
from enum import Enum
import re
from typing import NamedTuple
import datetime as dt
from datetime import datetime
from operator import itemgetter

import pytz
from toggl_track import Optional, TimeEntry
from toggl_track.lib import utc_now
from client import ParsedEntry, RofiTrackClient
from rofi import MenuItem, Menu
from lib import format_duration, pango_escape
from editor import EditMenu


class EntryItem(MenuItem):
    def __init__(self, text, entry: TimeEntry, **kwargs):
        super().__init__(text, **kwargs)
        self.entry = entry

    def format_for_edit(self):
        entry = self.entry
        parts = []
        parts.append(entry.description)
        if project := entry.project:
            parts.append(f"@{project.name}")

        if entry.tags:
            tagstr = ' '.join(f"#{tag}" for tag in entry.tags)
            parts.append(tagstr)

        return '    '.join(parts)


class CustomMenu(Menu):
    def __init__(self, client: RofiTrackClient, keymap={}, **kwargs):
        kwargs.setdefault('markup_rows', True)
        kwargs.setdefault('case_insensitive', True)
        kwargs.setdefault('matching', 'regex')
        super().__init__(**kwargs)
        self.keymap = keymap

        self.client = client

    def make_items(self):
        # Testing for project acmpl
        items = []
        for project in self.client.state.projects.values():
            pname = project.name
            pcolour = project.colour
            esc_pname = pango_escape(pname)
            text = f"@<span color=\"{pcolour}\">{esc_pname:<}</span>"
            item = MenuItem(text)
            items.append(item)
        # TODO: Make these nonselectable
        return items

    def run(self):
        ...


class TrackMenu(Menu):
    Keys = Enum('TrackMenuKeys', ('EDIT', 'HELP', 'REFRESH'))
    keys = list(Keys)
    default_keymap = {
        Keys.EDIT: 'Alt+Meta+Return',
        Keys.HELP: 'Alt+Meta+h',
        Keys.REFRESH: 'Alt+Meta+r',
    }

    def __init__(self, client: RofiTrackClient, keymap={}, **kwargs):
        kwargs.setdefault('markup_rows', True)
        kwargs.setdefault('case_insensitive', True)
        kwargs.setdefault('matching', 'fuzzy')
        kwargs.setdefault('tokenize', True)
        super().__init__(**kwargs)
        self.keymap = self.default_keymap | keymap

        self.client = client
        self.entries: list[TimeEntry] = []
        # TODO: Add this to configuration
        self.timezone = pytz.timezone(client.profile.timezone or 'utc')

    def make_items(self, entries):
        tz = self.timezone

        desc_width = max(
            (len(e.description or 'No Description') for e in entries),
            default=0
        )
        proj_width = max(
            (len(e.project.name if e.project else 'No Project') for e in entries),
            default=0
        ) + 5

        dates = set()
        items = {}
        for i, entry in enumerate(reversed(entries)):
            i = len(entries) - i - 1
            desc = pango_escape(entry.description or "No description")

            date_str = entry.start.astimezone(tz).date()
            if date_str not in dates:
                dates.add(date_str)
            else:
                date_str = ""

            start_str = entry.start.astimezone(tz).strftime('%H:%M')
            stop_str = entry.stop.astimezone(tz).strftime('%H:%M') if entry.stop else 'NOW  '
            dur = format_duration(entry.actual_duration)

            parts = []
            parts.append(f"<span color=\"gray\">{i:>2}. </span>")
            parts.append(f"{desc:<{desc_width}}")
            if project := entry.project:
                pname = project.name
                pcolour = project.colour
                esc_pname = pango_escape(pname)
                pfield = proj_width + len(esc_pname) - len(pname)
                parts.append(
                    f" @<span color=\"{pcolour}\">{esc_pname:<{pfield}}</span>"
                )
            parts.append(
                f"{pango_escape(str(date_str)):<10}  {start_str} - {stop_str} ({dur})"
            )

            text = ''.join(parts)
            item = EntryItem(text, entry)
            items[entry.id] = item
        return items

    def make_mini_items(self):
        items = []
        for project in self.client.state.projects.values():
            pname = project.name
            pcolour = project.colour
            esc_pname = pango_escape(pname)
            text = f"@<span color=\"{pcolour}\">{esc_pname:<}</span>"
            item = MenuItem(text, permanent=True)
            items.append(item)
        # TODO: Make these nonselectable
        return items

    def make_header(self):
        tz = self.timezone
        start_of_day = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)

        proj_times = defaultdict(int)
        proj_index = {}
        for entry in reversed(self.entries):
            print(entry)
            if entry.stop and entry.stop < start_of_day:
                break 
            elif entry.start < start_of_day:
                contributes = entry.actual_duration - (start_of_day - entry.start).total_seconds()
            else:
                contributes = entry.actual_duration
            proj_times[entry.project_id] += int(contributes)
            if entry.project_id is not None:
                proj_index[entry.project_id] = entry.project

        lines = []
        for pid, dur in sorted(list(proj_times.items()), key=itemgetter(1), reverse=True):
            project = proj_index.get(pid)
            if project is None:
                pname = "No Project"
                pcolour = "#000000"
            else:
                pname = project.name 
                pcolour = project.colour
            esc_pname = pango_escape(pname)
            pname_col = f"<span color=\'{pcolour}\'>{esc_pname}</span>"
            print(pname_col)
            dur_str = format_duration(dur)
            lines.append(f"<b>{dur_str}</b> -- {pname_col}")
        if lines:
            header = '\n'.join(lines)
        else:
            header = "<i>No time tracked today</i>"
        return header

    async def run(self):
        entries = self.entries = sorted(self.client.state.time_entries.values(), key=lambda e: e.start)
        self.message = self.make_header()

        await self.display()
        items = self.make_items(entries)
        await self.write_items(*items.values())

        resp = await self.read()
        print(resp)
        print(resp.code)

        if resp.code >= 10:
            key = self.keys[resp.code - 10]
        else:
            key = None

        if resp.text:
            text = resp.text.decode().strip()
            # Find item matching this text, if it exists
            selected_item = next(
                (item for item in items.values() if item.text == text),
                None
            )
            if selected_item:
                parsed = None
            else:
                parsed = self.client.parse_entry(text)
                if parsed is None:
                    # TODO: Error menu/message
                    raise ValueError("Couldn't parse provided input.")
        else:
            selected_item = None
            parsed = None

        if key is self.Keys.EDIT:
            # Run edit menu
            # TODO: make separate menu
            if selected_item:
                entry = self.client.parse_entry(selected_item.format_for_edit())
            else:
                entry = None
            menu = EditMenu(self.client, entry=entry)
            await menu.run()
            # if selected_item:
            #     self.filter = selected_item.format_for_edit()
            #     await self.run()
        elif key is self.Keys.HELP:
            # Show help message
            ...
        elif key is self.Keys.REFRESH:
            # Refresh entries
            # Set filter text to custom entry, if it exists
            # Rerun
            ...
        else:
            # Start/Stop/Continue based on text given
            if selected_item is not None:
                selected_entry = selected_item.entry
                if selected_entry.running:
                    print("Stopping!")
                    await selected_entry.stop_entry()
                else:
                    await selected_entry.continue_entry()
            elif parsed is not None:
                # TODO: Show errors if we can't find project or tag
                projectid = None
                if parsed.project:
                    project = self.client.get_project_by_name(parsed.project)
                    if project:
                        projectid = project.id

                tag_ids = []
                for tagstr in parsed.tags:
                    tag = self.client.get_tag_by_name(tagstr)
                    if tag:
                        tag_ids.append(tag.id)

                await self.client.start_entry(
                    workspace_id=self.client.default_workspace.id,
                    description=parsed.desc,
                    start=utc_now(),
                    project_id=projectid,
                    tag_ids=tag_ids
                )

            # Show confirmation/error?
            # TODO: Better fetch methods for names?
            ...
