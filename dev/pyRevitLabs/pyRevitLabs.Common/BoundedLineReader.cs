using System;
using System.IO;
using System.Text;
using System.Threading.Tasks;

namespace pyRevitLabs.Common {
    /// <summary>
    /// Reads <c>\n</c>-terminated lines from a <see cref="TextReader"/>, refusing any line longer
    /// than a fixed limit instead of buffering it whole.
    /// </summary>
    /// <remarks>
    /// Lines end at <c>\n</c> only; a <c>\r</c> right before it is dropped. A last line with no
    /// <c>\n</c> is returned at end of stream, like <see cref="TextReader.ReadLine"/>.
    /// An over-long line is read to its end and discarded before the exception is thrown, so the
    /// next call returns the line after it.
    /// The reader buffers ahead of the line it returns, so the wrapped reader must not be read
    /// directly once this one is in use.
    /// </remarks>
    public sealed class BoundedLineReader {
        public const int DefaultMaxLineChars = 16 * 1024 * 1024;

        private readonly TextReader reader;
        private readonly int maxLineChars;
        private readonly char[] buffer = new char[8192];
        private readonly StringBuilder line = new StringBuilder();
        private int position;
        private int length;
        private bool readAny;
        private bool tooLong;

        public BoundedLineReader(TextReader reader, int maxLineChars = DefaultMaxLineChars) {
            this.reader = reader;
            this.maxLineChars = maxLineChars;
        }

        /// <returns>The next line, or null at end of stream.</returns>
        /// <exception cref="InvalidDataException">The line is longer than the limit.</exception>
        public string ReadLine() {
            while (true) {
                if (position == length) {
                    length = reader.Read(buffer, 0, buffer.Length);
                    position = 0;
                    if (length == 0)
                        return EndOfStream();
                }
                if (TakeLine())
                    return Finish();
            }
        }

        /// <returns>The next line, or null at end of stream.</returns>
        /// <exception cref="InvalidDataException">The line is longer than the limit.</exception>
        public async Task<string> ReadLineAsync() {
            while (true) {
                if (position == length) {
                    length = await reader.ReadAsync(buffer, 0, buffer.Length).ConfigureAwait(false);
                    position = 0;
                    if (length == 0)
                        return EndOfStream();
                }
                if (TakeLine())
                    return Finish();
            }
        }

        private bool TakeLine() {
            readAny = true;
            var start = position;
            var newline = Array.IndexOf(buffer, '\n', position, length - position);
            var end = newline < 0 ? length : newline;
            position = newline < 0 ? length : newline + 1;
            if (!tooLong && line.Length + (end - start) > maxLineChars + 1) {
                tooLong = true;
                line.Clear();
            }
            if (!tooLong)
                line.Append(buffer, start, end - start);
            return newline >= 0;
        }

        private string EndOfStream() => readAny ? Finish() : null;

        private string Finish() {
            if (line.Length > 0 && line[line.Length - 1] == '\r')
                line.Length--;
            var refused = tooLong || line.Length > maxLineChars;
            var text = refused ? null : line.ToString();
            line.Clear();
            readAny = false;
            tooLong = false;
            if (refused)
                throw new InvalidDataException($"Line is longer than {maxLineChars} characters.");
            return text;
        }
    }
}
