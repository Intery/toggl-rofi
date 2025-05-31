from typing import Optional
import re

from toggl_track import Project, Tag, TrackClient

entry_pattern = re.compile(
    r"(?P<desc>[^\@]*) \s* (?:\@(?P<proj>[^\#]*)) \s* (?P<tags>\#.*)?",
    re.VERBOSE | re.MULTILINE | re.UNICODE
)

class ParsedEntry:
    def __init__(self, original: str, desc: Optional[str], project: Optional[str], tags: list[str] = []):
        self.original = original
        self.desc = desc
        self.project = project
        self.tags = tags

    def format_for_edit(self):
        parts = []
        parts.append(self.desc)
        if project := self.project:
            parts.append(f"@{project}")

        if self.tags:
            tagstr = ' '.join(f"#{tag}" for tag in self.tags)
            parts.append(tagstr)

        return '    '.join(parts)


class RofiTrackClient(TrackClient):
    def parse_entry(self, userstr: str) -> ParsedEntry | None:
        match = re.match(entry_pattern, userstr)
        if match:
            description = match['desc'].strip()
            pname = match['proj'].strip().lower()
            tags = (tag.strip('# ') for tag in (match['tags'] or '').split('#'))
            tags = [tag for tag in tags if tag]
            return ParsedEntry(userstr, description, pname, tags)
        else:
            return None

    def get_project_by_name(self, project_name: str) -> Project | None:
        matching = (
            p for p in self.state.projects.values() if p.name.lower() == project_name.lower()
        )
        return next(matching, None)

    def get_tag_by_name(self, tagstr: str) -> Tag | None:
        tag = next(
            (tag for tag in self.state.tags.values() if tag.name.lower() == tagstr.lower()),
            None
        )
        return tag
