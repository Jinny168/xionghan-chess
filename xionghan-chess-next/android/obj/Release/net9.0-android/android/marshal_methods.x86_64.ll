; ModuleID = 'marshal_methods.x86_64.ll'
source_filename = "marshal_methods.x86_64.ll"
target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"
target triple = "x86_64-unknown-linux-android21"

%struct.MarshalMethodName = type {
	i64, ; uint64_t id
	ptr ; char* name
}

%struct.MarshalMethodsManagedClass = type {
	i32, ; uint32_t token
	ptr ; MonoClass klass
}

@assembly_image_cache = dso_local local_unnamed_addr global [27 x ptr] zeroinitializer, align 16

; Each entry maps hash of an assembly name to an index into the `assembly_image_cache` array
@assembly_image_cache_hashes = dso_local local_unnamed_addr constant [81 x i64] [
	i64 u0x02abedc11addc1ed, ; 0: lib_Mono.Android.Runtime.dll.so => 25
	i64 u0x0517ef04e06e9f76, ; 1: System.Net.Primitives => 12
	i64 u0x0581db89237110e9, ; 2: lib_System.Collections.dll.so => 4
	i64 u0x07dcdc7460a0c5e4, ; 3: System.Collections.NonGeneric => 3
	i64 u0x092266563089ae3e, ; 4: lib_System.Collections.NonGeneric.dll.so => 3
	i64 u0x09d144a7e214d457, ; 5: System.Security.Cryptography => 19
	i64 u0x0c59ad9fbbd43abe, ; 6: Mono.Android => 26
	i64 u0x10f6cfcbcf801616, ; 7: System.IO.Compression.Brotli => 8
	i64 u0x13f1e5e209e91af4, ; 8: lib_Java.Interop.dll.so => 23
	i64 u0x1a91866a319e9259, ; 9: lib_System.Collections.Concurrent.dll.so => 2
	i64 u0x1c753b5ff15bce1b, ; 10: Mono.Android.Runtime.dll => 25
	i64 u0x209375905fcc1bad, ; 11: lib_System.IO.Compression.Brotli.dll.so => 8
	i64 u0x2174319c0d835bc9, ; 12: System.Runtime => 18
	i64 u0x2407aef2bbe8fadf, ; 13: System.Console => 5
	i64 u0x27b410442fad6cf1, ; 14: Java.Interop.dll => 23
	i64 u0x2801845a2c71fbfb, ; 15: System.Net.Primitives.dll => 12
	i64 u0x2a22dd561c691232, ; 16: lib_XionghanChessAndroid.dll.so => 1
	i64 u0x2af298f63581d886, ; 17: System.Text.RegularExpressions.dll => 21
	i64 u0x2afc1c4f898552ee, ; 18: lib_System.Formats.Asn1.dll.so => 7
	i64 u0x31195fef5d8fb552, ; 19: _Microsoft.Android.Resource.Designer.dll => 0
	i64 u0x3b860f9932505633, ; 20: lib_System.Text.Encoding.Extensions.dll.so => 20
	i64 u0x434c4e1d9284cdae, ; 21: Mono.Android.dll => 26
	i64 u0x4d55a010ffc4faff, ; 22: System.Private.Xml => 15
	i64 u0x4e32f00cb0937401, ; 23: Mono.Android.Runtime => 25
	i64 u0x526ce79eb8e90527, ; 24: lib_System.Net.Primitives.dll.so => 12
	i64 u0x54795225dd1587af, ; 25: lib_System.Runtime.dll.so => 18
	i64 u0x571c5cfbec5ae8e2, ; 26: System.Private.Uri => 14
	i64 u0x579a06fed6eec900, ; 27: System.Private.CoreLib.dll => 22
	i64 u0x57c542c14049b66d, ; 28: System.Diagnostics.DiagnosticSource => 6
	i64 u0x5db0cbbd1028510e, ; 29: lib_System.Runtime.InteropServices.dll.so => 16
	i64 u0x622eef6f9e59068d, ; 30: System.Private.CoreLib => 22
	i64 u0x65ece51227bfa724, ; 31: lib_System.Runtime.Numerics.dll.so => 17
	i64 u0x6692e924eade1b29, ; 32: lib_System.Console.dll.so => 5
	i64 u0x68fbbbe2eb455198, ; 33: System.Formats.Asn1 => 7
	i64 u0x6a4d7577b2317255, ; 34: System.Runtime.InteropServices.dll => 16
	i64 u0x76ca07b878f44da0, ; 35: System.Runtime.Numerics.dll => 17
	i64 u0x7dfc3d6d9d8d7b70, ; 36: System.Collections => 4
	i64 u0x87f6569b25707834, ; 37: System.IO.Compression.Brotli.dll => 8
	i64 u0x8b4ff5d0fdd5faa1, ; 38: lib_System.Diagnostics.DiagnosticSource.dll.so => 6
	i64 u0x8da188285aadfe8e, ; 39: System.Collections.Concurrent => 2
	i64 u0x903101b46fb73a04, ; 40: _Microsoft.Android.Resource.Designer => 0
	i64 u0x90393bd4865292f3, ; 41: lib_System.IO.Compression.dll.so => 9
	i64 u0x903e26bb5318b54d, ; 42: XionghanChessAndroid => 1
	i64 u0x90bf7ce1f703819e, ; 43: XionghanChessAndroid.dll => 1
	i64 u0x91a74f07b30d37e2, ; 44: System.Linq.dll => 10
	i64 u0x944077d8ca3c6580, ; 45: System.IO.Compression.dll => 9
	i64 u0x97e144c9d3c6976e, ; 46: System.Collections.Concurrent.dll => 2
	i64 u0xa0d8259f4cc284ec, ; 47: lib_System.Security.Cryptography.dll.so => 19
	i64 u0xa5f1ba49b85dd355, ; 48: System.Security.Cryptography.dll => 19
	i64 u0xa7eab29ed44b4e7a, ; 49: Mono.Android.Export => 24
	i64 u0xaa443ac34067eeef, ; 50: System.Private.Xml.dll => 15
	i64 u0xaa52de307ef5d1dd, ; 51: System.Net.Http => 11
	i64 u0xac2af3fa195a15ce, ; 52: System.Runtime.Numerics => 17
	i64 u0xae282bcd03739de7, ; 53: Java.Interop => 23
	i64 u0xb220631954820169, ; 54: System.Text.RegularExpressions => 21
	i64 u0xb81a2c6e0aee50fe, ; 55: lib_System.Private.CoreLib.dll.so => 22
	i64 u0xba48785529705af9, ; 56: System.Collections.dll => 4
	i64 u0xbd0e2c0d55246576, ; 57: System.Net.Http.dll => 11
	i64 u0xc0d928351ab5ca77, ; 58: System.Console.dll => 5
	i64 u0xc12b8b3afa48329c, ; 59: lib_System.Linq.dll.so => 10
	i64 u0xc2902f6cf5452577, ; 60: lib_Mono.Android.Export.dll.so => 24
	i64 u0xc519125d6bc8fb11, ; 61: lib_System.Net.Requests.dll.so => 13
	i64 u0xc5325b2fcb37446f, ; 62: lib_System.Private.Xml.dll.so => 15
	i64 u0xc5a0f4b95a699af7, ; 63: lib_System.Private.Uri.dll.so => 14
	i64 u0xc7c01e7d7c93a110, ; 64: System.Text.Encoding.Extensions.dll => 20
	i64 u0xcbd4fdd9cef4a294, ; 65: lib__Microsoft.Android.Resource.Designer.dll.so => 0
	i64 u0xcc2876b32ef2794c, ; 66: lib_System.Text.RegularExpressions.dll.so => 21
	i64 u0xcd10a42808629144, ; 67: System.Net.Requests => 13
	i64 u0xcf23d8093f3ceadf, ; 68: System.Diagnostics.DiagnosticSource.dll => 6
	i64 u0xd333d0af9e423810, ; 69: System.Runtime.InteropServices => 16
	i64 u0xd3651b6fc3125825, ; 70: System.Private.Uri.dll => 14
	i64 u0xdad05a11827959a3, ; 71: System.Collections.NonGeneric.dll => 3
	i64 u0xdbf9607a441b4505, ; 72: System.Linq => 10
	i64 u0xdd2b722d78ef5f43, ; 73: System.Runtime.dll => 18
	i64 u0xe2420585aeceb728, ; 74: System.Net.Requests.dll => 13
	i64 u0xe332bacb3eb4a806, ; 75: Mono.Android.Export.dll => 24
	i64 u0xe5434e8a119ceb69, ; 76: lib_Mono.Android.dll.so => 26
	i64 u0xf1c4b4005493d871, ; 77: System.Formats.Asn1.dll => 7
	i64 u0xf4c1dd70a5496a17, ; 78: System.IO.Compression => 9
	i64 u0xfbf0a31c9fc34bc4, ; 79: lib_System.Net.Http.dll.so => 11
	i64 u0xfd536c702f64dc47 ; 80: System.Text.Encoding.Extensions => 20
], align 16

@assembly_image_cache_indices = dso_local local_unnamed_addr constant [81 x i32] [
	i32 25, i32 12, i32 4, i32 3, i32 3, i32 19, i32 26, i32 8,
	i32 23, i32 2, i32 25, i32 8, i32 18, i32 5, i32 23, i32 12,
	i32 1, i32 21, i32 7, i32 0, i32 20, i32 26, i32 15, i32 25,
	i32 12, i32 18, i32 14, i32 22, i32 6, i32 16, i32 22, i32 17,
	i32 5, i32 7, i32 16, i32 17, i32 4, i32 8, i32 6, i32 2,
	i32 0, i32 9, i32 1, i32 1, i32 10, i32 9, i32 2, i32 19,
	i32 19, i32 24, i32 15, i32 11, i32 17, i32 23, i32 21, i32 22,
	i32 4, i32 11, i32 5, i32 10, i32 24, i32 13, i32 15, i32 14,
	i32 20, i32 0, i32 21, i32 13, i32 6, i32 16, i32 14, i32 3,
	i32 10, i32 18, i32 13, i32 24, i32 26, i32 7, i32 9, i32 11,
	i32 20
], align 16

@marshal_methods_number_of_classes = dso_local local_unnamed_addr constant i32 0, align 4

@marshal_methods_class_cache = dso_local local_unnamed_addr global [0 x %struct.MarshalMethodsManagedClass] zeroinitializer, align 8

; Names of classes in which marshal methods reside
@mm_class_names = dso_local local_unnamed_addr constant [0 x ptr] zeroinitializer, align 8

@mm_method_names = dso_local local_unnamed_addr constant [1 x %struct.MarshalMethodName] [
	%struct.MarshalMethodName {
		i64 u0x0000000000000000, ; name: 
		ptr @.MarshalMethodName.0_name; char* name
	} ; 0
], align 8

; get_function_pointer (uint32_t mono_image_index, uint32_t class_index, uint32_t method_token, void*& target_ptr)
@get_function_pointer = internal dso_local unnamed_addr global ptr null, align 8

; Functions

; Function attributes: memory(write, argmem: none, inaccessiblemem: none) "min-legal-vector-width"="0" mustprogress "no-trapping-math"="true" nofree norecurse nosync nounwind "stack-protector-buffer-size"="8" uwtable willreturn
define void @xamarin_app_init(ptr nocapture noundef readnone %env, ptr noundef %fn) local_unnamed_addr #0
{
	%fnIsNull = icmp eq ptr %fn, null
	br i1 %fnIsNull, label %1, label %2

1: ; preds = %0
	%putsResult = call noundef i32 @puts(ptr @.str.0)
	call void @abort()
	unreachable 

2: ; preds = %1, %0
	store ptr %fn, ptr @get_function_pointer, align 8, !tbaa !3
	ret void
}

; Strings
@.str.0 = private unnamed_addr constant [40 x i8] c"get_function_pointer MUST be specified\0A\00", align 16

;MarshalMethodName
@.MarshalMethodName.0_name = private unnamed_addr constant [1 x i8] c"\00", align 1

; External functions

; Function attributes: "no-trapping-math"="true" noreturn nounwind "stack-protector-buffer-size"="8"
declare void @abort() local_unnamed_addr #2

; Function attributes: nofree nounwind
declare noundef i32 @puts(ptr noundef) local_unnamed_addr #1
attributes #0 = { memory(write, argmem: none, inaccessiblemem: none) "min-legal-vector-width"="0" mustprogress "no-trapping-math"="true" nofree norecurse nosync nounwind "stack-protector-buffer-size"="8" "target-cpu"="x86-64" "target-features"="+crc32,+cx16,+cx8,+fxsr,+mmx,+popcnt,+sse,+sse2,+sse3,+sse4.1,+sse4.2,+ssse3,+x87" "tune-cpu"="generic" uwtable willreturn }
attributes #1 = { nofree nounwind }
attributes #2 = { "no-trapping-math"="true" noreturn nounwind "stack-protector-buffer-size"="8" "target-cpu"="x86-64" "target-features"="+crc32,+cx16,+cx8,+fxsr,+mmx,+popcnt,+sse,+sse2,+sse3,+sse4.1,+sse4.2,+ssse3,+x87" "tune-cpu"="generic" }

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
