using System;
using System.IO;
using System.Text;
using System.Threading;
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
    /// Invariant: characters are read one at a time, never past the <c>\n</c> that ends the line.
    /// A block read on a <see cref="StreamReader"/> keeps reading the stream while each read
    /// fills its byte buffer, so it would wait for the client's next line before returning this one.
    /// </remarks>
    public sealed class BoundedLineReader {
        public const int DefaultMaxLineChars = 16 * 1024 * 1024;

        private readonly TextReader reader;
        private readonly int maxLineChars;
        private readonly char[] single = new char[1];
        private StringBuilder line = new StringBuilder();
        private bool readAny;
        private bool tooLong;

        public BoundedLineReader(TextReader reader, int maxLineChars = DefaultMaxLineChars) {
            this.reader = reader;
            this.maxLineChars = maxLineChars;
        }

        /// <returns>The next line, or null at end of stream.</returns>
        /// <exception cref="InvalidDataException">The line is longer than the limit.</exception>
        public string ReadLine() {
            int next;
            while ((next = reader.Read()) >= 0) {
                if (Take((char)next))
                    return Finish();
            }
            return EndOfStream();
        }

        /// <returns>The next line, or null at end of stream.</returns>
        /// <exception cref="InvalidDataException">The line is longer than the limit.</exception>
        /// <exception cref="OperationCanceledException">
        /// <paramref name="cancellation"/> fired. On .NET Framework it is only checked between characters.
        /// </exception>
        public async Task<string> ReadLineAsync(CancellationToken cancellation = default) {
            while (await ReadOneAsync(cancellation).ConfigureAwait(false) > 0) {
                if (Take(single[0]))
                    return Finish();
            }
            return EndOfStream();
        }

#if NETFRAMEWORK
        private Task<int> ReadOneAsync(CancellationToken cancellation) {
            cancellation.ThrowIfCancellationRequested();
            return reader.ReadAsync(single, 0, 1);
        }
#else
        private ValueTask<int> ReadOneAsync(CancellationToken cancellation) =>
            reader.ReadAsync(single.AsMemory(0, 1), cancellation);
#endif

        private bool Take(char next) {
            readAny = true;
            if (next == '\n')
                return true;
            if (tooLong)
                return false;
            if (line.Length > maxLineChars) {
                tooLong = true;
                line = new StringBuilder();
                return false;
            }
            line.Append(next);
            return false;
        }

        private string EndOfStream() => readAny ? Finish() : null;

        private string Finish() {
            if (line.Length > 0 && line[line.Length - 1] == '\r')
                line.Length--;
            var refused = tooLong || line.Length > maxLineChars;
            var text = refused ? null : line.ToString();
            line = new StringBuilder();
            readAny = false;
            tooLong = false;
            if (refused)
                throw new InvalidDataException($"Line is longer than {maxLineChars} characters.");
            return text;
        }
    }
}
