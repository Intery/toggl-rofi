import itertools
import asyncio
from typing import Optional


class RofiResponse:
    def __init__(self, text, code, info):
        self.text = text
        self.code = code
        self.info = info

    def __repr__(self):
        return f"<RofiResponse {self.text=} {self.code=} {self.info=}>"


class MenuItem:
    def __init__(self, text,
                 icon=None,
                 meta=None,
                 nonselectable=None,
                 info=None,
                 permanent=None,
                 ):
        self.text = text
        self.icon = icon
        self.meta = meta
        self.nonselectable = nonselectable
        self.info = info 
        self.permanent = permanent

    def _options(self):
        options = [
            ('icon', self.icon),
            ('meta', self.meta),
            ('nonselectable', self.nonselectable),
            ('info', self.info),
            ('permanent', self.permanent),
        ]
        return [
            name.encode() + b'\x1f' + str(value).encode()
            for name, value in options if value is not None
        ]

    def formatted(self):
        optionstr = b''.join(self._options())
        if optionstr:
            return self.text.encode() + b'\x00' + optionstr
        else:
            return self.text.encode()


class Menu:
    def __init__(self,
                 separator=None,
                 prompt=None,
                 maxlines=None,
                 case_insensitive=None,
                 active_rows=None,
                 urgent_rows=None,
                 only_match=None,
                 no_custom=None,
                 format=None,
                 select=None,
                 message=None,
                 markup_rows=None,
                 multi_select=None,
                 sync=None,
                 window_title=None,
                 window_id=None,
                 keep_right=None,
                 display_columns=None,
                 display_column_sep=None,
                 ballot_selected=None,
                 ballot_unselected=None,
                 filter=None,
                 matching=None,
                 tokenize=None,
                 ):

         self.separator = separator
         self.prompt = prompt
         self.maxlines = maxlines
         self.case_insensitive = case_insensitive
         self.active_rows = active_rows
         self.urgent_rows = urgent_rows
         self.only_match = only_match
         self.no_custom = no_custom
         self.format = format
         self.select = select
         self.message = message
         self.markup_rows = markup_rows
         self.multi_select = multi_select
         self.sync = sync
         self.window_title = window_title
         self.window_id = window_id
         self.keep_right = keep_right
         self.display_columns = display_columns
         self.display_column_sep = display_column_sep
         self.ballot_selected = ballot_selected
         self.ballot_unselected = ballot_unselected
         self.filter = filter
         self.matching=matching
         self.tokenize=tokenize

         self.keymap = {}

         self.process: Optional[asyncio.Process] = None

    def options(self):
        raw = [
                ('-sep', self.separator),
                ('-p', self.prompt),
                ('-l', self.maxlines),
                ('-i', self.case_insensitive),
                ('-a', self.active_rows),
                ('-u', self.urgent_rows),
                ('-only-match', self.only_match),
                ('-no-custom', self.no_custom),
                ('-format', self.format),
                ('-select', self.select),
                ('-mesg', self.message),
                ('-markup-rows', self.markup_rows),
                ('-multi-select', self.multi_select),
                ('-sync', self.sync),
                ('-window-title', self.window_title),
                ('-w', self.window_id),
                ('-keep-right', self.keep_right),
                ('-display-columns', self.display_columns),
                ('-display-column-separator', self.display_column_sep),
                ('-ballot-selected-str', self.ballot_selected),
                ('-ballot-unselected-str', self.ballot_unselected),
                ('-filter', self.filter),
                ('-tokenize', self.tokenize),
                ('-matching', self.matching),
        ]
        options = list(itertools.chain(*((opt, f"\"{val}\"" if not isinstance(val, bool) else str(val).lower()) for opt, val in raw if val is not None)))
        for i, key in enumerate(self.keymap.values()):
            options.extend((f"-kb-custom-{i+1}", key))

        return options

    async def display(self):

        command = ' '.join(('rofi -dmenu', *self.options())),
        print(f"{command=}")
        if self.process is not None:
            await self.process.terminate()
            self.process = None

        self.process = await asyncio.create_subprocess_shell(
            ' '.join(('rofi -dmenu', *self.options())),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
        )

    async def write_items(self, *items: MenuItem):
        if self.process is None:
            raise ValueError("Menu cannot write items before displaying.")
        self.process.stdin.writelines(item.formatted() + b'\n' for item in items)

    async def read(self):
        if self.process is None:
            raise ValueError("Menu cannot read before displaying.")
        stdout, _ = await self.process.communicate()
        response = RofiResponse(stdout, self.process.returncode, None)
        self.process = None
        return response
