using System;
using System.IO;
using System.Text;

namespace PyRevitLabs.PyRevit.Runtime {
    /// <summary>
    /// Reads the lines appended to a growing journal file since the previous read.
    /// </summary>
    /// <remarks>
    /// Only complete lines are returned, blank lines included. Text after the last line feed stays
    /// unread until its line break arrives, so a line written across several reads is delivered once
    /// and whole. If the open file is shorter than the read position it is treated as truncated and
    /// read from the start. A file replaced by a longer one is not detected. At most one chunk of
    /// bytes is read per call; a chunk without any line feed is discarded, together with the rest of that
    /// line up to its next line feed, so a runaway line cannot stall the reader or leak its tail. Not thread-safe.
    /// </remarks>
    public sealed class JournalTail {
        private const int DefaultMaxChunkBytes = 1 << 20;
        private static readonly string[] NoLines = new string[0];
        private static readonly string[] LineBreaks = { "\r\n", "\n", "\r" };

        private readonly string journalFile;
        private readonly int maxChunkBytes;
        private long offset;
        private bool discardingLine;

        /// <summary>
        /// Starts reading at the current end of the file, or at the beginning if it does not exist yet.
        /// If the file ends inside an unfinished line, the rest of that line is skipped when it arrives.
        /// </summary>
        /// <param name="journalFile">Path of the journal file to follow.</param>
        public JournalTail(string journalFile) : this(journalFile, DefaultMaxChunkBytes) {
        }

        internal JournalTail(string journalFile, int maxChunkBytes) {
            this.journalFile = journalFile;
            this.maxChunkBytes = maxChunkBytes;
            var info = new FileInfo(journalFile);
            offset = info.Exists ? info.Length : 0;
            discardingLine = offset > 0 && EndsInsideLine(offset);
        }

        private bool EndsInsideLine(long length) {
            try {
                using (var stream = new FileStream(journalFile, FileMode.Open, FileAccess.Read, FileShare.Delete | FileShare.ReadWrite)) {
                    if (stream.Length < length)
                        return false;
                    stream.Seek(length - 1, SeekOrigin.Begin);
                    return stream.ReadByte() != '\n';
                }
            }
            catch (IOException) {
                return false;
            }
        }

        /// <summary>
        /// Returns the complete lines appended since the last call, one entry per line break.
        /// </summary>
        /// <returns>The new lines, or an empty array when there are none or the file does not exist.</returns>
        public string[] ReadNewLines() {
            byte[] chunk;
            try {
                using (var stream = new FileStream(journalFile, FileMode.Open, FileAccess.Read, FileShare.Delete | FileShare.ReadWrite)) {
                    if (stream.Length < offset) {
                        offset = 0;
                        discardingLine = false;
                    }
                    long available = stream.Length - offset;
                    if (available == 0)
                        return NoLines;

                    stream.Seek(offset, SeekOrigin.Begin);
                    chunk = new byte[Math.Min(available, maxChunkBytes)];
                    int read = 0;
                    while (read < chunk.Length) {
                        int n = stream.Read(chunk, read, chunk.Length - read);
                        if (n == 0)
                            break;
                        read += n;
                    }
                    if (read < chunk.Length)
                        Array.Resize(ref chunk, read);
                }
            }
            catch (FileNotFoundException) {
                return NoLines;
            }
            catch (DirectoryNotFoundException) {
                return NoLines;
            }

            int start = 0;
            if (discardingLine) {
                int endOfDiscarded = Array.IndexOf(chunk, (byte)'\n');
                if (endOfDiscarded < 0) {
                    offset += chunk.Length;
                    return NoLines;
                }
                start = endOfDiscarded + 1;
                offset += start;
                discardingLine = false;
            }

            int lastLineFeed = Array.LastIndexOf(chunk, (byte)'\n');
            if (lastLineFeed < start) {
                if (start == 0 && chunk.Length >= maxChunkBytes) {
                    offset += chunk.Length;
                    discardingLine = true;
                }
                return NoLines;
            }

            offset += lastLineFeed + 1 - start;
            var text = Encoding.UTF8.GetString(chunk, start, lastLineFeed + 1 - start);
            var lines = text.Split(LineBreaks, StringSplitOptions.None);
            Array.Resize(ref lines, lines.Length - 1);
            return lines;
        }
    }
}
