; ModuleID = 'compressed_assemblies.x86_64.ll'
source_filename = "compressed_assemblies.x86_64.ll"
target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"
target triple = "x86_64-unknown-linux-android21"

%struct.CompressedAssemblies = type {
	i32, ; uint32_t count
	ptr ; CompressedAssemblyDescriptor descriptors
}

%struct.CompressedAssemblyDescriptor = type {
	i32, ; uint32_t uncompressed_file_size
	i1, ; bool loaded
	ptr ; uint8_t data
}

@compressed_assemblies = dso_local local_unnamed_addr global %struct.CompressedAssemblies {
	i32 175, ; uint32_t count
	ptr @compressed_assembly_descriptors; CompressedAssemblyDescriptor* descriptors
}, align 8

@compressed_assembly_descriptors = internal dso_local global [175 x %struct.CompressedAssemblyDescriptor] [
	%struct.CompressedAssemblyDescriptor {
		i32 19456, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_0; uint8_t* data
	}, ; 0: XionghanChessAndroid
	%struct.CompressedAssemblyDescriptor {
		i32 3584, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_1; uint8_t* data
	}, ; 1: _Microsoft.Android.Resource.Designer
	%struct.CompressedAssemblyDescriptor {
		i32 307984, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_2; uint8_t* data
	}, ; 2: Microsoft.CSharp
	%struct.CompressedAssemblyDescriptor {
		i32 430352, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_3; uint8_t* data
	}, ; 3: Microsoft.VisualBasic.Core
	%struct.CompressedAssemblyDescriptor {
		i32 17680, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_4; uint8_t* data
	}, ; 4: Microsoft.VisualBasic
	%struct.CompressedAssemblyDescriptor {
		i32 15664, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_5; uint8_t* data
	}, ; 5: Microsoft.Win32.Primitives
	%struct.CompressedAssemblyDescriptor {
		i32 33592, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_6; uint8_t* data
	}, ; 6: Microsoft.Win32.Registry
	%struct.CompressedAssemblyDescriptor {
		i32 15672, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_7; uint8_t* data
	}, ; 7: System.AppContext
	%struct.CompressedAssemblyDescriptor {
		i32 15632, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_8; uint8_t* data
	}, ; 8: System.Buffers
	%struct.CompressedAssemblyDescriptor {
		i32 89872, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_9; uint8_t* data
	}, ; 9: System.Collections.Concurrent
	%struct.CompressedAssemblyDescriptor {
		i32 255760, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_10; uint8_t* data
	}, ; 10: System.Collections.Immutable
	%struct.CompressedAssemblyDescriptor {
		i32 48440, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_11; uint8_t* data
	}, ; 11: System.Collections.NonGeneric
	%struct.CompressedAssemblyDescriptor {
		i32 48392, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_12; uint8_t* data
	}, ; 12: System.Collections.Specialized
	%struct.CompressedAssemblyDescriptor {
		i32 126736, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_13; uint8_t* data
	}, ; 13: System.Collections
	%struct.CompressedAssemblyDescriptor {
		i32 102672, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_14; uint8_t* data
	}, ; 14: System.ComponentModel.Annotations
	%struct.CompressedAssemblyDescriptor {
		i32 17168, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_15; uint8_t* data
	}, ; 15: System.ComponentModel.DataAnnotations
	%struct.CompressedAssemblyDescriptor {
		i32 26888, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_16; uint8_t* data
	}, ; 16: System.ComponentModel.EventBasedAsync
	%struct.CompressedAssemblyDescriptor {
		i32 42296, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_17; uint8_t* data
	}, ; 17: System.ComponentModel.Primitives
	%struct.CompressedAssemblyDescriptor {
		i32 315664, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_18; uint8_t* data
	}, ; 18: System.ComponentModel.TypeConverter
	%struct.CompressedAssemblyDescriptor {
		i32 16656, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_19; uint8_t* data
	}, ; 19: System.ComponentModel
	%struct.CompressedAssemblyDescriptor {
		i32 19728, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_20; uint8_t* data
	}, ; 20: System.Configuration
	%struct.CompressedAssemblyDescriptor {
		i32 50992, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_21; uint8_t* data
	}, ; 21: System.Console
	%struct.CompressedAssemblyDescriptor {
		i32 23816, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_22; uint8_t* data
	}, ; 22: System.Core
	%struct.CompressedAssemblyDescriptor {
		i32 1016624, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_23; uint8_t* data
	}, ; 23: System.Data.Common
	%struct.CompressedAssemblyDescriptor {
		i32 16144, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_24; uint8_t* data
	}, ; 24: System.Data.DataSetExtensions
	%struct.CompressedAssemblyDescriptor {
		i32 25360, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_25; uint8_t* data
	}, ; 25: System.Data
	%struct.CompressedAssemblyDescriptor {
		i32 16688, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_26; uint8_t* data
	}, ; 26: System.Diagnostics.Contracts
	%struct.CompressedAssemblyDescriptor {
		i32 16136, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_27; uint8_t* data
	}, ; 27: System.Diagnostics.Debug
	%struct.CompressedAssemblyDescriptor {
		i32 184584, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_28; uint8_t* data
	}, ; 28: System.Diagnostics.DiagnosticSource
	%struct.CompressedAssemblyDescriptor {
		i32 29496, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_29; uint8_t* data
	}, ; 29: System.Diagnostics.FileVersionInfo
	%struct.CompressedAssemblyDescriptor {
		i32 127248, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_30; uint8_t* data
	}, ; 30: System.Diagnostics.Process
	%struct.CompressedAssemblyDescriptor {
		i32 26376, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_31; uint8_t* data
	}, ; 31: System.Diagnostics.StackTrace
	%struct.CompressedAssemblyDescriptor {
		i32 32048, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_32; uint8_t* data
	}, ; 32: System.Diagnostics.TextWriterTraceListener
	%struct.CompressedAssemblyDescriptor {
		i32 15664, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_33; uint8_t* data
	}, ; 33: System.Diagnostics.Tools
	%struct.CompressedAssemblyDescriptor {
		i32 59144, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_34; uint8_t* data
	}, ; 34: System.Diagnostics.TraceSource
	%struct.CompressedAssemblyDescriptor {
		i32 16656, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_35; uint8_t* data
	}, ; 35: System.Diagnostics.Tracing
	%struct.CompressedAssemblyDescriptor {
		i32 64784, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_36; uint8_t* data
	}, ; 36: System.Drawing.Primitives
	%struct.CompressedAssemblyDescriptor {
		i32 20752, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_37; uint8_t* data
	}, ; 37: System.Drawing
	%struct.CompressedAssemblyDescriptor {
		i32 16696, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_38; uint8_t* data
	}, ; 38: System.Dynamic.Runtime
	%struct.CompressedAssemblyDescriptor {
		i32 96560, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_39; uint8_t* data
	}, ; 39: System.Formats.Asn1
	%struct.CompressedAssemblyDescriptor {
		i32 121616, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_40; uint8_t* data
	}, ; 40: System.Formats.Tar
	%struct.CompressedAssemblyDescriptor {
		i32 16144, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_41; uint8_t* data
	}, ; 41: System.Globalization.Calendars
	%struct.CompressedAssemblyDescriptor {
		i32 15632, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_42; uint8_t* data
	}, ; 42: System.Globalization.Extensions
	%struct.CompressedAssemblyDescriptor {
		i32 16144, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_43; uint8_t* data
	}, ; 43: System.Globalization
	%struct.CompressedAssemblyDescriptor {
		i32 41232, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_44; uint8_t* data
	}, ; 44: System.IO.Compression.Brotli
	%struct.CompressedAssemblyDescriptor {
		i32 15624, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_45; uint8_t* data
	}, ; 45: System.IO.Compression.FileSystem
	%struct.CompressedAssemblyDescriptor {
		i32 38160, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_46; uint8_t* data
	}, ; 46: System.IO.Compression.ZipFile
	%struct.CompressedAssemblyDescriptor {
		i32 110344, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_47; uint8_t* data
	}, ; 47: System.IO.Compression
	%struct.CompressedAssemblyDescriptor {
		i32 32568, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_48; uint8_t* data
	}, ; 48: System.IO.FileSystem.AccessControl
	%struct.CompressedAssemblyDescriptor {
		i32 48400, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_49; uint8_t* data
	}, ; 49: System.IO.FileSystem.DriveInfo
	%struct.CompressedAssemblyDescriptor {
		i32 15632, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_50; uint8_t* data
	}, ; 50: System.IO.FileSystem.Primitives
	%struct.CompressedAssemblyDescriptor {
		i32 55088, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_51; uint8_t* data
	}, ; 51: System.IO.FileSystem.Watcher
	%struct.CompressedAssemblyDescriptor {
		i32 16144, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_52; uint8_t* data
	}, ; 52: System.IO.FileSystem
	%struct.CompressedAssemblyDescriptor {
		i32 43832, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_53; uint8_t* data
	}, ; 53: System.IO.IsolatedStorage
	%struct.CompressedAssemblyDescriptor {
		i32 48952, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_54; uint8_t* data
	}, ; 54: System.IO.MemoryMappedFiles
	%struct.CompressedAssemblyDescriptor {
		i32 78640, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_55; uint8_t* data
	}, ; 55: System.IO.Pipelines
	%struct.CompressedAssemblyDescriptor {
		i32 23816, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_56; uint8_t* data
	}, ; 56: System.IO.Pipes.AccessControl
	%struct.CompressedAssemblyDescriptor {
		i32 67888, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_57; uint8_t* data
	}, ; 57: System.IO.Pipes
	%struct.CompressedAssemblyDescriptor {
		i32 15664, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_58; uint8_t* data
	}, ; 58: System.IO.UnmanagedMemoryStream
	%struct.CompressedAssemblyDescriptor {
		i32 16136, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_59; uint8_t* data
	}, ; 59: System.IO
	%struct.CompressedAssemblyDescriptor {
		i32 575752, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_60; uint8_t* data
	}, ; 60: System.Linq.Expressions
	%struct.CompressedAssemblyDescriptor {
		i32 223496, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_61; uint8_t* data
	}, ; 61: System.Linq.Parallel
	%struct.CompressedAssemblyDescriptor {
		i32 76552, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_62; uint8_t* data
	}, ; 62: System.Linq.Queryable
	%struct.CompressedAssemblyDescriptor {
		i32 149264, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_63; uint8_t* data
	}, ; 63: System.Linq
	%struct.CompressedAssemblyDescriptor {
		i32 56120, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_64; uint8_t* data
	}, ; 64: System.Memory
	%struct.CompressedAssemblyDescriptor {
		i32 56592, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_65; uint8_t* data
	}, ; 65: System.Net.Http.Json
	%struct.CompressedAssemblyDescriptor {
		i32 676664, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_66; uint8_t* data
	}, ; 66: System.Net.Http
	%struct.CompressedAssemblyDescriptor {
		i32 131896, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_67; uint8_t* data
	}, ; 67: System.Net.HttpListener
	%struct.CompressedAssemblyDescriptor {
		i32 174904, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_68; uint8_t* data
	}, ; 68: System.Net.Mail
	%struct.CompressedAssemblyDescriptor {
		i32 51976, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_69; uint8_t* data
	}, ; 69: System.Net.NameResolution
	%struct.CompressedAssemblyDescriptor {
		i32 66320, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_70; uint8_t* data
	}, ; 70: System.Net.NetworkInformation
	%struct.CompressedAssemblyDescriptor {
		i32 56080, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_71; uint8_t* data
	}, ; 71: System.Net.Ping
	%struct.CompressedAssemblyDescriptor {
		i32 107280, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_72; uint8_t* data
	}, ; 72: System.Net.Primitives
	%struct.CompressedAssemblyDescriptor {
		i32 173360, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_73; uint8_t* data
	}, ; 73: System.Net.Quic
	%struct.CompressedAssemblyDescriptor {
		i32 162104, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_74; uint8_t* data
	}, ; 74: System.Net.Requests
	%struct.CompressedAssemblyDescriptor {
		i32 253752, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_75; uint8_t* data
	}, ; 75: System.Net.Security
	%struct.CompressedAssemblyDescriptor {
		i32 15624, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_76; uint8_t* data
	}, ; 76: System.Net.ServicePoint
	%struct.CompressedAssemblyDescriptor {
		i32 235280, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_77; uint8_t* data
	}, ; 77: System.Net.Sockets
	%struct.CompressedAssemblyDescriptor {
		i32 70928, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_78; uint8_t* data
	}, ; 78: System.Net.WebClient
	%struct.CompressedAssemblyDescriptor {
		i32 33584, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_79; uint8_t* data
	}, ; 79: System.Net.WebHeaderCollection
	%struct.CompressedAssemblyDescriptor {
		i32 23864, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_80; uint8_t* data
	}, ; 80: System.Net.WebProxy
	%struct.CompressedAssemblyDescriptor {
		i32 51976, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_81; uint8_t* data
	}, ; 81: System.Net.WebSockets.Client
	%struct.CompressedAssemblyDescriptor {
		i32 103176, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_82; uint8_t* data
	}, ; 82: System.Net.WebSockets
	%struct.CompressedAssemblyDescriptor {
		i32 17680, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_83; uint8_t* data
	}, ; 83: System.Net
	%struct.CompressedAssemblyDescriptor {
		i32 16144, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_84; uint8_t* data
	}, ; 84: System.Numerics.Vectors
	%struct.CompressedAssemblyDescriptor {
		i32 15672, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_85; uint8_t* data
	}, ; 85: System.Numerics
	%struct.CompressedAssemblyDescriptor {
		i32 41776, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_86; uint8_t* data
	}, ; 86: System.ObjectModel
	%struct.CompressedAssemblyDescriptor {
		i32 852272, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_87; uint8_t* data
	}, ; 87: System.Private.DataContractSerialization
	%struct.CompressedAssemblyDescriptor {
		i32 103216, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_88; uint8_t* data
	}, ; 88: System.Private.Uri
	%struct.CompressedAssemblyDescriptor {
		i32 153872, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_89; uint8_t* data
	}, ; 89: System.Private.Xml.Linq
	%struct.CompressedAssemblyDescriptor {
		i32 3099920, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_90; uint8_t* data
	}, ; 90: System.Private.Xml
	%struct.CompressedAssemblyDescriptor {
		i32 38704, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_91; uint8_t* data
	}, ; 91: System.Reflection.DispatchProxy
	%struct.CompressedAssemblyDescriptor {
		i32 16136, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_92; uint8_t* data
	}, ; 92: System.Reflection.Emit.ILGeneration
	%struct.CompressedAssemblyDescriptor {
		i32 16144, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_93; uint8_t* data
	}, ; 93: System.Reflection.Emit.Lightweight
	%struct.CompressedAssemblyDescriptor {
		i32 130352, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_94; uint8_t* data
	}, ; 94: System.Reflection.Emit
	%struct.CompressedAssemblyDescriptor {
		i32 15632, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_95; uint8_t* data
	}, ; 95: System.Reflection.Extensions
	%struct.CompressedAssemblyDescriptor {
		i32 501520, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_96; uint8_t* data
	}, ; 96: System.Reflection.Metadata
	%struct.CompressedAssemblyDescriptor {
		i32 16144, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_97; uint8_t* data
	}, ; 97: System.Reflection.Primitives
	%struct.CompressedAssemblyDescriptor {
		i32 24336, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_98; uint8_t* data
	}, ; 98: System.Reflection.TypeExtensions
	%struct.CompressedAssemblyDescriptor {
		i32 16656, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_99; uint8_t* data
	}, ; 99: System.Reflection
	%struct.CompressedAssemblyDescriptor {
		i32 15664, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_100; uint8_t* data
	}, ; 100: System.Resources.Reader
	%struct.CompressedAssemblyDescriptor {
		i32 16144, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_101; uint8_t* data
	}, ; 101: System.Resources.ResourceManager
	%struct.CompressedAssemblyDescriptor {
		i32 26896, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_102; uint8_t* data
	}, ; 102: System.Resources.Writer
	%struct.CompressedAssemblyDescriptor {
		i32 15632, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_103; uint8_t* data
	}, ; 103: System.Runtime.CompilerServices.Unsafe
	%struct.CompressedAssemblyDescriptor {
		i32 17720, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_104; uint8_t* data
	}, ; 104: System.Runtime.CompilerServices.VisualC
	%struct.CompressedAssemblyDescriptor {
		i32 18224, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_105; uint8_t* data
	}, ; 105: System.Runtime.Extensions
	%struct.CompressedAssemblyDescriptor {
		i32 15672, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_106; uint8_t* data
	}, ; 106: System.Runtime.Handles
	%struct.CompressedAssemblyDescriptor {
		i32 38672, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_107; uint8_t* data
	}, ; 107: System.Runtime.InteropServices.JavaScript
	%struct.CompressedAssemblyDescriptor {
		i32 15624, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_108; uint8_t* data
	}, ; 108: System.Runtime.InteropServices.RuntimeInformation
	%struct.CompressedAssemblyDescriptor {
		i32 64816, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_109; uint8_t* data
	}, ; 109: System.Runtime.InteropServices
	%struct.CompressedAssemblyDescriptor {
		i32 17680, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_110; uint8_t* data
	}, ; 110: System.Runtime.Intrinsics
	%struct.CompressedAssemblyDescriptor {
		i32 16136, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_111; uint8_t* data
	}, ; 111: System.Runtime.Loader
	%struct.CompressedAssemblyDescriptor {
		i32 143632, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_112; uint8_t* data
	}, ; 112: System.Runtime.Numerics
	%struct.CompressedAssemblyDescriptor {
		i32 66360, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_113; uint8_t* data
	}, ; 113: System.Runtime.Serialization.Formatters
	%struct.CompressedAssemblyDescriptor {
		i32 16144, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_114; uint8_t* data
	}, ; 114: System.Runtime.Serialization.Json
	%struct.CompressedAssemblyDescriptor {
		i32 23824, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_115; uint8_t* data
	}, ; 115: System.Runtime.Serialization.Primitives
	%struct.CompressedAssemblyDescriptor {
		i32 17168, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_116; uint8_t* data
	}, ; 116: System.Runtime.Serialization.Xml
	%struct.CompressedAssemblyDescriptor {
		i32 17168, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_117; uint8_t* data
	}, ; 117: System.Runtime.Serialization
	%struct.CompressedAssemblyDescriptor {
		i32 44816, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_118; uint8_t* data
	}, ; 118: System.Runtime
	%struct.CompressedAssemblyDescriptor {
		i32 58632, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_119; uint8_t* data
	}, ; 119: System.Security.AccessControl
	%struct.CompressedAssemblyDescriptor {
		i32 54024, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_120; uint8_t* data
	}, ; 120: System.Security.Claims
	%struct.CompressedAssemblyDescriptor {
		i32 17680, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_121; uint8_t* data
	}, ; 121: System.Security.Cryptography.Algorithms
	%struct.CompressedAssemblyDescriptor {
		i32 16696, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_122; uint8_t* data
	}, ; 122: System.Security.Cryptography.Cng
	%struct.CompressedAssemblyDescriptor {
		i32 16176, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_123; uint8_t* data
	}, ; 123: System.Security.Cryptography.Csp
	%struct.CompressedAssemblyDescriptor {
		i32 16144, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_124; uint8_t* data
	}, ; 124: System.Security.Cryptography.Encoding
	%struct.CompressedAssemblyDescriptor {
		i32 15672, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_125; uint8_t* data
	}, ; 125: System.Security.Cryptography.OpenSsl
	%struct.CompressedAssemblyDescriptor {
		i32 16144, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_126; uint8_t* data
	}, ; 126: System.Security.Cryptography.Primitives
	%struct.CompressedAssemblyDescriptor {
		i32 17200, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_127; uint8_t* data
	}, ; 127: System.Security.Cryptography.X509Certificates
	%struct.CompressedAssemblyDescriptor {
		i32 705296, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_128; uint8_t* data
	}, ; 128: System.Security.Cryptography
	%struct.CompressedAssemblyDescriptor {
		i32 38152, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_129; uint8_t* data
	}, ; 129: System.Security.Principal.Windows
	%struct.CompressedAssemblyDescriptor {
		i32 15664, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_130; uint8_t* data
	}, ; 130: System.Security.Principal
	%struct.CompressedAssemblyDescriptor {
		i32 15632, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_131; uint8_t* data
	}, ; 131: System.Security.SecureString
	%struct.CompressedAssemblyDescriptor {
		i32 18744, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_132; uint8_t* data
	}, ; 132: System.Security
	%struct.CompressedAssemblyDescriptor {
		i32 17200, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_133; uint8_t* data
	}, ; 133: System.ServiceModel.Web
	%struct.CompressedAssemblyDescriptor {
		i32 16176, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_134; uint8_t* data
	}, ; 134: System.ServiceProcess
	%struct.CompressedAssemblyDescriptor {
		i32 741168, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_135; uint8_t* data
	}, ; 135: System.Text.Encoding.CodePages
	%struct.CompressedAssemblyDescriptor {
		i32 16144, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_136; uint8_t* data
	}, ; 136: System.Text.Encoding.Extensions
	%struct.CompressedAssemblyDescriptor {
		i32 16144, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_137; uint8_t* data
	}, ; 137: System.Text.Encoding
	%struct.CompressedAssemblyDescriptor {
		i32 70416, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_138; uint8_t* data
	}, ; 138: System.Text.Encodings.Web
	%struct.CompressedAssemblyDescriptor {
		i32 617736, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_139; uint8_t* data
	}, ; 139: System.Text.Json
	%struct.CompressedAssemblyDescriptor {
		i32 369424, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_140; uint8_t* data
	}, ; 140: System.Text.RegularExpressions
	%struct.CompressedAssemblyDescriptor {
		i32 57096, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_141; uint8_t* data
	}, ; 141: System.Threading.Channels
	%struct.CompressedAssemblyDescriptor {
		i32 16144, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_142; uint8_t* data
	}, ; 142: System.Threading.Overlapped
	%struct.CompressedAssemblyDescriptor {
		i32 186120, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_143; uint8_t* data
	}, ; 143: System.Threading.Tasks.Dataflow
	%struct.CompressedAssemblyDescriptor {
		i32 16136, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_144; uint8_t* data
	}, ; 144: System.Threading.Tasks.Extensions
	%struct.CompressedAssemblyDescriptor {
		i32 61712, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_145; uint8_t* data
	}, ; 145: System.Threading.Tasks.Parallel
	%struct.CompressedAssemblyDescriptor {
		i32 17200, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_146; uint8_t* data
	}, ; 146: System.Threading.Tasks
	%struct.CompressedAssemblyDescriptor {
		i32 16184, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_147; uint8_t* data
	}, ; 147: System.Threading.Thread
	%struct.CompressedAssemblyDescriptor {
		i32 16136, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_148; uint8_t* data
	}, ; 148: System.Threading.ThreadPool
	%struct.CompressedAssemblyDescriptor {
		i32 15632, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_149; uint8_t* data
	}, ; 149: System.Threading.Timer
	%struct.CompressedAssemblyDescriptor {
		i32 45360, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_150; uint8_t* data
	}, ; 150: System.Threading
	%struct.CompressedAssemblyDescriptor {
		i32 175928, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_151; uint8_t* data
	}, ; 151: System.Transactions.Local
	%struct.CompressedAssemblyDescriptor {
		i32 16696, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_152; uint8_t* data
	}, ; 152: System.Transactions
	%struct.CompressedAssemblyDescriptor {
		i32 15664, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_153; uint8_t* data
	}, ; 153: System.ValueTuple
	%struct.CompressedAssemblyDescriptor {
		i32 30992, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_154; uint8_t* data
	}, ; 154: System.Web.HttpUtility
	%struct.CompressedAssemblyDescriptor {
		i32 15624, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_155; uint8_t* data
	}, ; 155: System.Web
	%struct.CompressedAssemblyDescriptor {
		i32 16144, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_156; uint8_t* data
	}, ; 156: System.Windows
	%struct.CompressedAssemblyDescriptor {
		i32 16184, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_157; uint8_t* data
	}, ; 157: System.Xml.Linq
	%struct.CompressedAssemblyDescriptor {
		i32 22328, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_158; uint8_t* data
	}, ; 158: System.Xml.ReaderWriter
	%struct.CompressedAssemblyDescriptor {
		i32 16696, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_159; uint8_t* data
	}, ; 159: System.Xml.Serialization
	%struct.CompressedAssemblyDescriptor {
		i32 16144, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_160; uint8_t* data
	}, ; 160: System.Xml.XDocument
	%struct.CompressedAssemblyDescriptor {
		i32 16144, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_161; uint8_t* data
	}, ; 161: System.Xml.XPath.XDocument
	%struct.CompressedAssemblyDescriptor {
		i32 16144, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_162; uint8_t* data
	}, ; 162: System.Xml.XPath
	%struct.CompressedAssemblyDescriptor {
		i32 16136, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_163; uint8_t* data
	}, ; 163: System.Xml.XmlDocument
	%struct.CompressedAssemblyDescriptor {
		i32 18192, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_164; uint8_t* data
	}, ; 164: System.Xml.XmlSerializer
	%struct.CompressedAssemblyDescriptor {
		i32 23824, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_165; uint8_t* data
	}, ; 165: System.Xml
	%struct.CompressedAssemblyDescriptor {
		i32 50960, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_166; uint8_t* data
	}, ; 166: System
	%struct.CompressedAssemblyDescriptor {
		i32 16656, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_167; uint8_t* data
	}, ; 167: WindowsBase
	%struct.CompressedAssemblyDescriptor {
		i32 60176, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_168; uint8_t* data
	}, ; 168: mscorlib
	%struct.CompressedAssemblyDescriptor {
		i32 101136, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_169; uint8_t* data
	}, ; 169: netstandard
	%struct.CompressedAssemblyDescriptor {
		i32 240184, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_170; uint8_t* data
	}, ; 170: Java.Interop
	%struct.CompressedAssemblyDescriptor {
		i32 82976, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_171; uint8_t* data
	}, ; 171: Mono.Android.Export
	%struct.CompressedAssemblyDescriptor {
		i32 19008, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_172; uint8_t* data
	}, ; 172: Mono.Android.Runtime
	%struct.CompressedAssemblyDescriptor {
		i32 37449272, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_173; uint8_t* data
	}, ; 173: Mono.Android
	%struct.CompressedAssemblyDescriptor {
		i32 4777264, ; uint32_t uncompressed_file_size
		i1 false, ; bool loaded
		ptr @__compressedAssemblyData_174; uint8_t* data
	} ; 174: System.Private.CoreLib
], align 16

@__compressedAssemblyData_0 = internal dso_local global [19456 x i8] zeroinitializer, align 16
@__compressedAssemblyData_1 = internal dso_local global [3584 x i8] zeroinitializer, align 16
@__compressedAssemblyData_2 = internal dso_local global [307984 x i8] zeroinitializer, align 16
@__compressedAssemblyData_3 = internal dso_local global [430352 x i8] zeroinitializer, align 16
@__compressedAssemblyData_4 = internal dso_local global [17680 x i8] zeroinitializer, align 16
@__compressedAssemblyData_5 = internal dso_local global [15664 x i8] zeroinitializer, align 16
@__compressedAssemblyData_6 = internal dso_local global [33592 x i8] zeroinitializer, align 16
@__compressedAssemblyData_7 = internal dso_local global [15672 x i8] zeroinitializer, align 16
@__compressedAssemblyData_8 = internal dso_local global [15632 x i8] zeroinitializer, align 16
@__compressedAssemblyData_9 = internal dso_local global [89872 x i8] zeroinitializer, align 16
@__compressedAssemblyData_10 = internal dso_local global [255760 x i8] zeroinitializer, align 16
@__compressedAssemblyData_11 = internal dso_local global [48440 x i8] zeroinitializer, align 16
@__compressedAssemblyData_12 = internal dso_local global [48392 x i8] zeroinitializer, align 16
@__compressedAssemblyData_13 = internal dso_local global [126736 x i8] zeroinitializer, align 16
@__compressedAssemblyData_14 = internal dso_local global [102672 x i8] zeroinitializer, align 16
@__compressedAssemblyData_15 = internal dso_local global [17168 x i8] zeroinitializer, align 16
@__compressedAssemblyData_16 = internal dso_local global [26888 x i8] zeroinitializer, align 16
@__compressedAssemblyData_17 = internal dso_local global [42296 x i8] zeroinitializer, align 16
@__compressedAssemblyData_18 = internal dso_local global [315664 x i8] zeroinitializer, align 16
@__compressedAssemblyData_19 = internal dso_local global [16656 x i8] zeroinitializer, align 16
@__compressedAssemblyData_20 = internal dso_local global [19728 x i8] zeroinitializer, align 16
@__compressedAssemblyData_21 = internal dso_local global [50992 x i8] zeroinitializer, align 16
@__compressedAssemblyData_22 = internal dso_local global [23816 x i8] zeroinitializer, align 16
@__compressedAssemblyData_23 = internal dso_local global [1016624 x i8] zeroinitializer, align 16
@__compressedAssemblyData_24 = internal dso_local global [16144 x i8] zeroinitializer, align 16
@__compressedAssemblyData_25 = internal dso_local global [25360 x i8] zeroinitializer, align 16
@__compressedAssemblyData_26 = internal dso_local global [16688 x i8] zeroinitializer, align 16
@__compressedAssemblyData_27 = internal dso_local global [16136 x i8] zeroinitializer, align 16
@__compressedAssemblyData_28 = internal dso_local global [184584 x i8] zeroinitializer, align 16
@__compressedAssemblyData_29 = internal dso_local global [29496 x i8] zeroinitializer, align 16
@__compressedAssemblyData_30 = internal dso_local global [127248 x i8] zeroinitializer, align 16
@__compressedAssemblyData_31 = internal dso_local global [26376 x i8] zeroinitializer, align 16
@__compressedAssemblyData_32 = internal dso_local global [32048 x i8] zeroinitializer, align 16
@__compressedAssemblyData_33 = internal dso_local global [15664 x i8] zeroinitializer, align 16
@__compressedAssemblyData_34 = internal dso_local global [59144 x i8] zeroinitializer, align 16
@__compressedAssemblyData_35 = internal dso_local global [16656 x i8] zeroinitializer, align 16
@__compressedAssemblyData_36 = internal dso_local global [64784 x i8] zeroinitializer, align 16
@__compressedAssemblyData_37 = internal dso_local global [20752 x i8] zeroinitializer, align 16
@__compressedAssemblyData_38 = internal dso_local global [16696 x i8] zeroinitializer, align 16
@__compressedAssemblyData_39 = internal dso_local global [96560 x i8] zeroinitializer, align 16
@__compressedAssemblyData_40 = internal dso_local global [121616 x i8] zeroinitializer, align 16
@__compressedAssemblyData_41 = internal dso_local global [16144 x i8] zeroinitializer, align 16
@__compressedAssemblyData_42 = internal dso_local global [15632 x i8] zeroinitializer, align 16
@__compressedAssemblyData_43 = internal dso_local global [16144 x i8] zeroinitializer, align 16
@__compressedAssemblyData_44 = internal dso_local global [41232 x i8] zeroinitializer, align 16
@__compressedAssemblyData_45 = internal dso_local global [15624 x i8] zeroinitializer, align 16
@__compressedAssemblyData_46 = internal dso_local global [38160 x i8] zeroinitializer, align 16
@__compressedAssemblyData_47 = internal dso_local global [110344 x i8] zeroinitializer, align 16
@__compressedAssemblyData_48 = internal dso_local global [32568 x i8] zeroinitializer, align 16
@__compressedAssemblyData_49 = internal dso_local global [48400 x i8] zeroinitializer, align 16
@__compressedAssemblyData_50 = internal dso_local global [15632 x i8] zeroinitializer, align 16
@__compressedAssemblyData_51 = internal dso_local global [55088 x i8] zeroinitializer, align 16
@__compressedAssemblyData_52 = internal dso_local global [16144 x i8] zeroinitializer, align 16
@__compressedAssemblyData_53 = internal dso_local global [43832 x i8] zeroinitializer, align 16
@__compressedAssemblyData_54 = internal dso_local global [48952 x i8] zeroinitializer, align 16
@__compressedAssemblyData_55 = internal dso_local global [78640 x i8] zeroinitializer, align 16
@__compressedAssemblyData_56 = internal dso_local global [23816 x i8] zeroinitializer, align 16
@__compressedAssemblyData_57 = internal dso_local global [67888 x i8] zeroinitializer, align 16
@__compressedAssemblyData_58 = internal dso_local global [15664 x i8] zeroinitializer, align 16
@__compressedAssemblyData_59 = internal dso_local global [16136 x i8] zeroinitializer, align 16
@__compressedAssemblyData_60 = internal dso_local global [575752 x i8] zeroinitializer, align 16
@__compressedAssemblyData_61 = internal dso_local global [223496 x i8] zeroinitializer, align 16
@__compressedAssemblyData_62 = internal dso_local global [76552 x i8] zeroinitializer, align 16
@__compressedAssemblyData_63 = internal dso_local global [149264 x i8] zeroinitializer, align 16
@__compressedAssemblyData_64 = internal dso_local global [56120 x i8] zeroinitializer, align 16
@__compressedAssemblyData_65 = internal dso_local global [56592 x i8] zeroinitializer, align 16
@__compressedAssemblyData_66 = internal dso_local global [676664 x i8] zeroinitializer, align 16
@__compressedAssemblyData_67 = internal dso_local global [131896 x i8] zeroinitializer, align 16
@__compressedAssemblyData_68 = internal dso_local global [174904 x i8] zeroinitializer, align 16
@__compressedAssemblyData_69 = internal dso_local global [51976 x i8] zeroinitializer, align 16
@__compressedAssemblyData_70 = internal dso_local global [66320 x i8] zeroinitializer, align 16
@__compressedAssemblyData_71 = internal dso_local global [56080 x i8] zeroinitializer, align 16
@__compressedAssemblyData_72 = internal dso_local global [107280 x i8] zeroinitializer, align 16
@__compressedAssemblyData_73 = internal dso_local global [173360 x i8] zeroinitializer, align 16
@__compressedAssemblyData_74 = internal dso_local global [162104 x i8] zeroinitializer, align 16
@__compressedAssemblyData_75 = internal dso_local global [253752 x i8] zeroinitializer, align 16
@__compressedAssemblyData_76 = internal dso_local global [15624 x i8] zeroinitializer, align 16
@__compressedAssemblyData_77 = internal dso_local global [235280 x i8] zeroinitializer, align 16
@__compressedAssemblyData_78 = internal dso_local global [70928 x i8] zeroinitializer, align 16
@__compressedAssemblyData_79 = internal dso_local global [33584 x i8] zeroinitializer, align 16
@__compressedAssemblyData_80 = internal dso_local global [23864 x i8] zeroinitializer, align 16
@__compressedAssemblyData_81 = internal dso_local global [51976 x i8] zeroinitializer, align 16
@__compressedAssemblyData_82 = internal dso_local global [103176 x i8] zeroinitializer, align 16
@__compressedAssemblyData_83 = internal dso_local global [17680 x i8] zeroinitializer, align 16
@__compressedAssemblyData_84 = internal dso_local global [16144 x i8] zeroinitializer, align 16
@__compressedAssemblyData_85 = internal dso_local global [15672 x i8] zeroinitializer, align 16
@__compressedAssemblyData_86 = internal dso_local global [41776 x i8] zeroinitializer, align 16
@__compressedAssemblyData_87 = internal dso_local global [852272 x i8] zeroinitializer, align 16
@__compressedAssemblyData_88 = internal dso_local global [103216 x i8] zeroinitializer, align 16
@__compressedAssemblyData_89 = internal dso_local global [153872 x i8] zeroinitializer, align 16
@__compressedAssemblyData_90 = internal dso_local global [3099920 x i8] zeroinitializer, align 16
@__compressedAssemblyData_91 = internal dso_local global [38704 x i8] zeroinitializer, align 16
@__compressedAssemblyData_92 = internal dso_local global [16136 x i8] zeroinitializer, align 16
@__compressedAssemblyData_93 = internal dso_local global [16144 x i8] zeroinitializer, align 16
@__compressedAssemblyData_94 = internal dso_local global [130352 x i8] zeroinitializer, align 16
@__compressedAssemblyData_95 = internal dso_local global [15632 x i8] zeroinitializer, align 16
@__compressedAssemblyData_96 = internal dso_local global [501520 x i8] zeroinitializer, align 16
@__compressedAssemblyData_97 = internal dso_local global [16144 x i8] zeroinitializer, align 16
@__compressedAssemblyData_98 = internal dso_local global [24336 x i8] zeroinitializer, align 16
@__compressedAssemblyData_99 = internal dso_local global [16656 x i8] zeroinitializer, align 16
@__compressedAssemblyData_100 = internal dso_local global [15664 x i8] zeroinitializer, align 16
@__compressedAssemblyData_101 = internal dso_local global [16144 x i8] zeroinitializer, align 16
@__compressedAssemblyData_102 = internal dso_local global [26896 x i8] zeroinitializer, align 16
@__compressedAssemblyData_103 = internal dso_local global [15632 x i8] zeroinitializer, align 16
@__compressedAssemblyData_104 = internal dso_local global [17720 x i8] zeroinitializer, align 16
@__compressedAssemblyData_105 = internal dso_local global [18224 x i8] zeroinitializer, align 16
@__compressedAssemblyData_106 = internal dso_local global [15672 x i8] zeroinitializer, align 16
@__compressedAssemblyData_107 = internal dso_local global [38672 x i8] zeroinitializer, align 16
@__compressedAssemblyData_108 = internal dso_local global [15624 x i8] zeroinitializer, align 16
@__compressedAssemblyData_109 = internal dso_local global [64816 x i8] zeroinitializer, align 16
@__compressedAssemblyData_110 = internal dso_local global [17680 x i8] zeroinitializer, align 16
@__compressedAssemblyData_111 = internal dso_local global [16136 x i8] zeroinitializer, align 16
@__compressedAssemblyData_112 = internal dso_local global [143632 x i8] zeroinitializer, align 16
@__compressedAssemblyData_113 = internal dso_local global [66360 x i8] zeroinitializer, align 16
@__compressedAssemblyData_114 = internal dso_local global [16144 x i8] zeroinitializer, align 16
@__compressedAssemblyData_115 = internal dso_local global [23824 x i8] zeroinitializer, align 16
@__compressedAssemblyData_116 = internal dso_local global [17168 x i8] zeroinitializer, align 16
@__compressedAssemblyData_117 = internal dso_local global [17168 x i8] zeroinitializer, align 16
@__compressedAssemblyData_118 = internal dso_local global [44816 x i8] zeroinitializer, align 16
@__compressedAssemblyData_119 = internal dso_local global [58632 x i8] zeroinitializer, align 16
@__compressedAssemblyData_120 = internal dso_local global [54024 x i8] zeroinitializer, align 16
@__compressedAssemblyData_121 = internal dso_local global [17680 x i8] zeroinitializer, align 16
@__compressedAssemblyData_122 = internal dso_local global [16696 x i8] zeroinitializer, align 16
@__compressedAssemblyData_123 = internal dso_local global [16176 x i8] zeroinitializer, align 16
@__compressedAssemblyData_124 = internal dso_local global [16144 x i8] zeroinitializer, align 16
@__compressedAssemblyData_125 = internal dso_local global [15672 x i8] zeroinitializer, align 16
@__compressedAssemblyData_126 = internal dso_local global [16144 x i8] zeroinitializer, align 16
@__compressedAssemblyData_127 = internal dso_local global [17200 x i8] zeroinitializer, align 16
@__compressedAssemblyData_128 = internal dso_local global [705296 x i8] zeroinitializer, align 16
@__compressedAssemblyData_129 = internal dso_local global [38152 x i8] zeroinitializer, align 16
@__compressedAssemblyData_130 = internal dso_local global [15664 x i8] zeroinitializer, align 16
@__compressedAssemblyData_131 = internal dso_local global [15632 x i8] zeroinitializer, align 16
@__compressedAssemblyData_132 = internal dso_local global [18744 x i8] zeroinitializer, align 16
@__compressedAssemblyData_133 = internal dso_local global [17200 x i8] zeroinitializer, align 16
@__compressedAssemblyData_134 = internal dso_local global [16176 x i8] zeroinitializer, align 16
@__compressedAssemblyData_135 = internal dso_local global [741168 x i8] zeroinitializer, align 16
@__compressedAssemblyData_136 = internal dso_local global [16144 x i8] zeroinitializer, align 16
@__compressedAssemblyData_137 = internal dso_local global [16144 x i8] zeroinitializer, align 16
@__compressedAssemblyData_138 = internal dso_local global [70416 x i8] zeroinitializer, align 16
@__compressedAssemblyData_139 = internal dso_local global [617736 x i8] zeroinitializer, align 16
@__compressedAssemblyData_140 = internal dso_local global [369424 x i8] zeroinitializer, align 16
@__compressedAssemblyData_141 = internal dso_local global [57096 x i8] zeroinitializer, align 16
@__compressedAssemblyData_142 = internal dso_local global [16144 x i8] zeroinitializer, align 16
@__compressedAssemblyData_143 = internal dso_local global [186120 x i8] zeroinitializer, align 16
@__compressedAssemblyData_144 = internal dso_local global [16136 x i8] zeroinitializer, align 16
@__compressedAssemblyData_145 = internal dso_local global [61712 x i8] zeroinitializer, align 16
@__compressedAssemblyData_146 = internal dso_local global [17200 x i8] zeroinitializer, align 16
@__compressedAssemblyData_147 = internal dso_local global [16184 x i8] zeroinitializer, align 16
@__compressedAssemblyData_148 = internal dso_local global [16136 x i8] zeroinitializer, align 16
@__compressedAssemblyData_149 = internal dso_local global [15632 x i8] zeroinitializer, align 16
@__compressedAssemblyData_150 = internal dso_local global [45360 x i8] zeroinitializer, align 16
@__compressedAssemblyData_151 = internal dso_local global [175928 x i8] zeroinitializer, align 16
@__compressedAssemblyData_152 = internal dso_local global [16696 x i8] zeroinitializer, align 16
@__compressedAssemblyData_153 = internal dso_local global [15664 x i8] zeroinitializer, align 16
@__compressedAssemblyData_154 = internal dso_local global [30992 x i8] zeroinitializer, align 16
@__compressedAssemblyData_155 = internal dso_local global [15624 x i8] zeroinitializer, align 16
@__compressedAssemblyData_156 = internal dso_local global [16144 x i8] zeroinitializer, align 16
@__compressedAssemblyData_157 = internal dso_local global [16184 x i8] zeroinitializer, align 16
@__compressedAssemblyData_158 = internal dso_local global [22328 x i8] zeroinitializer, align 16
@__compressedAssemblyData_159 = internal dso_local global [16696 x i8] zeroinitializer, align 16
@__compressedAssemblyData_160 = internal dso_local global [16144 x i8] zeroinitializer, align 16
@__compressedAssemblyData_161 = internal dso_local global [16144 x i8] zeroinitializer, align 16
@__compressedAssemblyData_162 = internal dso_local global [16144 x i8] zeroinitializer, align 16
@__compressedAssemblyData_163 = internal dso_local global [16136 x i8] zeroinitializer, align 16
@__compressedAssemblyData_164 = internal dso_local global [18192 x i8] zeroinitializer, align 16
@__compressedAssemblyData_165 = internal dso_local global [23824 x i8] zeroinitializer, align 16
@__compressedAssemblyData_166 = internal dso_local global [50960 x i8] zeroinitializer, align 16
@__compressedAssemblyData_167 = internal dso_local global [16656 x i8] zeroinitializer, align 16
@__compressedAssemblyData_168 = internal dso_local global [60176 x i8] zeroinitializer, align 16
@__compressedAssemblyData_169 = internal dso_local global [101136 x i8] zeroinitializer, align 16
@__compressedAssemblyData_170 = internal dso_local global [240184 x i8] zeroinitializer, align 16
@__compressedAssemblyData_171 = internal dso_local global [82976 x i8] zeroinitializer, align 16
@__compressedAssemblyData_172 = internal dso_local global [19008 x i8] zeroinitializer, align 16
@__compressedAssemblyData_173 = internal dso_local global [37449272 x i8] zeroinitializer, align 16
@__compressedAssemblyData_174 = internal dso_local global [4777264 x i8] zeroinitializer, align 16

; Metadata
!llvm.module.flags = !{!0, !1}
!0 = !{i32 1, !"wchar_size", i32 4}
!1 = !{i32 7, !"PIC Level", i32 2}
!llvm.ident = !{!2}
!2 = !{!".NET for Android remotes/origin/release/9.0.1xx @ 9abff7703206541fdb83ffa80fe2c2753ad1997b"}
!3 = !{!4, !4, i64 0}
!4 = !{!"any pointer", !5, i64 0}
!5 = !{!"omnipotent char", !6, i64 0}
!6 = !{!"Simple C++ TBAA"}
