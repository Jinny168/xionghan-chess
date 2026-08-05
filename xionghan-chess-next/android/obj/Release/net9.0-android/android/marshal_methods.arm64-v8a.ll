; ModuleID = 'marshal_methods.arm64-v8a.ll'
source_filename = "marshal_methods.arm64-v8a.ll"
target datalayout = "e-m:e-i8:8:32-i16:16:32-i64:64-i128:128-n32:64-S128"
target triple = "aarch64-unknown-linux-android21"

%struct.MarshalMethodName = type {
	i64, ; uint64_t id
	ptr ; char* name
}

%struct.MarshalMethodsManagedClass = type {
	i32, ; uint32_t token
	ptr ; MonoClass klass
}

@assembly_image_cache = dso_local local_unnamed_addr global [10 x ptr] zeroinitializer, align 8

; Each entry maps hash of an assembly name to an index into the `assembly_image_cache` array
@assembly_image_cache_hashes = dso_local local_unnamed_addr constant [30 x i64] [
	i64 u0x02abedc11addc1ed, ; 0: lib_Mono.Android.Runtime.dll.so => 8
	i64 u0x0c59ad9fbbd43abe, ; 1: Mono.Android => 9
	i64 u0x13f1e5e209e91af4, ; 2: lib_Java.Interop.dll.so => 7
	i64 u0x1c753b5ff15bce1b, ; 3: Mono.Android.Runtime.dll => 8
	i64 u0x2174319c0d835bc9, ; 4: System.Runtime => 5
	i64 u0x2407aef2bbe8fadf, ; 5: System.Console => 2
	i64 u0x27b410442fad6cf1, ; 6: Java.Interop.dll => 7
	i64 u0x2a22dd561c691232, ; 7: lib_XionghanChessAndroid.dll.so => 1
	i64 u0x31195fef5d8fb552, ; 8: _Microsoft.Android.Resource.Designer.dll => 0
	i64 u0x434c4e1d9284cdae, ; 9: Mono.Android.dll => 9
	i64 u0x4e32f00cb0937401, ; 10: Mono.Android.Runtime => 8
	i64 u0x54795225dd1587af, ; 11: lib_System.Runtime.dll.so => 5
	i64 u0x579a06fed6eec900, ; 12: System.Private.CoreLib.dll => 6
	i64 u0x5db0cbbd1028510e, ; 13: lib_System.Runtime.InteropServices.dll.so => 4
	i64 u0x622eef6f9e59068d, ; 14: System.Private.CoreLib => 6
	i64 u0x6692e924eade1b29, ; 15: lib_System.Console.dll.so => 2
	i64 u0x6a4d7577b2317255, ; 16: System.Runtime.InteropServices.dll => 4
	i64 u0x903101b46fb73a04, ; 17: _Microsoft.Android.Resource.Designer => 0
	i64 u0x903e26bb5318b54d, ; 18: XionghanChessAndroid => 1
	i64 u0x90bf7ce1f703819e, ; 19: XionghanChessAndroid.dll => 1
	i64 u0x91a74f07b30d37e2, ; 20: System.Linq.dll => 3
	i64 u0xae282bcd03739de7, ; 21: Java.Interop => 7
	i64 u0xb81a2c6e0aee50fe, ; 22: lib_System.Private.CoreLib.dll.so => 6
	i64 u0xc0d928351ab5ca77, ; 23: System.Console.dll => 2
	i64 u0xc12b8b3afa48329c, ; 24: lib_System.Linq.dll.so => 3
	i64 u0xcbd4fdd9cef4a294, ; 25: lib__Microsoft.Android.Resource.Designer.dll.so => 0
	i64 u0xd333d0af9e423810, ; 26: System.Runtime.InteropServices => 4
	i64 u0xdbf9607a441b4505, ; 27: System.Linq => 3
	i64 u0xdd2b722d78ef5f43, ; 28: System.Runtime.dll => 5
	i64 u0xe5434e8a119ceb69 ; 29: lib_Mono.Android.dll.so => 9
], align 8

@assembly_image_cache_indices = dso_local local_unnamed_addr constant [30 x i32] [
	i32 8, i32 9, i32 7, i32 8, i32 5, i32 2, i32 7, i32 1,
	i32 0, i32 9, i32 8, i32 5, i32 6, i32 4, i32 6, i32 2,
	i32 4, i32 0, i32 1, i32 1, i32 3, i32 7, i32 6, i32 2,
	i32 3, i32 0, i32 4, i32 3, i32 5, i32 9
], align 4

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
@.str.0 = private unnamed_addr constant [40 x i8] c"get_function_pointer MUST be specified\0A\00", align 1

;MarshalMethodName
@.MarshalMethodName.0_name = private unnamed_addr constant [1 x i8] c"\00", align 1

; External functions

; Function attributes: "no-trapping-math"="true" noreturn nounwind "stack-protector-buffer-size"="8"
declare void @abort() local_unnamed_addr #2

; Function attributes: nofree nounwind
declare noundef i32 @puts(ptr noundef) local_unnamed_addr #1
attributes #0 = { memory(write, argmem: none, inaccessiblemem: none) "min-legal-vector-width"="0" mustprogress "no-trapping-math"="true" nofree norecurse nosync nounwind "stack-protector-buffer-size"="8" "target-cpu"="generic" "target-features"="+fix-cortex-a53-835769,+neon,+outline-atomics,+v8a" uwtable willreturn }
attributes #1 = { nofree nounwind }
attributes #2 = { "no-trapping-math"="true" noreturn nounwind "stack-protector-buffer-size"="8" "target-cpu"="generic" "target-features"="+fix-cortex-a53-835769,+neon,+outline-atomics,+v8a" }

; Metadata
!llvm.module.flags = !{!0, !1, !7, !8, !9, !10}
!0 = !{i32 1, !"wchar_size", i32 4}
!1 = !{i32 7, !"PIC Level", i32 2}
!llvm.ident = !{!2}
!2 = !{!".NET for Android remotes/origin/release/9.0.1xx @ 9abff7703206541fdb83ffa80fe2c2753ad1997b"}
!3 = !{!4, !4, i64 0}
!4 = !{!"any pointer", !5, i64 0}
!5 = !{!"omnipotent char", !6, i64 0}
!6 = !{!"Simple C++ TBAA"}
!7 = !{i32 1, !"branch-target-enforcement", i32 0}
!8 = !{i32 1, !"sign-return-address", i32 0}
!9 = !{i32 1, !"sign-return-address-all", i32 0}
!10 = !{i32 1, !"sign-return-address-with-bkey", i32 0}
