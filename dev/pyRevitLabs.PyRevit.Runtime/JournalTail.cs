using System;
using System.IO;
using System.Text;

namespace PyRevitLabs.PyRevit.Runtime {
    /// <summary>
    /// Reads the lines appended to a growing journal file since the previous read.
    /// </summary>
    /// <remarks>
    /// Only complete lines are returned. Text after the last line feed stays unread until its line
    /// break arrives, so a line written across several reads is delivered once and whole. If the file
    /// becomes shorter than the read position it is treated as truncated and read from the start.
    /// Not thread-safe.
    /// </remarks>
    public sealed class JournalTail {
        private static readonly string[] NoLines = new string[0];
        private static readonly char[] LineBreaks = { '\r', '\n' };

        private readonly string journalFile;
        private long offset;

        /// <summary>
        /// Starts reading at the current end of the file, or at the beginning if it does not exist yet.
        /// </summary>
        /// <param name="journalFile">Path of the journal file to follow.</param>
        public JournalTail(string journalFile) {
            this.journalFile = journalFile;
            var info = new FileInfo(journalFile);
            offset = info.Exists ? info.Length : 0;
        }

        /// <summary>
        /// Returns the complete, non-empty lines appended since the last call.
        /// </summary>
        /// <returns>The new lines, or an empty array when there are none or the file does not exist.</returns>
        public string[] ReadNewLines() {
            var info = new FileInfo(journalFile);
            if (!info.Exists)
                return NoLines;

            if (info.Length < offset)
                offset = 0;
            if (info.Length == offset)
                return NoLines;

            byte[] chunk;
            using (var stream = new FileStream(journalFile, FileMode.Open, FileAccess.Read, FileShare.Delete | FileShare.ReadWrite)) {
                stream.Seek(offset, SeekOrigin.Begin);
                chunk = new byte[stream.Length - offset];
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

            int lastLineFeed = Array.LastIndexOf(chunk, (byte)'\n');
            if (lastLineFeed < 0)
                return NoLines;

            offset += lastLineFeed + 1;
            var text = Encoding.UTF8.GetString(chunk, 0, lastLineFeed + 1);
            return text.Split(LineBreaks, StringSplitOptions.RemoveEmptyEntries);
        }
    }
}
