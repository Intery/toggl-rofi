#!/bin/python3
import re
import subprocess
import datetime
from collections import defaultdict

import pendulum
from toggl import api



input_regex = r"(?P<desc>[^\@]*) \s* (?:\@(?P<proj>[^\#]*)) \s* (?P<tags>\#.*)?"


tags = None
tag_map = None
projects = api.Project.objects.all()
pnames = {project.id: (project.name, project.hex_color) for project in projects}
pname_map = {project.name.lower(): project for project in projects}
tz = api.User.objects.current_user().timezone


def init_tags():
    global tags
    global tag_map
    if tags is None:
        tags = api.Tag.objects.all()
        tag_map = {tag.name.lower(): tag for tag in tags}


def run_blocking(args, input=None):
    kwargs = {}
    kwargs['stdout'] = subprocess.PIPE
    kwargs['universal_newlines'] = True

    result = subprocess.run(args, input=input, **kwargs)
    return result.returncode, result.stdout


def pango_escape(str):
    return str.translate(
        {38: '&amp;'}
    ).translate({
        34: '&quot;',
        39: '&apos;',
        60: '&lt;',
        62: '&gt;'
    })


def format_entries(entry_list):
    max_desc = max(len(entry.description) for entry in entries)
    max_project = max(
        len(pnames.get(entry.pid)[0] if hasattr(entry, 'pid') else "None")
        for entry in entry_list
    )
    project_field = max_project + 5

    dates = set()
    entry_strs = []
    for i, entry in enumerate(reversed(entry_list)):
        i = len(entry_list) - i - 1
        desc = pango_escape(entry.description or "No description")
        pname, pcolour = pnames.get(entry.pid) if hasattr(entry, 'pid') else ("None", "#000000")
        esc_pname = pango_escape(pname)
        p_field = project_field + (len(esc_pname) - len(pname))

        date_str = entry.start.in_tz(tz).to_date_string()
        if date_str not in dates:
            dates.add(date_str)
        else:
            date_str = ""

        start_str = entry.start.in_tz(tz).strftime("%H:%M")
        stop_str = entry.stop.in_tz(tz).strftime("%H:%M") if not entry.is_running else 'NOW  '
        dur = api.models.format_duration(entry.duration)
        dur_str = ':'.join(dur.split(':')[:2])

        entry_str = []
        entry_str.append(f"<span color=\"grey\">{i:>2}. </span>")
        entry_str.append(f"{desc:<{max_desc}}")
        entry_str.append(" @")
        if pname:
            pcolour = pcolour or '#000000'
            entry_str.append(
                f"<span color=\"{pcolour}\">{esc_pname:<{p_field}}</span>"
            )
        entry_str.append(
            f"{date_str:<10}  {start_str} - {stop_str} ({dur_str})"
        )

        entry_strs.append(''.join(entry_str))

    return list(reversed(entry_strs))


def dialog(prompt, options, header="", join_char='\n', filter="", keys=[]):
    args = ['rofi', '-dmenu', '-i', '-p', prompt, '-filter', filter, '-format', 's', '-markup-rows', '-matching fuzzy']
    if header:
        args.extend(['-mesg', header])
    if keys:
        for i, k in enumerate(keys):
            args.extend((f"-kb-custom-{i+1}", k))

    option_str = join_char.join(options)
    code, stdout = run_blocking(args, input=option_str)
    return code, stdout


def entry_to_input(entry):
    tagstr = ' '.join(f"#{tag}" for tag in entry.tags) if hasattr(entry, 'tags') else ""
    return (
        f"{entry.description}  @{entry.project.name}  {tagstr}"
    )


def parse_input_fields(userstr):
    """
    Description @Project here #Tag1 #Tag2 -- 10/10/2010 10:11 - 10:11
    """
    match = re.match(input_regex, userstr, re.VERBOSE | re.MULTILINE | re.UNICODE)
    if match:
        description = match['desc'].strip()
        pname = match['proj'].strip().lower()

        project = pname_map.get(pname, None)
        if match['tags']:
            tagstr = match['tags'].strip('# ')
            init_tags()
            tags = [tag_map.get(tag.strip().lower(), None) for tag in tagstr.split('#')]
            tags = [tag.name for tag in tags if tag]
        else:
            tags = []

        return {
            "description": description,
            "project": project,
            "tags": tags
        }


def gen_header(entries):
    proj_times = defaultdict(int)
    for entry in entries:
        if entry.start < pendulum.today(tz):
            break
        proj_times[entry.pid if hasattr(entry, "pid") else 0] += entry.duration

    lines = []
    for pid, dur in sorted(list(proj_times.items()), key=lambda p: p[1], reverse=True):
        pname, pcolour = pnames.get(pid, ("No Project", "#000000"))
        esc_pname = pango_escape(pname)
        pname_col = f"<span color=\"{pcolour}\">{esc_pname}</span>"

        dur_str = api.models.format_duration(dur)
        dur_str = ':'.join(dur_str.split(':')[:2])
        lines.append(f"<b>{dur_str}</b> -- {pname_col}")
    return '\n'.join(lines)


if __name__ == "__main__":
    entries = api.TimeEntry.objects.all(order='start')
    formatted = format_entries(entries)
    header = gen_header(entries)
    code, stdout = dialog("Entry", formatted, header=header, keys=["Alt+Return"])
    if stdout.startswith('<span color'):
        index = int(stdout.partition('>')[2].partition('<')[0].strip(' .'))
        entry = entries[index]
        if entry.is_running:
            entry.stop_and_save()
        elif code == 0:
            entry.continue_and_save()
        elif code == 10:
            # entry.continue_and_save()
            entry_str = entry_to_input(entry)
            code, stdout = dialog("Edit and Start", "", filter=entry_str)
            if code == 0:
                args = parse_input_fields(stdout)
                entry = api.TimeEntry.start_and_save(**args)
                print(entry_to_input(entry))
    else:
        args = parse_input_fields(stdout)
        entry = api.TimeEntry.start_and_save(**args)
        print(entry_to_input(entry))
    print(code, stdout)
