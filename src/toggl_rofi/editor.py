"""
Edit and custom-create menus for toggl-rofi.

It doesn't look like we can fit the acmpl into one menu, as nice as that would be.
Unless we actually write a mode for rofi. 
No combination of row operations and matching modes will let us
show the list of matching projects when we start typing @,
rofi is meant for matching the other way.

Accordingly, for building a new entry the EditMenu should have explicit options:
    - Description: ...
    - Project: ...
    - Tags: ...
    - Start: ...
    - End: ...
    - Confirm and Create/Edit (autoselected)
When these options are selected, it opens a new menu, with acmpl for those options.
Tags can even have multi-select like it should!
When *that* is confirmed, the option gets updated in the editor.
The filter text is remembered, or rather, re-parsed and has the provided option
replaced. 
Project and tags could also have a special option 'New Project' and 'New Tag'
for creation...
"""
from toggl_track.lib import utc_now

from .client import RofiTrackClient, ParsedEntry
from .rofi import MenuItem, Menu
from .lib import pango_escape


class EditMenu(Menu):
    def __init__(self, client: RofiTrackClient, entry: ParsedEntry | None = None, **kwargs):
        kwargs.setdefault('markup_rows', True)
        kwargs.setdefault('format', 'f')
        super().__init__(**kwargs)

        self.client = client 
        self.entry: ParsedEntry = entry if entry is not None else ParsedEntry('', desc=None, project=None)
        self.filter = entry.format_for_edit()

    async def do_edit_desc(self):
        ...

    async def do_edit_project(self):
        ...

    async def do_edit_tags(self):
        ...

    async def do_edit_start(self):
        ...

    async def do_edit_stop(self):
        ...

    async def do_confirm(self):
        # Convert ParsedEntry to data
        # Error if fields don't exist 
        # Edit or start or add entry depending
        parsed = self.entry
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

    async def run(self):
        items = []
        # Build the items 
        # Make sure confirm is auto-selected
        # Display menu 
        # Write items 
        # Handle selections
        if self.entry.project:
            project = self.client.get_project_by_name(self.entry.project)
            if project:
                pname = project.name
                pcolour = project.colour
            else:
                pname = f"{self.entry.project} (Unknown Project)"
                pcolour = "#FA1111"
            pname = pango_escape(pname)
            pfield = f"@<span color=\"{pcolour}\">{pname}</span>"
        else:
            pfield = "<i>No Project</i>"

        if self.entry.tags:
            tags = []
            for tagstr in self.entry.tags:
                tag = self.client.get_tag_by_name(tagstr)
                if tag:
                    tags.append('#'+tag.name)
            tfield = f"@<span color='grey'>{' '.join(tags)}</span>"
        else:
            tfield = "<i>No Tags</i>"

        table = [
            ("Description:", self.entry.desc or ''),
            ("Project:", pfield),
            ("Tags:", tfield)
        ]

        items = []
        keyfield = max(len(key) for key, _ in table)
        for key, value in table:
            text = f"<b>{key:<{keyfield}}\t\t {value}</b>"
            item = MenuItem(text, permanent=True)
            items.append(item)

        items.append(
            MenuItem("<b>Confirm and Start</b>", permanent=True, )
        )
        
        await self.display()
        await self.write_items(*items)
        resp = await self.read()

        if resp.text:
            text = resp.text.decode().strip()
            parsed = self.client.parse_entry(text)
            if parsed is None:
                raise ValueError("Couldn't parse provided input")
            self.entry = parsed 
            await self.do_confirm()
            # # Find item matching this text, if it exists
            # if text == items[0].text:
            #     # Description 
            #     await self.do_edit_desc()
            # elif text == items[1].text:
            #     await self.do_edit_project()
            # elif text == items[2].text:
            #     await self.do_edit_tags()
            # else:
            #     if text == items[3].text:
            #         parsed = self.entry
            #     else:
            #         parsed = self.client.parse_entry(text)
            #         if parsed is None:
            #             # TODO: Error menu/message
            #             raise ValueError("Couldn't parse provided input.")
            #         self.entry = parsed
            #     await self.do_confirm()
