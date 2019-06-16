# .NET Dependecy Conflicts

## Newtonsoft.Json

[See related issues here](https://github.com/eirannejad/pyRevit/issues?utf8=%E2%9C%93&q=is%3Aissue+is%3Aclosed+Newtonsoft)

`Newtonsoft.Json` (==12.0.1 | .NET 4.5) was recompile to `pyRevitLabs.Json` (==12.0.1 | .NET 4.7.1) to avoid the conflict.

Changes listed here were made to the Visual Studio project

- Refactored the root namespace to `pyRevitLabs.Json`
- Renamed project assembly name to `pyRevitLabs.Json`
- New GUID for the assembly in `Assembly.cs`

  ```c#
  Guid("C85AD3F6-7962-4E4B-820E-B7E1115ABAAE")
  ```

- Added .NET 4.7.1 to the target frameworks to compile for

  ```xml
    <TargetFrameworks Condition="'$(LibraryFrameworks)'==''">net471;net45;net40;net35;net20;netstandard1.0;netstandard1.3;netstandard2.0;portable-net45+win8+wpa81+wp8;portable-net40+win8+wpa81+wp8+sl5</TargetFrameworks>
  ```

  ```xml
  <PropertyGroup Condition="'$(TargetFramework)'=='net471'">
    <AssemblyTitle>Json.NET</AssemblyTitle>
    <DefineConstants>HAVE_ADO_NET;HAVE_APP_DOMAIN;HAVE_ASYNC;HAVE_BIG_INTEGER;HAVE_BINARY_FORMATTER;HAVE_BINARY_SERIALIZATION;HAVE_BINARY_EXCEPTION_SERIALIZATION;HAVE_CAS;HAVE_CHAR_TO_LOWER_WITH_CULTURE;HAVE_CHAR_TO_STRING_WITH_CULTURE;HAVE_COM_ATTRIBUTES;HAVE_COMPONENT_MODEL;HAVE_CONCURRENT_COLLECTIONS;HAVE_COVARIANT_GENERICS;HAVE_DATA_CONTRACTS;HAVE_DATE_TIME_OFFSET;HAVE_DB_NULL_TYPE_CODE;HAVE_DYNAMIC;HAVE_EMPTY_TYPES;HAVE_ENTITY_FRAMEWORK;HAVE_EXPRESSIONS;HAVE_FAST_REVERSE;HAVE_FSHARP_TYPES;HAVE_FULL_REFLECTION;HAVE_GUID_TRY_PARSE;HAVE_HASH_SET;HAVE_ICLONEABLE;HAVE_ICONVERTIBLE;HAVE_IGNORE_DATA_MEMBER_ATTRIBUTE;HAVE_INOTIFY_COLLECTION_CHANGED;HAVE_INOTIFY_PROPERTY_CHANGING;HAVE_ISET;HAVE_LINQ;HAVE_MEMORY_BARRIER;HAVE_METHOD_IMPL_ATTRIBUTE;HAVE_NON_SERIALIZED_ATTRIBUTE;HAVE_READ_ONLY_COLLECTIONS;HAVE_REFLECTION_EMIT;HAVE_SECURITY_SAFE_CRITICAL_ATTRIBUTE;HAVE_SERIALIZATION_BINDER_BIND_TO_NAME;HAVE_STREAM_READER_WRITER_CLOSE;HAVE_STRING_JOIN_WITH_ENUMERABLE;HAVE_TIME_SPAN_PARSE_WITH_CULTURE;HAVE_TIME_SPAN_TO_STRING_WITH_CULTURE;HAVE_TIME_ZONE_INFO;HAVE_TRACE_WRITER;HAVE_TYPE_DESCRIPTOR;HAVE_UNICODE_SURROGATE_DETECTION;HAVE_VARIANT_TYPE_PARAMETERS;HAVE_VERSION_TRY_PARSE;HAVE_XLINQ;HAVE_XML_DOCUMENT;HAVE_XML_DOCUMENT_TYPE;HAVE_CONCURRENT_DICTIONARY;$(AdditionalConstants)
    </DefineConstants>
  </PropertyGroup>
  ```

## MahApps.Metro

[See related issues here](https://github.com/eirannejad/pyRevit/issues?utf8=%E2%9C%93&q=is%3Aissue+is%3Aclosed+MahApps)

`MahApps.Metro` (==1.6.5) was recompile to `pyRevitLabs.MahAppsMetro` (==1.6.5 | .NET 4.7) to avoid the conflict.

Changes listed here were made to the Visual Studio project

- Refactored the root namespace to `pyRevitLabs.MahAppsMetro`
- Refactored xaml namespaces to `pyRevitLabs.MahAppsMetro`
- Refactored `StaticResource` and `DynamicResource` references to `pyRevitLabs.MahAppsMetro`
- Renamed project assembly name to `pyRevitLabs.MahAppsMetro`

## NLog

[See related issues here](https://github.com/eirannejad/pyRevit/issues/579)

`NLog` (==4.6.4) was recompile to `pyRevitLabs.NLog` (==4.6.4 | .NET 4.5) to avoid the conflict.

Changes listed here were made to the Visual Studio project

- Refactored the root namespace to `pyRevitLabs.NLog`
- Changed Package settings to version 4.6.4
- Renamed project assembly name to `pyRevitLabs.NLog`


## natsort

natsort.natsort.py
wrapped natsort_key.__doc__ (line # 209) in try-except for IronPython 2.7.3 compatibility
