using System;

namespace pyRevitLabs.PythonNet
{
    /// <summary>
    /// xxx
    /// </summary>
    internal interface IReflectedType
    {
        string PythonTypeName();
        Type GetReflectedType();
    }

    internal interface IReflectedClass : IReflectedType
    {
        bool IsException();
    }

    internal interface IReflectedInterface : IReflectedType
    {
    }

    internal interface IReflectedArray : IReflectedType
    {
    }

    internal interface IReflectedGenericClass : IReflectedClass
    {
    }
}
