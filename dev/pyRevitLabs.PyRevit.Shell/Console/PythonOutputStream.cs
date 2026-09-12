// Copyright (c) 2010 Joe Moorhouse

using System;
using System.IO;
using System.Text;
using System.Text.RegularExpressions;

namespace PythonConsoleControl
{
    public class PythonOutputStream : Stream
    {
        PythonTextEditor textEditor;

        public PythonOutputStream(PythonTextEditor textEditor)
        {
            this.textEditor = textEditor;
        }

        public override bool CanRead
        {
            get { return false; }
        }

        public override bool CanSeek
        {
            get { return false; }
        }

        public override bool CanWrite
        {
            get { return true; }
        }

        public override long Length
        {
            get { return 0; }
        }

        public override long Position
        {
            get { return 0; }
            set { }
        }

        public override void Flush()
        {
        }

        public override long Seek(long offset, SeekOrigin origin)
        {
            return 0;
        }

        public override void SetLength(long value)
        {
        }

        public override int Read(byte[] buffer, int offset, int count)
        {
            return 0;
        }

        /// <summary>
        /// Assumes the bytes are UTF8 and writes them to the text editor.
        /// </summary>
        public override void Write(byte[] buffer, int offset, int count)
        {
            string text = Encoding.UTF8.GetString(buffer, offset, count);
            text = DecodeUnicodeEscapes(text);
            textEditor.Write(text);
        }
        private string DecodeUnicodeEscapes(string input)
        {
            return Regex.Replace(input, @"\\u[0-9a-fA-F]{4}", match =>
            {
                var hex = match.Value.Substring(2);
                int charValue = Convert.ToInt32(hex, 16);
                return char.ConvertFromUtf32(charValue);
            });
        }
    }
}
