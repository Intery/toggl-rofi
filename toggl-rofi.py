#!/bin/python3
import subprocess

from toggl import api


projects = api.Project.objects.all()
pnames = {project.id: (project.name, project.hex_color) for project in projects}


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
    max_project = 20
    project_field = max_project + 10

    dates = set()
    entry_strs = []
    for i, entry in enumerate(entry_list):
        desc = pango_escape(entry.description or "No description")
        pname, pcolour = pnames.get(entry.pid, (None, None))
        esc_pname = pango_escape(pname)
        p_field = project_field + (len(esc_pname) - len(pname))

        date_str = entry.start.to_date_string()
        if date_str not in dates:
            dates.add(date_str)
        else:
            date_str = ""

        start_str = entry.start.strftime("%H:%M")
        stop_str = entry.stop.strftime("%H:%M") if not entry.is_running else 'NOW  '
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

    return entry_strs


def dialog(prompt, options, header="", join_char='\n'):
    args = ['rofi', '-dmenu', '-i', '-p', prompt, '-format', 's', '-markup-rows']
    if header:
        args.extend(['-mesg', header])

    option_str = join_char.join(options)
    code, stdout = run_blocking(args, input=option_str)
    return code, stdout


if __name__ == "__main__":
    entries = api.TimeEntry.objects.all(order='start')
    formatted = format_entries(entries)
    code, stdout = dialog("Entry", formatted)
    if code == 0:
        if stdout.startswith('<span color'):
            index = int(stdout.partition('>')[2].partition('<')[0].strip(' .'))
            entry = entries[index]
            if entry.is_running:
                entry.stop_and_save()
            else:
                entry.continue_and_save()
    print(code, stdout)
