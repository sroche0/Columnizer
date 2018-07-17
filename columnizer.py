class Columnizer:
    def __init__(self, headers, base_padding=6, mode='line', colorize=False, colormap=False, delimiter='  ', indent=0,
                 col_just=None, paginate=True, paginate_break=False, print_header=True):
        """
        Simplifies outputting large data sets in formatted columns. Just pass the list of headers when instancing and
        then calling update() with more values will handle formatting what is passed into columns. Can also optionally
        add ANSI coloring to output.

        :param headers: headers to use for this instance
        :type headers: list
        :param base_padding: minimum padding level to use for all columns regardless of header length
        :type base_padding: int
        :param mode: Possible values are 'line', or 'all'. Default is line. Depending on what is passed,
            self.update() will either print the whole table at once or accept updates line by line.
        :type mode: str
        :param colorize: Whether to add term coloring to passed message for common words
        :type colorize: Bool
        :param col_just: If given, a list of column justifications for each column, to override defaults
        :type col_just: List
        :param colormap: define custom color mapping for words or numbers. You can also set a color for a specific
                        column that is always applied. Pass a dict in similar format to below which will update the
                        default colormap. If setting a column, no "match" key is needed
                            EX: {'fail': {'color': '\033[91m', 'match': ['fail', 'failed', 'error']},
                                 3: {'color': '\033[92m'}
        :type colormap: dict
        :param delimiter: What to put as a spacer in between columns. Default is 3 spaces
        :type delimiter: str
        :param indent: Optional param to indent the table to better visually break up output
        :type indent: int
        :param paginate: Output will paginate based on the terminal height if needed. Default is True
        :type paginate: bool
        :param paginate_break: Output will paginate based on the terminal height if needed. Default is False
        :type paginate_break: bool
        :param print_header: Toggle printing of the header line
        :type print_header: bool
        """

        self.colors = BColors()

        self.colormap = {
            'fail': {
                'color': '\033[91m',
                'match': ['fail', 'failed', 'error', 'false', 'no']
            },
            'ok': {
                'color': '\033[92m',
                'match': ['ok', 'pass', 'passed', 'success', 'true', 'yes']
            },
            'warn': {
                'color': '\033[93m',
                'match': ['warn', 'warning']
            },
            'header': {
                'color': self.colors.YELLOW,
                'match': []
            },
            'bold': {
                'color': '\033[1m',
                'match': []
            },
            'end': {
                'color': '\033[0m',
                'match': []
            }
        }

        if colormap:
            self.colormap.update(colormap)

        self.delimiter = delimiter
        if isinstance(headers[0], list):
            self.headers = headers[-1]
            self.headers_list = headers
        else:
            self.headers = headers
            self.headers_list = [headers]

        self.column_data = {x: {'padding': base_padding, 'type': 'str'} for x in self.headers}
        self.col_just = col_just
        self.colorize_output = colorize
        self.message = []
        self.mode = mode
        self.padding_done = False
        self.needs_reflow = False
        self.indent = indent
        self.paginate = paginate
        self.paginate_break = paginate_break
        self.print_header = print_header
        try:
            self.term_height = int(subprocess.check_output(['stty', 'size']).split()[0])
        except Exception:
            self.term_height = 30
        self.count = 0

    def discover_padding(self, message):
        """
        Called after the first line of output is given, or on table reflow, to determine the appropriate space padding to make even columns
        :param message:
        :return:
        """
        self.padding_done = True
        # Check that a list of lists was passed for message, if not make it one
        # This is so the same logic can be used for mode=stream, mode=line, and mode=all
        try:
            if not isinstance(message[0], list):
                message = [message]
        except KeyError:
            message = [message]

        # iterate through the rows in the message, comparing the length of each column to the length of the header and
        # the current padding value stored for that column. Keep the highest length so the columns are aligned
        for headers in self.headers_list:
            for index, col in enumerate(headers):
                key = self.headers[index]
                for row in message:
                    if isinstance(row, dict):
                        word = row.get(key)
                    else:
                        word = row[index]

                    self.column_data[key]['padding'] = max([len(str(word)), len(str(col)), self.column_data[key]['padding']])

                    if not self.col_just:
                        # If manual column justifications haven't been specified, discover them dynamically
                        try:
                            int(word)
                            self.column_data[key]['type'] = 'num'
                        except ValueError:
                            self.column_data[key]['type'] = 'str'

                    else:
                        self.column_data[key]['type'] = self.col_just[index]

        if self.print_header:
            for headers in self.headers_list:
                header = []
                for i, col in enumerate(headers):
                    key = self.headers[i]
                    if self.column_data[key]['type'] == 'num':
                        header.append(col.rjust(self.column_data[key]['padding']))
                    else:
                        header.append(col.ljust(self.column_data[key]['padding']))

                header = self.delimiter.join(header)
                line_break = '-' * len(header)
                if self.colorize_output:
                    header = '{}{}\033[0m'.format(self.colormap['header']['color'], header)

                print('{}{}'.format(' ' * self.indent, header))

            print('{}{}'.format(' ' * self.indent, line_break))

    def update(self, message):
        """
        Prints a message under the header formatted into columns.

        :param message: what should be printed separated by column
        :type message: list str
        """
        if not self.padding_done:
            self.discover_padding(message)

        self.needs_reflow = False

        if self.mode == 'line':
            self._update_line(message)

        elif self.mode == 'all':
            for row in message:
                self._update_line(row)

    def _update_line(self, row):
        self.count += 1
        self.message.append(row)
        formatted_row = []

        for index, col in enumerate(self.headers):
            if isinstance(row, dict):
                word = row[col]
            else:
                word = row[index]
            formatted_row.append(self._format_column(col, word))

        formatted_row = '{}{}'.format(' ' * self.indent, self.delimiter.join(formatted_row))

        if not self.needs_reflow:
            print(formatted_row)
            if self.paginate and len(self.message) + 7 > self.term_height:
                if self.paginate_break:
                    print('\nlines {}-{} '.format(self.count - self.term_height + 6, self.count))
                    raw_input('Enter to continue, CTRL+C to quit')

                print
                self.message = []
                self.padding_done = False
        else:
            self._reflow_columns()

    def _format_column(self, col, message):
        word = str(message)
        if len(word) > self.column_data[col]['padding']:
            self.column_data[col]['padding'] = len(word)
            self.needs_reflow = True

        if self.column_data[col]['type'] == 'num':
            msg = '{}'.format(word.rjust(self.column_data[col]['padding']))
        else:
            msg = '{}'.format(word.ljust(self.column_data[col]['padding']))

        if self.colorize_output:
            # Color the text if requested
            msg = self.colorize(msg, col)

        return msg

    def _reflow_columns(self):
        """
        Used in line by line mode if a value passed later in table would break the column spacing. It re discovers the
        appropriate padding and reprints the whole table thats been made up til that pount
        :return:
        """
        # Try really hard to prevent recursion hell
        self.needs_reflow = False
        self.padding_done = False

        # Store the mode that the table was initialized with and then set it to "all" so the entire table we have so far
        # gets reprinted
        old_mode = str(self.mode)
        self.mode = 'all'

        # create a copy of the table created so far and the reset it to blank so the reflow can rebuild it with the
        # correct padding
        message = list(self.message)
        self.message = []

        # Do a normal update() and then reset the mode back to what it was
        print('\n{}Long value detected, re-flowing columns to fit\n'.format(' ' * self.indent))
        self.update(message)
        self.mode = old_mode

    def colorize(self, word, column):
        """
        Will apply colors to words like pass, fail, ok, warn, warning

        :param word: Message that will be colorized
        :type word: str
        :param column: The number column the data is in
        :type column: int
        :return: Colorized word
        :rtype: str
        """
        word = str(word)

        # try to get the dict version and list version of color (legacy mode support)
        if self.colormap.get(column):
            word = '{}{}\033[0m'.format(self.colormap[column]['color'], word)
        elif self.colormap.get(self.headers.index(column)):
            word = '{}{}\033[0m'.format(self.colormap[column]['color'], word)
        else:
            for category, values, in self.colormap.items():
                if word.lower().strip() in self.colormap[category]['match']:
                    word = '{}{}\033[0m'.format(self.colormap[category]['color'], word)

        return word