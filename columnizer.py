#!/usr/bin/env python
# encoding: utf-8
# Author: Shawn Roche
# Date: 4/12/2018
#########################
import sys
import subprocess

class Columnizer:
    def __init__(self, headers, base_padding=6, mode='line', colorize=False, colormap=False, delimiter='  ', indent=0, paginate=True, paginate_break=True):
        """
        Simplifies outputting large data sets in formatted columns. Just pass the list of headers when instancing and
        then calling update() with more values will handle formatting what is passed into columns. Can also optionally
        add ANSI coloring to output.

        :param headers: headers to use for this instance
        :type headers: list
        :param base_padding: minimum padding level to use for all columns regardless of header length
        :type base_padding: int
        :param mode: Possible values are 'stream', 'line', or all. Default is line. Depending on what is passed,
            self.update() will either print the whole table, one line at a time, or one column at a time.
        :type mode: str
        :param colorize: Whether to add term coloring to passed message for common words
        :type colorize: Bool
        :param colormap: define custom color mapping for words or numbers. You would pass a dict of tuples where the
                            first item is a string that is compatible with the .format() string method and the second
                            item is a list of words to apply the color to if they get passed into update()

                            EX: {'fail': ('\033[91m{}\033[0m', ['fail', 'failed', 'error']),
                                 'ok': ('\033[92m{}\033[0m', ['ok', 'pass', 'passed', 'success'])}
        :type colormap: dict
        :param delimiter: What to put as a spacer in between columns. Default is 3 spaces
        :type delimiter: str
        :param indent: Optional param to indent the table to better visually break up output
        :type indent: int
        :param paginate: Output will paginate based on the terminal height if needed. Default is True
        :type paginate: bool
        :param paginate_break: Output will paginate based on the terminal height if needed. Default is True
        :type paginate_break: bool
        """
        if not colormap:
            self. colormap = {
                'fail': ('\033[91m{}\033[0m', ['fail', 'failed', 'error', 'false', 'no']),
                'ok': ('\033[92m{}\033[0m', ['ok', 'pass', 'passed', 'success', 'true', 'yes']),
                'warn': ('\033[93m{}\033[0m', ['warn', 'warning']),
                'header': ('\033[95m{}\033[0m', ['']),
                'bold': ('\033[1m{}\033[0m', ['']),
                'end': ('\033[0m{}\033[0m', [''])
            }
        else:
            self.colormap = colormap
        self.delimiter = delimiter
        self.headers = headers
        self.padding = [(base_padding, 'str')] * len(self.headers)
        self.colorize_output = colorize
        self.row = []
        self.message = []
        self.mode = mode
        self.column_number = 0
        self.header_printed = False
        self.needs_reflow = False
        self.indent = indent
        self.paginate = paginate
        self.paginate_break = paginate_break
        self.term_height = int(subprocess.check_output(['stty', 'size']).split()[0])
        self.count = 0

    def pad_columns(self, message):
        """
        Called after the first line of output is given to determine the appropriate space padding to make even columns
        :param message:
        :return:
        """
        header = ' ' * self.indent

        # Check that a list of lists was passed for message, if not make it one
        # This is so the same logic can be used for mode=stream, mode=line, and mode=all
        if not isinstance(message[0], list):
            message = [message]

        # iterate through the rows in the message, comparing the length of each column to the length of the header and
        # the current padding value stored for that column. Keep the highest length so the columns are aligned
        for row in message:
            padding = []
            for index, col in enumerate(row):
                max_val = max([len(str(col)), len(str(self.headers[index])), self.padding[index][0]])
                try:
                    int(col)
                    val_type = 'num'
                except:
                    val_type = 'str'

                padding.append((max_val, val_type))

            self.padding = padding

        for i, col in enumerate(self.headers):
            if self.padding[i][1] == 'num':
                header += '{}'.format(col.rjust(self.padding[i][0]))
            else:
                header += '{}'.format(col.ljust(self.padding[i][0]))

            if len(self.padding) - i > 1:
                header += self.delimiter

        line_break = '{}{}'.format(' ' * self.indent, '-' * len(header))
        if self.colorize_output:
            header = self.colormap['bold'][0].format(header)

        print(header)
        print(line_break)
        self.header_printed = True

    def update(self, message):
        """
        Prints a message under the header formatted into columns.

        :param message: what should be printed separated by column
        :type message: list str
        """
        if not self.header_printed:
            self.pad_columns(message)

        self.needs_reflow = False

        if self.mode == 'line':
            self._update_line(message)

        elif self.mode == 'all':
            for row in message:
                self._update_line(row)

        elif self.mode == 'stream':
            self._update_column(message)

    def _update_line(self, message):
        for col in message:
            self._update_column(col)
        pass

    def _update_column(self, message):
        self.row.append(message)

        word = str(message)
        if len(word) > self.padding[self.column_number][0]:
            self.needs_reflow = True

        if self.padding[self.column_number][1] == 'num':
            msg = '{}'.format(word.rjust(self.padding[self.column_number][0]))
        else:
            msg = '{}'.format(word.ljust(self.padding[self.column_number][0]))

        if self.colorize_output:
            # Color the text if requested
            msg = self.colorize(msg)

        if self.column_number == 0:
            msg = '{}{}'.format(' ' * self.indent, msg)
        self.column_number += 1
        if self.column_number < len(self.headers):
            # If the column isnt the last in the row add the delimiter chars to it
            msg += self.delimiter

        sys.stdout.write(msg)
        sys.stdout.flush()

        if self.column_number >= len(self.headers):
            self.count += 1
            self.column_number = 0
            self.message.append(self.row)
            self.row = []
            print('')
            if self.needs_reflow:
                stored_mode = self.mode
                self.needs_reflow = False
                self.mode = 'all'
                self.pad_columns(self.message)
                self.update(self.message)
                self.mode = stored_mode

            if self.paginate and len(self.message) > self.term_height - 6:
                if self.paginate_break:
                    user_input = input('\nlines {}-{} '.format(self.count - self.term_height + 6, self.count))
                    if user_input == 'q':
                        print('Manual interrupt received')
                        exit(0)
                    print()
                self.message = []
                self.header_printed = False


    def colorize(self, word):
        """
        Will apply colors to words like pass, fail, ok, warn, warning

        :param word: Message that will be colorized
        :type word: str
        :return: Colorized word
        :rtype: str
        """
        word = str(word)

        for key, value in self.colormap.items():
            color, criteria = value
            if word.lower().strip() in criteria:
                word = color.format(word)

        return word
