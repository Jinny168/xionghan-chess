; ModuleID = 'typemaps.x86_64.ll'
source_filename = "typemaps.x86_64.ll"
target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"
target triple = "x86_64-unknown-linux-android21"

%struct.TypeMapJava = type {
	i32, ; uint32_t module_index
	i32, ; uint32_t type_token_id
	i32 ; uint32_t java_name_index
}

%struct.TypeMapModule = type {
	[16 x i8], ; uint8_t module_uuid[16]
	i32, ; uint32_t entry_count
	i32, ; uint32_t duplicate_count
	ptr, ; TypeMapModuleEntry map
	ptr, ; TypeMapModuleEntry duplicate_map
	ptr, ; char* assembly_name
	ptr, ; MonoImage image
	i32, ; uint32_t java_name_width
	ptr ; uint8_t java_map
}

%struct.TypeMapModuleEntry = type {
	i32, ; uint32_t type_token_id
	i32 ; uint32_t java_map_index
}

@map_module_count = dso_local local_unnamed_addr constant i32 2, align 4

@java_type_count = dso_local local_unnamed_addr constant i32 172, align 4

; Managed modules map
@map_modules = dso_local local_unnamed_addr global [2 x %struct.TypeMapModule] [
	%struct.TypeMapModule {
		[16 x i8] [ i8 u0xd6, i8 u0xe8, i8 u0xbf, i8 u0x01, i8 u0x4f, i8 u0x8d, i8 u0x4d, i8 u0x47, i8 u0x9f, i8 u0x5b, i8 u0x3c, i8 u0x71, i8 u0x4f, i8 u0x17, i8 u0x42, i8 u0x4f ], ; module_uuid: 01bfe8d6-8d4f-474d-9f5b-3c714f17424f
		i32 168, ; uint32_t entry_count
		i32 71, ; uint32_t duplicate_count
		ptr @module0_managed_to_java, ; TypeMapModuleEntry* map
		ptr @module0_managed_to_java_duplicates, ; TypeMapModuleEntry* duplicate_map
		ptr @.TypeMapModule.0_assembly_name, ; assembly_name: Mono.Android
		ptr null, ; MonoImage* image
		i32 0, ; uint32_t java_name_width
		ptr null; uint8_t* java_map
	}, ; 0
	%struct.TypeMapModule {
		[16 x i8] [ i8 u0xe1, i8 u0x80, i8 u0x9b, i8 u0x66, i8 u0x0c, i8 u0xb7, i8 u0xa7, i8 u0x42, i8 u0x85, i8 u0x37, i8 u0x2a, i8 u0xdd, i8 u0xf8, i8 u0x07, i8 u0xae, i8 u0x4f ], ; module_uuid: 669b80e1-b70c-42a7-8537-2addf807ae4f
		i32 4, ; uint32_t entry_count
		i32 0, ; uint32_t duplicate_count
		ptr @module1_managed_to_java, ; TypeMapModuleEntry* map
		ptr null, ; TypeMapModuleEntry* duplicate_map
		ptr @.TypeMapModule.1_assembly_name, ; assembly_name: XionghanChessAndroid
		ptr null, ; MonoImage* image
		i32 0, ; uint32_t java_name_width
		ptr null; uint8_t* java_map
	} ; 1
], align 16

; Java types name hashes
@map_java_hashes = dso_local local_unnamed_addr constant [172 x i64] [
	i64 u0x013d70f30586d278, ; 0 => javax/net/ssl/KeyManagerFactory
	i64 u0x01cd624f1e38cc9f, ; 1 => java/lang/Byte
	i64 u0x024025cba700002c, ; 2 => crc64f6f2b5806e9afa0f/MainActivity_GameWebChromeClient
	i64 u0x03cc98b851d4262c, ; 3 => javax/net/ssl/SSLContext
	i64 u0x06f84afe4273c430, ; 4 => java/net/InetSocketAddress
	i64 u0x083e83bb2321dd50, ; 5 => java/util/Random
	i64 u0x0a364502506e12a9, ; 6 => android/os/CancellationSignal
	i64 u0x0a49aab6fb8903b8, ; 7 => android/app/ActionBar
	i64 u0x0b1da699fb29019a, ; 8 => android/os/BaseBundle
	i64 u0x0c44130caa233945, ; 9 => mono/android/runtime/JavaObject
	i64 u0x0d9335f0988cd796, ; 10 => java/util/HashMap
	i64 u0x106be7c89662702e, ; 11 => java/net/Proxy$Type
	i64 u0x10cc64dc53558d33, ; 12 => android/content/ComponentName
	i64 u0x10e015905ca8bd0f, ; 13 => java/security/cert/Certificate
	i64 u0x110217f9f8accd72, ; 14 => android/view/WindowInsetsController
	i64 u0x116532ec07ee0771, ; 15 => java/security/spec/KeySpec
	i64 u0x13e5902d3b855db6, ; 16 => javax/net/ssl/TrustManagerFactory
	i64 u0x167be582da7ac6ee, ; 17 => android/view/WindowInsetsController$OnControllableInsetsChangedListener
	i64 u0x1950fac852291891, ; 18 => android/view/WindowInsetsAnimationControlListener
	i64 u0x1e04bf19f9c14045, ; 19 => android/util/AttributeSet
	i64 u0x1e549855226528a2, ; 20 => java/io/InterruptedIOException
	i64 u0x1e69018626ef9ffb, ; 21 => android/os/Handler
	i64 u0x1e957b3efd87ae08, ; 22 => android/content/res/ColorStateList
	i64 u0x21b381333982058e, ; 23 => javax/net/SocketFactory
	i64 u0x225c20a45cb91cd7, ; 24 => java/lang/Error
	i64 u0x228edb5145b4bbc1, ; 25 => android/view/InputEvent
	i64 u0x246d328253b69617, ; 26 => crc64f6f2b5806e9afa0f/MainActivity
	i64 u0x250f0166bb46cb93, ; 27 => android/webkit/WebChromeClient
	i64 u0x2a15272bf231e341, ; 28 => android/widget/EditText
	i64 u0x2bcca4a8219ac237, ; 29 => javax/security/cert/X509Certificate
	i64 u0x2bd1ad3b5c2d27f0, ; 30 => android/graphics/BlendMode
	i64 u0x2ff9fb2c70f4f954, ; 31 => java/lang/SecurityException
	i64 u0x3068b2cc16f39dc1, ; 32 => android/view/ContextMenu$ContextMenuInfo
	i64 u0x32d6a1d6ee9f6d5a, ; 33 => android/content/Intent
	i64 u0x332031975eda7654, ; 34 => java/lang/Boolean
	i64 u0x33446dc637a16331, ; 35 => android/view/Menu
	i64 u0x3436cf09b45d055e, ; 36 => java/security/Principal
	i64 u0x354fcde9fba66be0, ; 37 => android/content/DialogInterface$OnClickListener
	i64 u0x35e989807a64bcd9, ; 38 => java/lang/IllegalStateException
	i64 u0x3611feb7c92af67a, ; 39 => android/content/SharedPreferences$Editor
	i64 u0x406e54c64b3bee74, ; 40 => android/runtime/JavaProxyThrowable
	i64 u0x40c05cff47992547, ; 41 => android/view/ViewGroup
	i64 u0x41ac0ab939dc266a, ; 42 => android/view/MenuItem$OnActionExpandListener
	i64 u0x41d091ef7039ab94, ; 43 => java/net/URLConnection
	i64 u0x4209344bc1b095c1, ; 44 => java/net/ProtocolException
	i64 u0x4768ffd64bb01691, ; 45 => android/view/WindowInsets$Type
	i64 u0x48e1abb584b78c94, ; 46 => java/io/Writer
	i64 u0x498ba0971d83ce0a, ; 47 => android/content/res/XmlResourceParser
	i64 u0x4a39213a97fe1b2f, ; 48 => java/net/ConnectException
	i64 u0x4d5913834f8ec110, ; 49 => android/content/DialogInterface
	i64 u0x50d702ac1a779d77, ; 50 => mono/android/content/DialogInterface_OnClickListenerImplementor
	i64 u0x510b4a194e70a8b9, ; 51 => android/webkit/WebChromeClient$FileChooserParams
	i64 u0x516bd5763f07d608, ; 52 => android/net/Uri
	i64 u0x5181b129b1a25949, ; 53 => java/lang/Class
	i64 u0x5238ad63b58da994, ; 54 => java/lang/ClassCastException
	i64 u0x529e559bd64e4c22, ; 55 => javax/net/ssl/HttpsURLConnection
	i64 u0x551ac881eb4466c0, ; 56 => java/lang/Number
	i64 u0x55f72f5bdbb6740d, ; 57 => android/webkit/WebResourceRequest
	i64 u0x56365290d5a06704, ; 58 => java/lang/LinkageError
	i64 u0x57fe4a40460344db, ; 59 => android/os/Build$VERSION
	i64 u0x5a6af884fe3c181e, ; 60 => android/os/Bundle
	i64 u0x5b905726d9bc975f, ; 61 => android/widget/TextView
	i64 u0x5bfd65ae1a6e6ffc, ; 62 => android/app/Activity
	i64 u0x5c9a08d12cd9a5b9, ; 63 => android/view/ActionProvider
	i64 u0x5e1c513312ebc1b3, ; 64 => android/view/KeyEvent
	i64 u0x5f5a9fc3430795a4, ; 65 => android/content/ContextWrapper
	i64 u0x5f7e709faf8646e0, ; 66 => java/lang/Short
	i64 u0x6219335ac57fb821, ; 67 => java/io/Serializable
	i64 u0x6531c3e6b4a10d86, ; 68 => android/app/AlertDialog$Builder
	i64 u0x65b48068a8beab4c, ; 69 => org/xmlpull/v1/XmlPullParserException
	i64 u0x65f6b14b7e978927, ; 70 => java/io/IOException
	i64 u0x683ec3c5964ae14b, ; 71 => android/view/MenuItem$OnMenuItemClickListener
	i64 u0x6aa7d9af28b4551f, ; 72 => java/net/SocketTimeoutException
	i64 u0x6e0fb15bd0f04d15, ; 73 => java/lang/StackTraceElement
	i64 u0x6e23edb7ba3b4ddb, ; 74 => android/runtime/XmlReaderResourceParser
	i64 u0x714152b8b4c7f7d6, ; 75 => java/security/KeyFactory
	i64 u0x71a366471b83c5b5, ; 76 => android/graphics/PorterDuff$Mode
	i64 u0x720cd712e1248c34, ; 77 => java/util/Iterator
	i64 u0x75591c18ddf5e52d, ; 78 => mono/android/TypeManager
	i64 u0x763c2670ea45f55c, ; 79 => android/graphics/drawable/Drawable
	i64 u0x76cbd2104dd555ed, ; 80 => android/content/Context
	i64 u0x76cd544434e023e9, ; 81 => android/widget/AbsoluteLayout
	i64 u0x786e5a40bb3c74ca, ; 82 => android/webkit/ValueCallback
	i64 u0x79b8e6ed4e0962cc, ; 83 => android/webkit/WebView
	i64 u0x7b3aeb75b65cbd49, ; 84 => java/security/spec/PKCS8EncodedKeySpec
	i64 u0x7b925bdca68a0101, ; 85 => java/util/ArrayList
	i64 u0x7c93df30f68cf9a7, ; 86 => javax/security/auth/Subject
	i64 u0x7fc6286783d5249d, ; 87 => java/security/Key
	i64 u0x7fd6b531797aa365, ; 88 => java/net/URL
	i64 u0x83314b5931a387fb, ; 89 => android/widget/Toast
	i64 u0x84f94178aab6cc34, ; 90 => java/lang/CharSequence
	i64 u0x888700b03d541d93, ; 91 => java/lang/RuntimeException
	i64 u0x88f7510c649f4a97, ; 92 => java/io/InputStream
	i64 u0x8a1927818aa18084, ; 93 => javax/net/ssl/KeyManager
	i64 u0x8a3ea3c274e8ce68, ; 94 => java/lang/Character
	i64 u0x90b4aeb45636cd6a, ; 95 => mono/android/runtime/OutputStreamAdapter
	i64 u0x92188d393e2af2d2, ; 96 => java/lang/Throwable
	i64 u0x92b59c839bc46278, ; 97 => java/lang/Thread
	i64 u0x9461b0401dbcf96c, ; 98 => android/app/Dialog
	i64 u0x965bfaf1ff1da014, ; 99 => java/lang/ReflectiveOperationException
	i64 u0x98ba110c6c57da31, ; 100 => java/lang/Float
	i64 u0x99df91bab800c287, ; 101 => mono/android/runtime/InputStreamAdapter
	i64 u0x9e10a0b3efa170dc, ; 102 => android/view/ContextThemeWrapper
	i64 u0x9e6dc3e8eedaf8a8, ; 103 => java/net/SocketException
	i64 u0x9e8497fc52a96d4d, ; 104 => android/graphics/PorterDuff
	i64 u0x9fa1370a1b1093fa, ; 105 => java/lang/NullPointerException
	i64 u0xa07cbd8408019386, ; 106 => java/net/Proxy
	i64 u0xa24d07cd0d5c4f0f, ; 107 => android/animation/TimeInterpolator
	i64 u0xa59db4b8b7dbe046, ; 108 => javax/net/ssl/SSLSession
	i64 u0xa865adbdd81d9951, ; 109 => java/io/OutputStream
	i64 u0xa86f66387eaee170, ; 110 => android/content/SharedPreferences
	i64 u0xa95eae500754348a, ; 111 => java/net/SocketAddress
	i64 u0xaa75ead031784774, ; 112 => javax/net/ssl/SSLSocketFactory
	i64 u0xabc3cd0f40f748aa, ; 113 => java/lang/String
	i64 u0xabe6d6ebc681adc2, ; 114 => android/runtime/XmlReaderPullParser
	i64 u0xac9902bb0e4c5217, ; 115 => java/lang/IllegalArgumentException
	i64 u0xacbf549cdef93bef, ; 116 => java/net/HttpURLConnection
	i64 u0xb02badeb1c97535c, ; 117 => java/lang/Integer
	i64 u0xb18d71343ca8e96f, ; 118 => java/lang/Exception
	i64 u0xb209d55b71ead22c, ; 119 => android/view/animation/Interpolator
	i64 u0xb374dc7d92c34054, ; 120 => android/webkit/WebViewClient
	i64 u0xb43bff1eb757d5fb, ; 121 => org/xmlpull/v1/XmlPullParser
	i64 u0xb4fc3e21cc054bc7, ; 122 => android/graphics/Paint
	i64 u0xb56e3efa284790aa, ; 123 => android/view/WindowInsets
	i64 u0xb7f60ace3fa0816b, ; 124 => android/view/Window
	i64 u0xb8df224d6b778ca3, ; 125 => android/view/View
	i64 u0xb9e48b25660487c5, ; 126 => javax/net/ssl/TrustManager
	i64 u0xbb388df3745ca0e0, ; 127 => android/content/ActivityNotFoundException
	i64 u0xbb84ccbe48f6c18b, ; 128 => android/os/Looper
	i64 u0xbc23f0c88f3b93bb, ; 129 => android/webkit/WebResourceError
	i64 u0xbf6d427143271cb3, ; 130 => java/lang/Object
	i64 u0xbf9dae2beff68075, ; 131 => android/graphics/Insets
	i64 u0xc00f4c2f11efdcff, ; 132 => java/lang/ClassNotFoundException
	i64 u0xc288a8550f7ef636, ; 133 => android/view/SubMenu
	i64 u0xc2a8e50a5f08afc6, ; 134 => mono/java/lang/RunnableImplementor
	i64 u0xc2d2916e08f7fcd5, ; 135 => android/view/WindowInsetsAnimationController
	i64 u0xc3eb0cbb47f178b9, ; 136 => java/lang/Enum
	i64 u0xc99e090e60d66f58, ; 137 => java/io/StringWriter
	i64 u0xca35caf567cfa745, ; 138 => java/util/Collection
	i64 u0xcc306823503920e9, ; 139 => android/app/Application
	i64 u0xcdf4fe3b1db1eeb0, ; 140 => android/view/MenuItem
	i64 u0xd1b288a9c7bb8f53, ; 141 => java/lang/Double
	i64 u0xd202c8ea2a504e12, ; 142 => android/webkit/WebSettings
	i64 u0xd39c770b67de9183, ; 143 => android/app/AlertDialog
	i64 u0xd5a28b8fa6d48e71, ; 144 => android/os/Build
	i64 u0xd6880b1e41bf57b5, ; 145 => java/io/Reader
	i64 u0xdbb76cb30e7b6509, ; 146 => android/content/ContentResolver
	i64 u0xdd812f1d4afa427b, ; 147 => java/lang/UnsupportedOperationException
	i64 u0xde36efb42da7cc2d, ; 148 => javax/net/ssl/SSLSessionContext
	i64 u0xe024b538ad65ea66, ; 149 => java/util/function/Consumer
	i64 u0xe0446bf91fb0c2dd, ; 150 => java/lang/NoClassDefFoundError
	i64 u0xe1b3c5871398eb28, ; 151 => java/nio/channels/FileChannel
	i64 u0xe28cd0a2e6de00c1, ; 152 => java/security/KeyStore
	i64 u0xe3e37676779b8a30, ; 153 => crc64f6f2b5806e9afa0f/MainActivity_GameWebViewClient
	i64 u0xe59c130e7d1e4ac3, ; 154 => java/security/SecureRandom
	i64 u0xeb82145dcac4c559, ; 155 => java/lang/Long
	i64 u0xed3bf28f37177c87, ; 156 => android/content/SharedPreferences$OnSharedPreferenceChangeListener
	i64 u0xed49ed70aa9be1b3, ; 157 => java/nio/channels/spi/AbstractInterruptibleChannel
	i64 u0xee58348f4c4ad939, ; 158 => javax/net/ssl/HostnameVerifier
	i64 u0xee6f3d1e7507d907, ; 159 => java/util/Enumeration
	i64 u0xef2f2996a1d369cc, ; 160 => java/io/FileInputStream
	i64 u0xef953c41325a3428, ; 161 => java/io/PrintWriter
	i64 u0xefd8c7aa4b48418e, ; 162 => android/widget/LinearLayout
	i64 u0xf11f22a6441fcfbc, ; 163 => java/lang/IndexOutOfBoundsException
	i64 u0xf38608385d689955, ; 164 => mono/android/runtime/JavaArray
	i64 u0xf3d4ab08aaf25ccb, ; 165 => java/net/UnknownServiceException
	i64 u0xf85cbededb432844, ; 166 => java/security/spec/EncodedKeySpec
	i64 u0xf8a713f30367c25e, ; 167 => crc64f6f2b5806e9afa0f/MainActivity_GameBridge
	i64 u0xfb9a51a22eb2843f, ; 168 => javax/security/cert/Certificate
	i64 u0xfbe9bfa5cc50fed6, ; 169 => java/util/HashSet
	i64 u0xfd2b1a3de667eb51, ; 170 => java/lang/Runnable
	i64 u0xfebf2b77f1940e7e ; 171 => java/security/PrivateKey
], align 16

@module0_managed_to_java = internal dso_local constant [168 x %struct.TypeMapModuleEntry] [
	%struct.TypeMapModuleEntry {
		i32 u0x0200006f, ; uint32_t type_token_id
		i32 121; uint32_t java_map_index
	}, ; 0
	%struct.TypeMapModuleEntry {
		i32 u0x02000071, ; uint32_t type_token_id
		i32 69; uint32_t java_map_index
	}, ; 1
	%struct.TypeMapModuleEntry {
		i32 u0x02000073, ; uint32_t type_token_id
		i32 168; uint32_t java_map_index
	}, ; 2
	%struct.TypeMapModuleEntry {
		i32 u0x02000075, ; uint32_t type_token_id
		i32 29; uint32_t java_map_index
	}, ; 3
	%struct.TypeMapModuleEntry {
		i32 u0x02000077, ; uint32_t type_token_id
		i32 86; uint32_t java_map_index
	}, ; 4
	%struct.TypeMapModuleEntry {
		i32 u0x02000078, ; uint32_t type_token_id
		i32 23; uint32_t java_map_index
	}, ; 5
	%struct.TypeMapModuleEntry {
		i32 u0x0200007a, ; uint32_t type_token_id
		i32 55; uint32_t java_map_index
	}, ; 6
	%struct.TypeMapModuleEntry {
		i32 u0x0200007c, ; uint32_t type_token_id
		i32 158; uint32_t java_map_index
	}, ; 7
	%struct.TypeMapModuleEntry {
		i32 u0x0200007e, ; uint32_t type_token_id
		i32 93; uint32_t java_map_index
	}, ; 8
	%struct.TypeMapModuleEntry {
		i32 u0x02000080, ; uint32_t type_token_id
		i32 108; uint32_t java_map_index
	}, ; 9
	%struct.TypeMapModuleEntry {
		i32 u0x02000082, ; uint32_t type_token_id
		i32 148; uint32_t java_map_index
	}, ; 10
	%struct.TypeMapModuleEntry {
		i32 u0x02000084, ; uint32_t type_token_id
		i32 126; uint32_t java_map_index
	}, ; 11
	%struct.TypeMapModuleEntry {
		i32 u0x02000086, ; uint32_t type_token_id
		i32 0; uint32_t java_map_index
	}, ; 12
	%struct.TypeMapModuleEntry {
		i32 u0x02000087, ; uint32_t type_token_id
		i32 3; uint32_t java_map_index
	}, ; 13
	%struct.TypeMapModuleEntry {
		i32 u0x02000088, ; uint32_t type_token_id
		i32 112; uint32_t java_map_index
	}, ; 14
	%struct.TypeMapModuleEntry {
		i32 u0x0200008a, ; uint32_t type_token_id
		i32 16; uint32_t java_map_index
	}, ; 15
	%struct.TypeMapModuleEntry {
		i32 u0x0200008b, ; uint32_t type_token_id
		i32 82; uint32_t java_map_index
	}, ; 16
	%struct.TypeMapModuleEntry {
		i32 u0x0200008d, ; uint32_t type_token_id
		i32 57; uint32_t java_map_index
	}, ; 17
	%struct.TypeMapModuleEntry {
		i32 u0x02000091, ; uint32_t type_token_id
		i32 27; uint32_t java_map_index
	}, ; 18
	%struct.TypeMapModuleEntry {
		i32 u0x02000092, ; uint32_t type_token_id
		i32 51; uint32_t java_map_index
	}, ; 19
	%struct.TypeMapModuleEntry {
		i32 u0x02000094, ; uint32_t type_token_id
		i32 129; uint32_t java_map_index
	}, ; 20
	%struct.TypeMapModuleEntry {
		i32 u0x02000096, ; uint32_t type_token_id
		i32 142; uint32_t java_map_index
	}, ; 21
	%struct.TypeMapModuleEntry {
		i32 u0x02000098, ; uint32_t type_token_id
		i32 83; uint32_t java_map_index
	}, ; 22
	%struct.TypeMapModuleEntry {
		i32 u0x02000099, ; uint32_t type_token_id
		i32 120; uint32_t java_map_index
	}, ; 23
	%struct.TypeMapModuleEntry {
		i32 u0x0200009a, ; uint32_t type_token_id
		i32 61; uint32_t java_map_index
	}, ; 24
	%struct.TypeMapModuleEntry {
		i32 u0x0200009b, ; uint32_t type_token_id
		i32 81; uint32_t java_map_index
	}, ; 25
	%struct.TypeMapModuleEntry {
		i32 u0x0200009c, ; uint32_t type_token_id
		i32 28; uint32_t java_map_index
	}, ; 26
	%struct.TypeMapModuleEntry {
		i32 u0x0200009d, ; uint32_t type_token_id
		i32 162; uint32_t java_map_index
	}, ; 27
	%struct.TypeMapModuleEntry {
		i32 u0x0200009f, ; uint32_t type_token_id
		i32 89; uint32_t java_map_index
	}, ; 28
	%struct.TypeMapModuleEntry {
		i32 u0x020000a1, ; uint32_t type_token_id
		i32 19; uint32_t java_map_index
	}, ; 29
	%struct.TypeMapModuleEntry {
		i32 u0x020000a3, ; uint32_t type_token_id
		i32 21; uint32_t java_map_index
	}, ; 30
	%struct.TypeMapModuleEntry {
		i32 u0x020000a4, ; uint32_t type_token_id
		i32 8; uint32_t java_map_index
	}, ; 31
	%struct.TypeMapModuleEntry {
		i32 u0x020000a5, ; uint32_t type_token_id
		i32 144; uint32_t java_map_index
	}, ; 32
	%struct.TypeMapModuleEntry {
		i32 u0x020000a6, ; uint32_t type_token_id
		i32 59; uint32_t java_map_index
	}, ; 33
	%struct.TypeMapModuleEntry {
		i32 u0x020000a8, ; uint32_t type_token_id
		i32 60; uint32_t java_map_index
	}, ; 34
	%struct.TypeMapModuleEntry {
		i32 u0x020000a9, ; uint32_t type_token_id
		i32 6; uint32_t java_map_index
	}, ; 35
	%struct.TypeMapModuleEntry {
		i32 u0x020000aa, ; uint32_t type_token_id
		i32 128; uint32_t java_map_index
	}, ; 36
	%struct.TypeMapModuleEntry {
		i32 u0x020000ab, ; uint32_t type_token_id
		i32 107; uint32_t java_map_index
	}, ; 37
	%struct.TypeMapModuleEntry {
		i32 u0x020000ad, ; uint32_t type_token_id
		i32 125; uint32_t java_map_index
	}, ; 38
	%struct.TypeMapModuleEntry {
		i32 u0x020000ae, ; uint32_t type_token_id
		i32 64; uint32_t java_map_index
	}, ; 39
	%struct.TypeMapModuleEntry {
		i32 u0x020000af, ; uint32_t type_token_id
		i32 124; uint32_t java_map_index
	}, ; 40
	%struct.TypeMapModuleEntry {
		i32 u0x020000b0, ; uint32_t type_token_id
		i32 63; uint32_t java_map_index
	}, ; 41
	%struct.TypeMapModuleEntry {
		i32 u0x020000b2, ; uint32_t type_token_id
		i32 102; uint32_t java_map_index
	}, ; 42
	%struct.TypeMapModuleEntry {
		i32 u0x020000b3, ; uint32_t type_token_id
		i32 32; uint32_t java_map_index
	}, ; 43
	%struct.TypeMapModuleEntry {
		i32 u0x020000b5, ; uint32_t type_token_id
		i32 35; uint32_t java_map_index
	}, ; 44
	%struct.TypeMapModuleEntry {
		i32 u0x020000b8, ; uint32_t type_token_id
		i32 42; uint32_t java_map_index
	}, ; 45
	%struct.TypeMapModuleEntry {
		i32 u0x020000ba, ; uint32_t type_token_id
		i32 71; uint32_t java_map_index
	}, ; 46
	%struct.TypeMapModuleEntry {
		i32 u0x020000bc, ; uint32_t type_token_id
		i32 140; uint32_t java_map_index
	}, ; 47
	%struct.TypeMapModuleEntry {
		i32 u0x020000be, ; uint32_t type_token_id
		i32 25; uint32_t java_map_index
	}, ; 48
	%struct.TypeMapModuleEntry {
		i32 u0x020000c0, ; uint32_t type_token_id
		i32 133; uint32_t java_map_index
	}, ; 49
	%struct.TypeMapModuleEntry {
		i32 u0x020000c2, ; uint32_t type_token_id
		i32 135; uint32_t java_map_index
	}, ; 50
	%struct.TypeMapModuleEntry {
		i32 u0x020000c4, ; uint32_t type_token_id
		i32 18; uint32_t java_map_index
	}, ; 51
	%struct.TypeMapModuleEntry {
		i32 u0x020000c6, ; uint32_t type_token_id
		i32 14; uint32_t java_map_index
	}, ; 52
	%struct.TypeMapModuleEntry {
		i32 u0x020000c7, ; uint32_t type_token_id
		i32 17; uint32_t java_map_index
	}, ; 53
	%struct.TypeMapModuleEntry {
		i32 u0x020000d0, ; uint32_t type_token_id
		i32 41; uint32_t java_map_index
	}, ; 54
	%struct.TypeMapModuleEntry {
		i32 u0x020000d3, ; uint32_t type_token_id
		i32 123; uint32_t java_map_index
	}, ; 55
	%struct.TypeMapModuleEntry {
		i32 u0x020000d4, ; uint32_t type_token_id
		i32 45; uint32_t java_map_index
	}, ; 56
	%struct.TypeMapModuleEntry {
		i32 u0x020000d5, ; uint32_t type_token_id
		i32 119; uint32_t java_map_index
	}, ; 57
	%struct.TypeMapModuleEntry {
		i32 u0x020000eb, ; uint32_t type_token_id
		i32 101; uint32_t java_map_index
	}, ; 58
	%struct.TypeMapModuleEntry {
		i32 u0x020000ee, ; uint32_t type_token_id
		i32 164; uint32_t java_map_index
	}, ; 59
	%struct.TypeMapModuleEntry {
		i32 u0x020000f0, ; uint32_t type_token_id
		i32 138; uint32_t java_map_index
	}, ; 60
	%struct.TypeMapModuleEntry {
		i32 u0x020000f2, ; uint32_t type_token_id
		i32 10; uint32_t java_map_index
	}, ; 61
	%struct.TypeMapModuleEntry {
		i32 u0x020000fb, ; uint32_t type_token_id
		i32 85; uint32_t java_map_index
	}, ; 62
	%struct.TypeMapModuleEntry {
		i32 u0x020000fd, ; uint32_t type_token_id
		i32 9; uint32_t java_map_index
	}, ; 63
	%struct.TypeMapModuleEntry {
		i32 u0x020000fe, ; uint32_t type_token_id
		i32 40; uint32_t java_map_index
	}, ; 64
	%struct.TypeMapModuleEntry {
		i32 u0x020000ff, ; uint32_t type_token_id
		i32 169; uint32_t java_map_index
	}, ; 65
	%struct.TypeMapModuleEntry {
		i32 u0x0200010b, ; uint32_t type_token_id
		i32 95; uint32_t java_map_index
	}, ; 66
	%struct.TypeMapModuleEntry {
		i32 u0x02000113, ; uint32_t type_token_id
		i32 74; uint32_t java_map_index
	}, ; 67
	%struct.TypeMapModuleEntry {
		i32 u0x02000114, ; uint32_t type_token_id
		i32 114; uint32_t java_map_index
	}, ; 68
	%struct.TypeMapModuleEntry {
		i32 u0x02000115, ; uint32_t type_token_id
		i32 52; uint32_t java_map_index
	}, ; 69
	%struct.TypeMapModuleEntry {
		i32 u0x02000119, ; uint32_t type_token_id
		i32 30; uint32_t java_map_index
	}, ; 70
	%struct.TypeMapModuleEntry {
		i32 u0x0200011a, ; uint32_t type_token_id
		i32 131; uint32_t java_map_index
	}, ; 71
	%struct.TypeMapModuleEntry {
		i32 u0x0200011b, ; uint32_t type_token_id
		i32 122; uint32_t java_map_index
	}, ; 72
	%struct.TypeMapModuleEntry {
		i32 u0x0200011c, ; uint32_t type_token_id
		i32 104; uint32_t java_map_index
	}, ; 73
	%struct.TypeMapModuleEntry {
		i32 u0x0200011d, ; uint32_t type_token_id
		i32 76; uint32_t java_map_index
	}, ; 74
	%struct.TypeMapModuleEntry {
		i32 u0x0200011e, ; uint32_t type_token_id
		i32 79; uint32_t java_map_index
	}, ; 75
	%struct.TypeMapModuleEntry {
		i32 u0x02000120, ; uint32_t type_token_id
		i32 80; uint32_t java_map_index
	}, ; 76
	%struct.TypeMapModuleEntry {
		i32 u0x02000121, ; uint32_t type_token_id
		i32 33; uint32_t java_map_index
	}, ; 77
	%struct.TypeMapModuleEntry {
		i32 u0x02000122, ; uint32_t type_token_id
		i32 127; uint32_t java_map_index
	}, ; 78
	%struct.TypeMapModuleEntry {
		i32 u0x02000123, ; uint32_t type_token_id
		i32 12; uint32_t java_map_index
	}, ; 79
	%struct.TypeMapModuleEntry {
		i32 u0x02000124, ; uint32_t type_token_id
		i32 146; uint32_t java_map_index
	}, ; 80
	%struct.TypeMapModuleEntry {
		i32 u0x02000127, ; uint32_t type_token_id
		i32 65; uint32_t java_map_index
	}, ; 81
	%struct.TypeMapModuleEntry {
		i32 u0x02000129, ; uint32_t type_token_id
		i32 37; uint32_t java_map_index
	}, ; 82
	%struct.TypeMapModuleEntry {
		i32 u0x0200012c, ; uint32_t type_token_id
		i32 50; uint32_t java_map_index
	}, ; 83
	%struct.TypeMapModuleEntry {
		i32 u0x0200012d, ; uint32_t type_token_id
		i32 49; uint32_t java_map_index
	}, ; 84
	%struct.TypeMapModuleEntry {
		i32 u0x0200012f, ; uint32_t type_token_id
		i32 39; uint32_t java_map_index
	}, ; 85
	%struct.TypeMapModuleEntry {
		i32 u0x02000131, ; uint32_t type_token_id
		i32 156; uint32_t java_map_index
	}, ; 86
	%struct.TypeMapModuleEntry {
		i32 u0x02000133, ; uint32_t type_token_id
		i32 110; uint32_t java_map_index
	}, ; 87
	%struct.TypeMapModuleEntry {
		i32 u0x02000135, ; uint32_t type_token_id
		i32 47; uint32_t java_map_index
	}, ; 88
	%struct.TypeMapModuleEntry {
		i32 u0x02000136, ; uint32_t type_token_id
		i32 22; uint32_t java_map_index
	}, ; 89
	%struct.TypeMapModuleEntry {
		i32 u0x0200013a, ; uint32_t type_token_id
		i32 7; uint32_t java_map_index
	}, ; 90
	%struct.TypeMapModuleEntry {
		i32 u0x0200013b, ; uint32_t type_token_id
		i32 62; uint32_t java_map_index
	}, ; 91
	%struct.TypeMapModuleEntry {
		i32 u0x0200013c, ; uint32_t type_token_id
		i32 143; uint32_t java_map_index
	}, ; 92
	%struct.TypeMapModuleEntry {
		i32 u0x0200013d, ; uint32_t type_token_id
		i32 68; uint32_t java_map_index
	}, ; 93
	%struct.TypeMapModuleEntry {
		i32 u0x0200013e, ; uint32_t type_token_id
		i32 139; uint32_t java_map_index
	}, ; 94
	%struct.TypeMapModuleEntry {
		i32 u0x0200013f, ; uint32_t type_token_id
		i32 98; uint32_t java_map_index
	}, ; 95
	%struct.TypeMapModuleEntry {
		i32 u0x02000145, ; uint32_t type_token_id
		i32 48; uint32_t java_map_index
	}, ; 96
	%struct.TypeMapModuleEntry {
		i32 u0x02000147, ; uint32_t type_token_id
		i32 116; uint32_t java_map_index
	}, ; 97
	%struct.TypeMapModuleEntry {
		i32 u0x02000149, ; uint32_t type_token_id
		i32 4; uint32_t java_map_index
	}, ; 98
	%struct.TypeMapModuleEntry {
		i32 u0x0200014a, ; uint32_t type_token_id
		i32 44; uint32_t java_map_index
	}, ; 99
	%struct.TypeMapModuleEntry {
		i32 u0x0200014b, ; uint32_t type_token_id
		i32 106; uint32_t java_map_index
	}, ; 100
	%struct.TypeMapModuleEntry {
		i32 u0x0200014c, ; uint32_t type_token_id
		i32 11; uint32_t java_map_index
	}, ; 101
	%struct.TypeMapModuleEntry {
		i32 u0x0200014d, ; uint32_t type_token_id
		i32 111; uint32_t java_map_index
	}, ; 102
	%struct.TypeMapModuleEntry {
		i32 u0x0200014f, ; uint32_t type_token_id
		i32 103; uint32_t java_map_index
	}, ; 103
	%struct.TypeMapModuleEntry {
		i32 u0x02000150, ; uint32_t type_token_id
		i32 72; uint32_t java_map_index
	}, ; 104
	%struct.TypeMapModuleEntry {
		i32 u0x02000151, ; uint32_t type_token_id
		i32 165; uint32_t java_map_index
	}, ; 105
	%struct.TypeMapModuleEntry {
		i32 u0x02000152, ; uint32_t type_token_id
		i32 88; uint32_t java_map_index
	}, ; 106
	%struct.TypeMapModuleEntry {
		i32 u0x02000153, ; uint32_t type_token_id
		i32 43; uint32_t java_map_index
	}, ; 107
	%struct.TypeMapModuleEntry {
		i32 u0x02000155, ; uint32_t type_token_id
		i32 87; uint32_t java_map_index
	}, ; 108
	%struct.TypeMapModuleEntry {
		i32 u0x02000157, ; uint32_t type_token_id
		i32 36; uint32_t java_map_index
	}, ; 109
	%struct.TypeMapModuleEntry {
		i32 u0x02000159, ; uint32_t type_token_id
		i32 171; uint32_t java_map_index
	}, ; 110
	%struct.TypeMapModuleEntry {
		i32 u0x0200015b, ; uint32_t type_token_id
		i32 75; uint32_t java_map_index
	}, ; 111
	%struct.TypeMapModuleEntry {
		i32 u0x0200015c, ; uint32_t type_token_id
		i32 152; uint32_t java_map_index
	}, ; 112
	%struct.TypeMapModuleEntry {
		i32 u0x0200015d, ; uint32_t type_token_id
		i32 154; uint32_t java_map_index
	}, ; 113
	%struct.TypeMapModuleEntry {
		i32 u0x0200015e, ; uint32_t type_token_id
		i32 166; uint32_t java_map_index
	}, ; 114
	%struct.TypeMapModuleEntry {
		i32 u0x02000160, ; uint32_t type_token_id
		i32 15; uint32_t java_map_index
	}, ; 115
	%struct.TypeMapModuleEntry {
		i32 u0x02000162, ; uint32_t type_token_id
		i32 84; uint32_t java_map_index
	}, ; 116
	%struct.TypeMapModuleEntry {
		i32 u0x02000163, ; uint32_t type_token_id
		i32 13; uint32_t java_map_index
	}, ; 117
	%struct.TypeMapModuleEntry {
		i32 u0x02000165, ; uint32_t type_token_id
		i32 151; uint32_t java_map_index
	}, ; 118
	%struct.TypeMapModuleEntry {
		i32 u0x02000167, ; uint32_t type_token_id
		i32 157; uint32_t java_map_index
	}, ; 119
	%struct.TypeMapModuleEntry {
		i32 u0x02000169, ; uint32_t type_token_id
		i32 160; uint32_t java_map_index
	}, ; 120
	%struct.TypeMapModuleEntry {
		i32 u0x0200016a, ; uint32_t type_token_id
		i32 92; uint32_t java_map_index
	}, ; 121
	%struct.TypeMapModuleEntry {
		i32 u0x0200016c, ; uint32_t type_token_id
		i32 20; uint32_t java_map_index
	}, ; 122
	%struct.TypeMapModuleEntry {
		i32 u0x0200016d, ; uint32_t type_token_id
		i32 70; uint32_t java_map_index
	}, ; 123
	%struct.TypeMapModuleEntry {
		i32 u0x0200016e, ; uint32_t type_token_id
		i32 67; uint32_t java_map_index
	}, ; 124
	%struct.TypeMapModuleEntry {
		i32 u0x02000170, ; uint32_t type_token_id
		i32 109; uint32_t java_map_index
	}, ; 125
	%struct.TypeMapModuleEntry {
		i32 u0x02000172, ; uint32_t type_token_id
		i32 161; uint32_t java_map_index
	}, ; 126
	%struct.TypeMapModuleEntry {
		i32 u0x02000173, ; uint32_t type_token_id
		i32 145; uint32_t java_map_index
	}, ; 127
	%struct.TypeMapModuleEntry {
		i32 u0x02000175, ; uint32_t type_token_id
		i32 137; uint32_t java_map_index
	}, ; 128
	%struct.TypeMapModuleEntry {
		i32 u0x02000176, ; uint32_t type_token_id
		i32 46; uint32_t java_map_index
	}, ; 129
	%struct.TypeMapModuleEntry {
		i32 u0x02000178, ; uint32_t type_token_id
		i32 159; uint32_t java_map_index
	}, ; 130
	%struct.TypeMapModuleEntry {
		i32 u0x0200017a, ; uint32_t type_token_id
		i32 77; uint32_t java_map_index
	}, ; 131
	%struct.TypeMapModuleEntry {
		i32 u0x0200017c, ; uint32_t type_token_id
		i32 5; uint32_t java_map_index
	}, ; 132
	%struct.TypeMapModuleEntry {
		i32 u0x0200017d, ; uint32_t type_token_id
		i32 149; uint32_t java_map_index
	}, ; 133
	%struct.TypeMapModuleEntry {
		i32 u0x0200017f, ; uint32_t type_token_id
		i32 34; uint32_t java_map_index
	}, ; 134
	%struct.TypeMapModuleEntry {
		i32 u0x02000180, ; uint32_t type_token_id
		i32 1; uint32_t java_map_index
	}, ; 135
	%struct.TypeMapModuleEntry {
		i32 u0x02000181, ; uint32_t type_token_id
		i32 94; uint32_t java_map_index
	}, ; 136
	%struct.TypeMapModuleEntry {
		i32 u0x02000182, ; uint32_t type_token_id
		i32 53; uint32_t java_map_index
	}, ; 137
	%struct.TypeMapModuleEntry {
		i32 u0x02000183, ; uint32_t type_token_id
		i32 132; uint32_t java_map_index
	}, ; 138
	%struct.TypeMapModuleEntry {
		i32 u0x02000184, ; uint32_t type_token_id
		i32 141; uint32_t java_map_index
	}, ; 139
	%struct.TypeMapModuleEntry {
		i32 u0x02000185, ; uint32_t type_token_id
		i32 118; uint32_t java_map_index
	}, ; 140
	%struct.TypeMapModuleEntry {
		i32 u0x02000186, ; uint32_t type_token_id
		i32 100; uint32_t java_map_index
	}, ; 141
	%struct.TypeMapModuleEntry {
		i32 u0x02000187, ; uint32_t type_token_id
		i32 90; uint32_t java_map_index
	}, ; 142
	%struct.TypeMapModuleEntry {
		i32 u0x02000188, ; uint32_t type_token_id
		i32 117; uint32_t java_map_index
	}, ; 143
	%struct.TypeMapModuleEntry {
		i32 u0x02000189, ; uint32_t type_token_id
		i32 155; uint32_t java_map_index
	}, ; 144
	%struct.TypeMapModuleEntry {
		i32 u0x0200018a, ; uint32_t type_token_id
		i32 130; uint32_t java_map_index
	}, ; 145
	%struct.TypeMapModuleEntry {
		i32 u0x0200018b, ; uint32_t type_token_id
		i32 91; uint32_t java_map_index
	}, ; 146
	%struct.TypeMapModuleEntry {
		i32 u0x0200018c, ; uint32_t type_token_id
		i32 66; uint32_t java_map_index
	}, ; 147
	%struct.TypeMapModuleEntry {
		i32 u0x0200018d, ; uint32_t type_token_id
		i32 113; uint32_t java_map_index
	}, ; 148
	%struct.TypeMapModuleEntry {
		i32 u0x0200018f, ; uint32_t type_token_id
		i32 97; uint32_t java_map_index
	}, ; 149
	%struct.TypeMapModuleEntry {
		i32 u0x02000190, ; uint32_t type_token_id
		i32 134; uint32_t java_map_index
	}, ; 150
	%struct.TypeMapModuleEntry {
		i32 u0x02000191, ; uint32_t type_token_id
		i32 96; uint32_t java_map_index
	}, ; 151
	%struct.TypeMapModuleEntry {
		i32 u0x02000192, ; uint32_t type_token_id
		i32 54; uint32_t java_map_index
	}, ; 152
	%struct.TypeMapModuleEntry {
		i32 u0x02000193, ; uint32_t type_token_id
		i32 136; uint32_t java_map_index
	}, ; 153
	%struct.TypeMapModuleEntry {
		i32 u0x02000195, ; uint32_t type_token_id
		i32 24; uint32_t java_map_index
	}, ; 154
	%struct.TypeMapModuleEntry {
		i32 u0x02000198, ; uint32_t type_token_id
		i32 115; uint32_t java_map_index
	}, ; 155
	%struct.TypeMapModuleEntry {
		i32 u0x02000199, ; uint32_t type_token_id
		i32 38; uint32_t java_map_index
	}, ; 156
	%struct.TypeMapModuleEntry {
		i32 u0x0200019a, ; uint32_t type_token_id
		i32 163; uint32_t java_map_index
	}, ; 157
	%struct.TypeMapModuleEntry {
		i32 u0x0200019b, ; uint32_t type_token_id
		i32 170; uint32_t java_map_index
	}, ; 158
	%struct.TypeMapModuleEntry {
		i32 u0x0200019d, ; uint32_t type_token_id
		i32 58; uint32_t java_map_index
	}, ; 159
	%struct.TypeMapModuleEntry {
		i32 u0x0200019e, ; uint32_t type_token_id
		i32 150; uint32_t java_map_index
	}, ; 160
	%struct.TypeMapModuleEntry {
		i32 u0x0200019f, ; uint32_t type_token_id
		i32 105; uint32_t java_map_index
	}, ; 161
	%struct.TypeMapModuleEntry {
		i32 u0x020001a0, ; uint32_t type_token_id
		i32 56; uint32_t java_map_index
	}, ; 162
	%struct.TypeMapModuleEntry {
		i32 u0x020001a2, ; uint32_t type_token_id
		i32 99; uint32_t java_map_index
	}, ; 163
	%struct.TypeMapModuleEntry {
		i32 u0x020001a3, ; uint32_t type_token_id
		i32 31; uint32_t java_map_index
	}, ; 164
	%struct.TypeMapModuleEntry {
		i32 u0x020001a4, ; uint32_t type_token_id
		i32 73; uint32_t java_map_index
	}, ; 165
	%struct.TypeMapModuleEntry {
		i32 u0x020001a5, ; uint32_t type_token_id
		i32 147; uint32_t java_map_index
	}, ; 166
	%struct.TypeMapModuleEntry {
		i32 u0x020001b4, ; uint32_t type_token_id
		i32 78; uint32_t java_map_index
	} ; 167
], align 16

@module0_managed_to_java_duplicates = internal dso_local constant [71 x %struct.TypeMapModuleEntry] [
	%struct.TypeMapModuleEntry {
		i32 u0x02000070, ; uint32_t type_token_id
		i32 121; uint32_t java_map_index
	}, ; 0
	%struct.TypeMapModuleEntry {
		i32 u0x02000074, ; uint32_t type_token_id
		i32 168; uint32_t java_map_index
	}, ; 1
	%struct.TypeMapModuleEntry {
		i32 u0x02000076, ; uint32_t type_token_id
		i32 29; uint32_t java_map_index
	}, ; 2
	%struct.TypeMapModuleEntry {
		i32 u0x02000079, ; uint32_t type_token_id
		i32 23; uint32_t java_map_index
	}, ; 3
	%struct.TypeMapModuleEntry {
		i32 u0x0200007b, ; uint32_t type_token_id
		i32 55; uint32_t java_map_index
	}, ; 4
	%struct.TypeMapModuleEntry {
		i32 u0x0200007d, ; uint32_t type_token_id
		i32 158; uint32_t java_map_index
	}, ; 5
	%struct.TypeMapModuleEntry {
		i32 u0x0200007f, ; uint32_t type_token_id
		i32 93; uint32_t java_map_index
	}, ; 6
	%struct.TypeMapModuleEntry {
		i32 u0x02000081, ; uint32_t type_token_id
		i32 108; uint32_t java_map_index
	}, ; 7
	%struct.TypeMapModuleEntry {
		i32 u0x02000083, ; uint32_t type_token_id
		i32 148; uint32_t java_map_index
	}, ; 8
	%struct.TypeMapModuleEntry {
		i32 u0x02000085, ; uint32_t type_token_id
		i32 126; uint32_t java_map_index
	}, ; 9
	%struct.TypeMapModuleEntry {
		i32 u0x02000089, ; uint32_t type_token_id
		i32 112; uint32_t java_map_index
	}, ; 10
	%struct.TypeMapModuleEntry {
		i32 u0x0200008c, ; uint32_t type_token_id
		i32 82; uint32_t java_map_index
	}, ; 11
	%struct.TypeMapModuleEntry {
		i32 u0x0200008e, ; uint32_t type_token_id
		i32 57; uint32_t java_map_index
	}, ; 12
	%struct.TypeMapModuleEntry {
		i32 u0x02000093, ; uint32_t type_token_id
		i32 51; uint32_t java_map_index
	}, ; 13
	%struct.TypeMapModuleEntry {
		i32 u0x02000095, ; uint32_t type_token_id
		i32 129; uint32_t java_map_index
	}, ; 14
	%struct.TypeMapModuleEntry {
		i32 u0x02000097, ; uint32_t type_token_id
		i32 142; uint32_t java_map_index
	}, ; 15
	%struct.TypeMapModuleEntry {
		i32 u0x020000a2, ; uint32_t type_token_id
		i32 19; uint32_t java_map_index
	}, ; 16
	%struct.TypeMapModuleEntry {
		i32 u0x020000ac, ; uint32_t type_token_id
		i32 107; uint32_t java_map_index
	}, ; 17
	%struct.TypeMapModuleEntry {
		i32 u0x020000b1, ; uint32_t type_token_id
		i32 63; uint32_t java_map_index
	}, ; 18
	%struct.TypeMapModuleEntry {
		i32 u0x020000b4, ; uint32_t type_token_id
		i32 32; uint32_t java_map_index
	}, ; 19
	%struct.TypeMapModuleEntry {
		i32 u0x020000b7, ; uint32_t type_token_id
		i32 35; uint32_t java_map_index
	}, ; 20
	%struct.TypeMapModuleEntry {
		i32 u0x020000b9, ; uint32_t type_token_id
		i32 42; uint32_t java_map_index
	}, ; 21
	%struct.TypeMapModuleEntry {
		i32 u0x020000bb, ; uint32_t type_token_id
		i32 71; uint32_t java_map_index
	}, ; 22
	%struct.TypeMapModuleEntry {
		i32 u0x020000bd, ; uint32_t type_token_id
		i32 140; uint32_t java_map_index
	}, ; 23
	%struct.TypeMapModuleEntry {
		i32 u0x020000bf, ; uint32_t type_token_id
		i32 25; uint32_t java_map_index
	}, ; 24
	%struct.TypeMapModuleEntry {
		i32 u0x020000c1, ; uint32_t type_token_id
		i32 133; uint32_t java_map_index
	}, ; 25
	%struct.TypeMapModuleEntry {
		i32 u0x020000c3, ; uint32_t type_token_id
		i32 135; uint32_t java_map_index
	}, ; 26
	%struct.TypeMapModuleEntry {
		i32 u0x020000c5, ; uint32_t type_token_id
		i32 18; uint32_t java_map_index
	}, ; 27
	%struct.TypeMapModuleEntry {
		i32 u0x020000c8, ; uint32_t type_token_id
		i32 17; uint32_t java_map_index
	}, ; 28
	%struct.TypeMapModuleEntry {
		i32 u0x020000c9, ; uint32_t type_token_id
		i32 14; uint32_t java_map_index
	}, ; 29
	%struct.TypeMapModuleEntry {
		i32 u0x020000d1, ; uint32_t type_token_id
		i32 41; uint32_t java_map_index
	}, ; 30
	%struct.TypeMapModuleEntry {
		i32 u0x020000d2, ; uint32_t type_token_id
		i32 124; uint32_t java_map_index
	}, ; 31
	%struct.TypeMapModuleEntry {
		i32 u0x020000d6, ; uint32_t type_token_id
		i32 119; uint32_t java_map_index
	}, ; 32
	%struct.TypeMapModuleEntry {
		i32 u0x020000f1, ; uint32_t type_token_id
		i32 138; uint32_t java_map_index
	}, ; 33
	%struct.TypeMapModuleEntry {
		i32 u0x020000f7, ; uint32_t type_token_id
		i32 10; uint32_t java_map_index
	}, ; 34
	%struct.TypeMapModuleEntry {
		i32 u0x020000fc, ; uint32_t type_token_id
		i32 85; uint32_t java_map_index
	}, ; 35
	%struct.TypeMapModuleEntry {
		i32 u0x02000100, ; uint32_t type_token_id
		i32 169; uint32_t java_map_index
	}, ; 36
	%struct.TypeMapModuleEntry {
		i32 u0x02000116, ; uint32_t type_token_id
		i32 52; uint32_t java_map_index
	}, ; 37
	%struct.TypeMapModuleEntry {
		i32 u0x0200011f, ; uint32_t type_token_id
		i32 79; uint32_t java_map_index
	}, ; 38
	%struct.TypeMapModuleEntry {
		i32 u0x02000125, ; uint32_t type_token_id
		i32 146; uint32_t java_map_index
	}, ; 39
	%struct.TypeMapModuleEntry {
		i32 u0x02000126, ; uint32_t type_token_id
		i32 80; uint32_t java_map_index
	}, ; 40
	%struct.TypeMapModuleEntry {
		i32 u0x0200012a, ; uint32_t type_token_id
		i32 37; uint32_t java_map_index
	}, ; 41
	%struct.TypeMapModuleEntry {
		i32 u0x0200012e, ; uint32_t type_token_id
		i32 49; uint32_t java_map_index
	}, ; 42
	%struct.TypeMapModuleEntry {
		i32 u0x02000130, ; uint32_t type_token_id
		i32 39; uint32_t java_map_index
	}, ; 43
	%struct.TypeMapModuleEntry {
		i32 u0x02000132, ; uint32_t type_token_id
		i32 156; uint32_t java_map_index
	}, ; 44
	%struct.TypeMapModuleEntry {
		i32 u0x02000134, ; uint32_t type_token_id
		i32 110; uint32_t java_map_index
	}, ; 45
	%struct.TypeMapModuleEntry {
		i32 u0x02000137, ; uint32_t type_token_id
		i32 47; uint32_t java_map_index
	}, ; 46
	%struct.TypeMapModuleEntry {
		i32 u0x02000143, ; uint32_t type_token_id
		i32 7; uint32_t java_map_index
	}, ; 47
	%struct.TypeMapModuleEntry {
		i32 u0x02000148, ; uint32_t type_token_id
		i32 116; uint32_t java_map_index
	}, ; 48
	%struct.TypeMapModuleEntry {
		i32 u0x0200014e, ; uint32_t type_token_id
		i32 111; uint32_t java_map_index
	}, ; 49
	%struct.TypeMapModuleEntry {
		i32 u0x02000154, ; uint32_t type_token_id
		i32 43; uint32_t java_map_index
	}, ; 50
	%struct.TypeMapModuleEntry {
		i32 u0x02000156, ; uint32_t type_token_id
		i32 87; uint32_t java_map_index
	}, ; 51
	%struct.TypeMapModuleEntry {
		i32 u0x02000158, ; uint32_t type_token_id
		i32 36; uint32_t java_map_index
	}, ; 52
	%struct.TypeMapModuleEntry {
		i32 u0x0200015a, ; uint32_t type_token_id
		i32 171; uint32_t java_map_index
	}, ; 53
	%struct.TypeMapModuleEntry {
		i32 u0x0200015f, ; uint32_t type_token_id
		i32 166; uint32_t java_map_index
	}, ; 54
	%struct.TypeMapModuleEntry {
		i32 u0x02000161, ; uint32_t type_token_id
		i32 15; uint32_t java_map_index
	}, ; 55
	%struct.TypeMapModuleEntry {
		i32 u0x02000164, ; uint32_t type_token_id
		i32 13; uint32_t java_map_index
	}, ; 56
	%struct.TypeMapModuleEntry {
		i32 u0x02000166, ; uint32_t type_token_id
		i32 151; uint32_t java_map_index
	}, ; 57
	%struct.TypeMapModuleEntry {
		i32 u0x02000168, ; uint32_t type_token_id
		i32 157; uint32_t java_map_index
	}, ; 58
	%struct.TypeMapModuleEntry {
		i32 u0x0200016b, ; uint32_t type_token_id
		i32 92; uint32_t java_map_index
	}, ; 59
	%struct.TypeMapModuleEntry {
		i32 u0x0200016f, ; uint32_t type_token_id
		i32 67; uint32_t java_map_index
	}, ; 60
	%struct.TypeMapModuleEntry {
		i32 u0x02000171, ; uint32_t type_token_id
		i32 109; uint32_t java_map_index
	}, ; 61
	%struct.TypeMapModuleEntry {
		i32 u0x02000174, ; uint32_t type_token_id
		i32 145; uint32_t java_map_index
	}, ; 62
	%struct.TypeMapModuleEntry {
		i32 u0x02000177, ; uint32_t type_token_id
		i32 46; uint32_t java_map_index
	}, ; 63
	%struct.TypeMapModuleEntry {
		i32 u0x02000179, ; uint32_t type_token_id
		i32 159; uint32_t java_map_index
	}, ; 64
	%struct.TypeMapModuleEntry {
		i32 u0x0200017b, ; uint32_t type_token_id
		i32 77; uint32_t java_map_index
	}, ; 65
	%struct.TypeMapModuleEntry {
		i32 u0x0200017e, ; uint32_t type_token_id
		i32 149; uint32_t java_map_index
	}, ; 66
	%struct.TypeMapModuleEntry {
		i32 u0x02000194, ; uint32_t type_token_id
		i32 136; uint32_t java_map_index
	}, ; 67
	%struct.TypeMapModuleEntry {
		i32 u0x02000196, ; uint32_t type_token_id
		i32 90; uint32_t java_map_index
	}, ; 68
	%struct.TypeMapModuleEntry {
		i32 u0x0200019c, ; uint32_t type_token_id
		i32 170; uint32_t java_map_index
	}, ; 69
	%struct.TypeMapModuleEntry {
		i32 u0x020001a1, ; uint32_t type_token_id
		i32 56; uint32_t java_map_index
	} ; 70
], align 16

@module1_managed_to_java = internal dso_local constant [4 x %struct.TypeMapModuleEntry] [
	%struct.TypeMapModuleEntry {
		i32 u0x02000002, ; uint32_t type_token_id
		i32 26; uint32_t java_map_index
	}, ; 0
	%struct.TypeMapModuleEntry {
		i32 u0x02000003, ; uint32_t type_token_id
		i32 153; uint32_t java_map_index
	}, ; 1
	%struct.TypeMapModuleEntry {
		i32 u0x02000004, ; uint32_t type_token_id
		i32 2; uint32_t java_map_index
	}, ; 2
	%struct.TypeMapModuleEntry {
		i32 u0x02000005, ; uint32_t type_token_id
		i32 167; uint32_t java_map_index
	} ; 3
], align 16

; Java to managed map
@map_java = dso_local local_unnamed_addr constant [172 x %struct.TypeMapJava] [
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000086, ; uint32_t type_token_id
		i32 12; uint32_t java_name_index
	}, ; 0
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000180, ; uint32_t type_token_id
		i32 135; uint32_t java_name_index
	}, ; 1
	%struct.TypeMapJava {
		i32 1, ; uint32_t module_index
		i32 u0x02000004, ; uint32_t type_token_id
		i32 170; uint32_t java_name_index
	}, ; 2
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000087, ; uint32_t type_token_id
		i32 13; uint32_t java_name_index
	}, ; 3
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000149, ; uint32_t type_token_id
		i32 98; uint32_t java_name_index
	}, ; 4
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x0200017c, ; uint32_t type_token_id
		i32 132; uint32_t java_name_index
	}, ; 5
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x020000a9, ; uint32_t type_token_id
		i32 35; uint32_t java_name_index
	}, ; 6
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x0200013a, ; uint32_t type_token_id
		i32 90; uint32_t java_name_index
	}, ; 7
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x020000a4, ; uint32_t type_token_id
		i32 31; uint32_t java_name_index
	}, ; 8
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x020000fd, ; uint32_t type_token_id
		i32 63; uint32_t java_name_index
	}, ; 9
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x020000f2, ; uint32_t type_token_id
		i32 61; uint32_t java_name_index
	}, ; 10
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x0200014c, ; uint32_t type_token_id
		i32 101; uint32_t java_name_index
	}, ; 11
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000123, ; uint32_t type_token_id
		i32 79; uint32_t java_name_index
	}, ; 12
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000163, ; uint32_t type_token_id
		i32 117; uint32_t java_name_index
	}, ; 13
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x00000000, ; uint32_t type_token_id
		i32 52; uint32_t java_name_index
	}, ; 14
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x00000000, ; uint32_t type_token_id
		i32 115; uint32_t java_name_index
	}, ; 15
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x0200008a, ; uint32_t type_token_id
		i32 15; uint32_t java_name_index
	}, ; 16
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x00000000, ; uint32_t type_token_id
		i32 53; uint32_t java_name_index
	}, ; 17
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x00000000, ; uint32_t type_token_id
		i32 51; uint32_t java_name_index
	}, ; 18
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x00000000, ; uint32_t type_token_id
		i32 29; uint32_t java_name_index
	}, ; 19
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x0200016c, ; uint32_t type_token_id
		i32 122; uint32_t java_name_index
	}, ; 20
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x020000a3, ; uint32_t type_token_id
		i32 30; uint32_t java_name_index
	}, ; 21
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000136, ; uint32_t type_token_id
		i32 89; uint32_t java_name_index
	}, ; 22
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000078, ; uint32_t type_token_id
		i32 5; uint32_t java_name_index
	}, ; 23
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000195, ; uint32_t type_token_id
		i32 154; uint32_t java_name_index
	}, ; 24
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x020000be, ; uint32_t type_token_id
		i32 48; uint32_t java_name_index
	}, ; 25
	%struct.TypeMapJava {
		i32 1, ; uint32_t module_index
		i32 u0x02000002, ; uint32_t type_token_id
		i32 168; uint32_t java_name_index
	}, ; 26
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000091, ; uint32_t type_token_id
		i32 18; uint32_t java_name_index
	}, ; 27
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x0200009c, ; uint32_t type_token_id
		i32 26; uint32_t java_name_index
	}, ; 28
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000075, ; uint32_t type_token_id
		i32 3; uint32_t java_name_index
	}, ; 29
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000119, ; uint32_t type_token_id
		i32 70; uint32_t java_name_index
	}, ; 30
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x020001a3, ; uint32_t type_token_id
		i32 164; uint32_t java_name_index
	}, ; 31
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x00000000, ; uint32_t type_token_id
		i32 43; uint32_t java_name_index
	}, ; 32
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000121, ; uint32_t type_token_id
		i32 77; uint32_t java_name_index
	}, ; 33
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x0200017f, ; uint32_t type_token_id
		i32 134; uint32_t java_name_index
	}, ; 34
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x00000000, ; uint32_t type_token_id
		i32 44; uint32_t java_name_index
	}, ; 35
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x00000000, ; uint32_t type_token_id
		i32 109; uint32_t java_name_index
	}, ; 36
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x00000000, ; uint32_t type_token_id
		i32 82; uint32_t java_name_index
	}, ; 37
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000199, ; uint32_t type_token_id
		i32 156; uint32_t java_name_index
	}, ; 38
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x00000000, ; uint32_t type_token_id
		i32 85; uint32_t java_name_index
	}, ; 39
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x020000fe, ; uint32_t type_token_id
		i32 64; uint32_t java_name_index
	}, ; 40
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x020000d0, ; uint32_t type_token_id
		i32 54; uint32_t java_name_index
	}, ; 41
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x00000000, ; uint32_t type_token_id
		i32 45; uint32_t java_name_index
	}, ; 42
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000153, ; uint32_t type_token_id
		i32 107; uint32_t java_name_index
	}, ; 43
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x0200014a, ; uint32_t type_token_id
		i32 99; uint32_t java_name_index
	}, ; 44
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x020000d4, ; uint32_t type_token_id
		i32 56; uint32_t java_name_index
	}, ; 45
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000176, ; uint32_t type_token_id
		i32 129; uint32_t java_name_index
	}, ; 46
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x00000000, ; uint32_t type_token_id
		i32 88; uint32_t java_name_index
	}, ; 47
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000145, ; uint32_t type_token_id
		i32 96; uint32_t java_name_index
	}, ; 48
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x00000000, ; uint32_t type_token_id
		i32 84; uint32_t java_name_index
	}, ; 49
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x0200012c, ; uint32_t type_token_id
		i32 83; uint32_t java_name_index
	}, ; 50
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000092, ; uint32_t type_token_id
		i32 19; uint32_t java_name_index
	}, ; 51
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000115, ; uint32_t type_token_id
		i32 69; uint32_t java_name_index
	}, ; 52
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000182, ; uint32_t type_token_id
		i32 137; uint32_t java_name_index
	}, ; 53
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000192, ; uint32_t type_token_id
		i32 152; uint32_t java_name_index
	}, ; 54
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x0200007a, ; uint32_t type_token_id
		i32 6; uint32_t java_name_index
	}, ; 55
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x020001a0, ; uint32_t type_token_id
		i32 162; uint32_t java_name_index
	}, ; 56
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x00000000, ; uint32_t type_token_id
		i32 17; uint32_t java_name_index
	}, ; 57
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x0200019d, ; uint32_t type_token_id
		i32 159; uint32_t java_name_index
	}, ; 58
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x020000a6, ; uint32_t type_token_id
		i32 33; uint32_t java_name_index
	}, ; 59
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x020000a8, ; uint32_t type_token_id
		i32 34; uint32_t java_name_index
	}, ; 60
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x0200009a, ; uint32_t type_token_id
		i32 24; uint32_t java_name_index
	}, ; 61
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x0200013b, ; uint32_t type_token_id
		i32 91; uint32_t java_name_index
	}, ; 62
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x020000b0, ; uint32_t type_token_id
		i32 41; uint32_t java_name_index
	}, ; 63
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x020000ae, ; uint32_t type_token_id
		i32 39; uint32_t java_name_index
	}, ; 64
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000127, ; uint32_t type_token_id
		i32 81; uint32_t java_name_index
	}, ; 65
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x0200018c, ; uint32_t type_token_id
		i32 147; uint32_t java_name_index
	}, ; 66
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x00000000, ; uint32_t type_token_id
		i32 124; uint32_t java_name_index
	}, ; 67
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x0200013d, ; uint32_t type_token_id
		i32 93; uint32_t java_name_index
	}, ; 68
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000071, ; uint32_t type_token_id
		i32 1; uint32_t java_name_index
	}, ; 69
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x0200016d, ; uint32_t type_token_id
		i32 123; uint32_t java_name_index
	}, ; 70
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x00000000, ; uint32_t type_token_id
		i32 46; uint32_t java_name_index
	}, ; 71
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000150, ; uint32_t type_token_id
		i32 104; uint32_t java_name_index
	}, ; 72
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x020001a4, ; uint32_t type_token_id
		i32 165; uint32_t java_name_index
	}, ; 73
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000113, ; uint32_t type_token_id
		i32 67; uint32_t java_name_index
	}, ; 74
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x0200015b, ; uint32_t type_token_id
		i32 111; uint32_t java_name_index
	}, ; 75
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x0200011d, ; uint32_t type_token_id
		i32 74; uint32_t java_name_index
	}, ; 76
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x00000000, ; uint32_t type_token_id
		i32 131; uint32_t java_name_index
	}, ; 77
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x020001b4, ; uint32_t type_token_id
		i32 167; uint32_t java_name_index
	}, ; 78
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x0200011e, ; uint32_t type_token_id
		i32 75; uint32_t java_name_index
	}, ; 79
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000120, ; uint32_t type_token_id
		i32 76; uint32_t java_name_index
	}, ; 80
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x0200009b, ; uint32_t type_token_id
		i32 25; uint32_t java_name_index
	}, ; 81
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x00000000, ; uint32_t type_token_id
		i32 16; uint32_t java_name_index
	}, ; 82
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000098, ; uint32_t type_token_id
		i32 22; uint32_t java_name_index
	}, ; 83
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000162, ; uint32_t type_token_id
		i32 116; uint32_t java_name_index
	}, ; 84
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x020000fb, ; uint32_t type_token_id
		i32 62; uint32_t java_name_index
	}, ; 85
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000077, ; uint32_t type_token_id
		i32 4; uint32_t java_name_index
	}, ; 86
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x00000000, ; uint32_t type_token_id
		i32 108; uint32_t java_name_index
	}, ; 87
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000152, ; uint32_t type_token_id
		i32 106; uint32_t java_name_index
	}, ; 88
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x0200009f, ; uint32_t type_token_id
		i32 28; uint32_t java_name_index
	}, ; 89
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x00000000, ; uint32_t type_token_id
		i32 142; uint32_t java_name_index
	}, ; 90
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x0200018b, ; uint32_t type_token_id
		i32 146; uint32_t java_name_index
	}, ; 91
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x0200016a, ; uint32_t type_token_id
		i32 121; uint32_t java_name_index
	}, ; 92
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x00000000, ; uint32_t type_token_id
		i32 8; uint32_t java_name_index
	}, ; 93
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000181, ; uint32_t type_token_id
		i32 136; uint32_t java_name_index
	}, ; 94
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x0200010b, ; uint32_t type_token_id
		i32 66; uint32_t java_name_index
	}, ; 95
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000191, ; uint32_t type_token_id
		i32 151; uint32_t java_name_index
	}, ; 96
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x0200018f, ; uint32_t type_token_id
		i32 149; uint32_t java_name_index
	}, ; 97
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x0200013f, ; uint32_t type_token_id
		i32 95; uint32_t java_name_index
	}, ; 98
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x020001a2, ; uint32_t type_token_id
		i32 163; uint32_t java_name_index
	}, ; 99
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000186, ; uint32_t type_token_id
		i32 141; uint32_t java_name_index
	}, ; 100
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x020000eb, ; uint32_t type_token_id
		i32 58; uint32_t java_name_index
	}, ; 101
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x020000b2, ; uint32_t type_token_id
		i32 42; uint32_t java_name_index
	}, ; 102
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x0200014f, ; uint32_t type_token_id
		i32 103; uint32_t java_name_index
	}, ; 103
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x0200011c, ; uint32_t type_token_id
		i32 73; uint32_t java_name_index
	}, ; 104
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x0200019f, ; uint32_t type_token_id
		i32 161; uint32_t java_name_index
	}, ; 105
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x0200014b, ; uint32_t type_token_id
		i32 100; uint32_t java_name_index
	}, ; 106
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x00000000, ; uint32_t type_token_id
		i32 37; uint32_t java_name_index
	}, ; 107
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x00000000, ; uint32_t type_token_id
		i32 9; uint32_t java_name_index
	}, ; 108
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000170, ; uint32_t type_token_id
		i32 125; uint32_t java_name_index
	}, ; 109
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x00000000, ; uint32_t type_token_id
		i32 87; uint32_t java_name_index
	}, ; 110
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x0200014d, ; uint32_t type_token_id
		i32 102; uint32_t java_name_index
	}, ; 111
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000088, ; uint32_t type_token_id
		i32 14; uint32_t java_name_index
	}, ; 112
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x0200018d, ; uint32_t type_token_id
		i32 148; uint32_t java_name_index
	}, ; 113
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000114, ; uint32_t type_token_id
		i32 68; uint32_t java_name_index
	}, ; 114
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000198, ; uint32_t type_token_id
		i32 155; uint32_t java_name_index
	}, ; 115
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000147, ; uint32_t type_token_id
		i32 97; uint32_t java_name_index
	}, ; 116
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000188, ; uint32_t type_token_id
		i32 143; uint32_t java_name_index
	}, ; 117
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000185, ; uint32_t type_token_id
		i32 140; uint32_t java_name_index
	}, ; 118
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x00000000, ; uint32_t type_token_id
		i32 57; uint32_t java_name_index
	}, ; 119
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000099, ; uint32_t type_token_id
		i32 23; uint32_t java_name_index
	}, ; 120
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x00000000, ; uint32_t type_token_id
		i32 0; uint32_t java_name_index
	}, ; 121
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x0200011b, ; uint32_t type_token_id
		i32 72; uint32_t java_name_index
	}, ; 122
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x020000d3, ; uint32_t type_token_id
		i32 55; uint32_t java_name_index
	}, ; 123
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x020000af, ; uint32_t type_token_id
		i32 40; uint32_t java_name_index
	}, ; 124
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x020000ad, ; uint32_t type_token_id
		i32 38; uint32_t java_name_index
	}, ; 125
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x00000000, ; uint32_t type_token_id
		i32 11; uint32_t java_name_index
	}, ; 126
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000122, ; uint32_t type_token_id
		i32 78; uint32_t java_name_index
	}, ; 127
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x020000aa, ; uint32_t type_token_id
		i32 36; uint32_t java_name_index
	}, ; 128
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000094, ; uint32_t type_token_id
		i32 20; uint32_t java_name_index
	}, ; 129
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x0200018a, ; uint32_t type_token_id
		i32 145; uint32_t java_name_index
	}, ; 130
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x0200011a, ; uint32_t type_token_id
		i32 71; uint32_t java_name_index
	}, ; 131
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000183, ; uint32_t type_token_id
		i32 138; uint32_t java_name_index
	}, ; 132
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x00000000, ; uint32_t type_token_id
		i32 49; uint32_t java_name_index
	}, ; 133
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000190, ; uint32_t type_token_id
		i32 150; uint32_t java_name_index
	}, ; 134
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x00000000, ; uint32_t type_token_id
		i32 50; uint32_t java_name_index
	}, ; 135
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000193, ; uint32_t type_token_id
		i32 153; uint32_t java_name_index
	}, ; 136
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000175, ; uint32_t type_token_id
		i32 128; uint32_t java_name_index
	}, ; 137
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x020000f0, ; uint32_t type_token_id
		i32 60; uint32_t java_name_index
	}, ; 138
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x0200013e, ; uint32_t type_token_id
		i32 94; uint32_t java_name_index
	}, ; 139
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x00000000, ; uint32_t type_token_id
		i32 47; uint32_t java_name_index
	}, ; 140
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000184, ; uint32_t type_token_id
		i32 139; uint32_t java_name_index
	}, ; 141
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000096, ; uint32_t type_token_id
		i32 21; uint32_t java_name_index
	}, ; 142
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x0200013c, ; uint32_t type_token_id
		i32 92; uint32_t java_name_index
	}, ; 143
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x020000a5, ; uint32_t type_token_id
		i32 32; uint32_t java_name_index
	}, ; 144
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000173, ; uint32_t type_token_id
		i32 127; uint32_t java_name_index
	}, ; 145
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000124, ; uint32_t type_token_id
		i32 80; uint32_t java_name_index
	}, ; 146
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x020001a5, ; uint32_t type_token_id
		i32 166; uint32_t java_name_index
	}, ; 147
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x00000000, ; uint32_t type_token_id
		i32 10; uint32_t java_name_index
	}, ; 148
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x00000000, ; uint32_t type_token_id
		i32 133; uint32_t java_name_index
	}, ; 149
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x0200019e, ; uint32_t type_token_id
		i32 160; uint32_t java_name_index
	}, ; 150
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000165, ; uint32_t type_token_id
		i32 118; uint32_t java_name_index
	}, ; 151
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x0200015c, ; uint32_t type_token_id
		i32 112; uint32_t java_name_index
	}, ; 152
	%struct.TypeMapJava {
		i32 1, ; uint32_t module_index
		i32 u0x02000003, ; uint32_t type_token_id
		i32 169; uint32_t java_name_index
	}, ; 153
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x0200015d, ; uint32_t type_token_id
		i32 113; uint32_t java_name_index
	}, ; 154
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000189, ; uint32_t type_token_id
		i32 144; uint32_t java_name_index
	}, ; 155
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x00000000, ; uint32_t type_token_id
		i32 86; uint32_t java_name_index
	}, ; 156
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000167, ; uint32_t type_token_id
		i32 119; uint32_t java_name_index
	}, ; 157
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x00000000, ; uint32_t type_token_id
		i32 7; uint32_t java_name_index
	}, ; 158
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x00000000, ; uint32_t type_token_id
		i32 130; uint32_t java_name_index
	}, ; 159
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000169, ; uint32_t type_token_id
		i32 120; uint32_t java_name_index
	}, ; 160
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000172, ; uint32_t type_token_id
		i32 126; uint32_t java_name_index
	}, ; 161
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x0200009d, ; uint32_t type_token_id
		i32 27; uint32_t java_name_index
	}, ; 162
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x0200019a, ; uint32_t type_token_id
		i32 157; uint32_t java_name_index
	}, ; 163
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x00000000, ; uint32_t type_token_id
		i32 59; uint32_t java_name_index
	}, ; 164
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000151, ; uint32_t type_token_id
		i32 105; uint32_t java_name_index
	}, ; 165
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x0200015e, ; uint32_t type_token_id
		i32 114; uint32_t java_name_index
	}, ; 166
	%struct.TypeMapJava {
		i32 1, ; uint32_t module_index
		i32 u0x02000005, ; uint32_t type_token_id
		i32 171; uint32_t java_name_index
	}, ; 167
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x02000073, ; uint32_t type_token_id
		i32 2; uint32_t java_name_index
	}, ; 168
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x020000ff, ; uint32_t type_token_id
		i32 65; uint32_t java_name_index
	}, ; 169
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x00000000, ; uint32_t type_token_id
		i32 158; uint32_t java_name_index
	}, ; 170
	%struct.TypeMapJava {
		i32 0, ; uint32_t module_index
		i32 u0x00000000, ; uint32_t type_token_id
		i32 110; uint32_t java_name_index
	} ; 171
], align 16

; Java type names
@java_type_names = dso_local local_unnamed_addr constant [172 x ptr] [
	ptr @.str.0, ; 0
	ptr @.str.1, ; 1
	ptr @.str.2, ; 2
	ptr @.str.3, ; 3
	ptr @.str.4, ; 4
	ptr @.str.5, ; 5
	ptr @.str.6, ; 6
	ptr @.str.7, ; 7
	ptr @.str.8, ; 8
	ptr @.str.9, ; 9
	ptr @.str.10, ; 10
	ptr @.str.11, ; 11
	ptr @.str.12, ; 12
	ptr @.str.13, ; 13
	ptr @.str.14, ; 14
	ptr @.str.15, ; 15
	ptr @.str.16, ; 16
	ptr @.str.17, ; 17
	ptr @.str.18, ; 18
	ptr @.str.19, ; 19
	ptr @.str.20, ; 20
	ptr @.str.21, ; 21
	ptr @.str.22, ; 22
	ptr @.str.23, ; 23
	ptr @.str.24, ; 24
	ptr @.str.25, ; 25
	ptr @.str.26, ; 26
	ptr @.str.27, ; 27
	ptr @.str.28, ; 28
	ptr @.str.29, ; 29
	ptr @.str.30, ; 30
	ptr @.str.31, ; 31
	ptr @.str.32, ; 32
	ptr @.str.33, ; 33
	ptr @.str.34, ; 34
	ptr @.str.35, ; 35
	ptr @.str.36, ; 36
	ptr @.str.37, ; 37
	ptr @.str.38, ; 38
	ptr @.str.39, ; 39
	ptr @.str.40, ; 40
	ptr @.str.41, ; 41
	ptr @.str.42, ; 42
	ptr @.str.43, ; 43
	ptr @.str.44, ; 44
	ptr @.str.45, ; 45
	ptr @.str.46, ; 46
	ptr @.str.47, ; 47
	ptr @.str.48, ; 48
	ptr @.str.49, ; 49
	ptr @.str.50, ; 50
	ptr @.str.51, ; 51
	ptr @.str.52, ; 52
	ptr @.str.53, ; 53
	ptr @.str.54, ; 54
	ptr @.str.55, ; 55
	ptr @.str.56, ; 56
	ptr @.str.57, ; 57
	ptr @.str.58, ; 58
	ptr @.str.59, ; 59
	ptr @.str.60, ; 60
	ptr @.str.61, ; 61
	ptr @.str.62, ; 62
	ptr @.str.63, ; 63
	ptr @.str.64, ; 64
	ptr @.str.65, ; 65
	ptr @.str.66, ; 66
	ptr @.str.67, ; 67
	ptr @.str.68, ; 68
	ptr @.str.69, ; 69
	ptr @.str.70, ; 70
	ptr @.str.71, ; 71
	ptr @.str.72, ; 72
	ptr @.str.73, ; 73
	ptr @.str.74, ; 74
	ptr @.str.75, ; 75
	ptr @.str.76, ; 76
	ptr @.str.77, ; 77
	ptr @.str.78, ; 78
	ptr @.str.79, ; 79
	ptr @.str.80, ; 80
	ptr @.str.81, ; 81
	ptr @.str.82, ; 82
	ptr @.str.83, ; 83
	ptr @.str.84, ; 84
	ptr @.str.85, ; 85
	ptr @.str.86, ; 86
	ptr @.str.87, ; 87
	ptr @.str.88, ; 88
	ptr @.str.89, ; 89
	ptr @.str.90, ; 90
	ptr @.str.91, ; 91
	ptr @.str.92, ; 92
	ptr @.str.93, ; 93
	ptr @.str.94, ; 94
	ptr @.str.95, ; 95
	ptr @.str.96, ; 96
	ptr @.str.97, ; 97
	ptr @.str.98, ; 98
	ptr @.str.99, ; 99
	ptr @.str.100, ; 100
	ptr @.str.101, ; 101
	ptr @.str.102, ; 102
	ptr @.str.103, ; 103
	ptr @.str.104, ; 104
	ptr @.str.105, ; 105
	ptr @.str.106, ; 106
	ptr @.str.107, ; 107
	ptr @.str.108, ; 108
	ptr @.str.109, ; 109
	ptr @.str.110, ; 110
	ptr @.str.111, ; 111
	ptr @.str.112, ; 112
	ptr @.str.113, ; 113
	ptr @.str.114, ; 114
	ptr @.str.115, ; 115
	ptr @.str.116, ; 116
	ptr @.str.117, ; 117
	ptr @.str.118, ; 118
	ptr @.str.119, ; 119
	ptr @.str.120, ; 120
	ptr @.str.121, ; 121
	ptr @.str.122, ; 122
	ptr @.str.123, ; 123
	ptr @.str.124, ; 124
	ptr @.str.125, ; 125
	ptr @.str.126, ; 126
	ptr @.str.127, ; 127
	ptr @.str.128, ; 128
	ptr @.str.129, ; 129
	ptr @.str.130, ; 130
	ptr @.str.131, ; 131
	ptr @.str.132, ; 132
	ptr @.str.133, ; 133
	ptr @.str.134, ; 134
	ptr @.str.135, ; 135
	ptr @.str.136, ; 136
	ptr @.str.137, ; 137
	ptr @.str.138, ; 138
	ptr @.str.139, ; 139
	ptr @.str.140, ; 140
	ptr @.str.141, ; 141
	ptr @.str.142, ; 142
	ptr @.str.143, ; 143
	ptr @.str.144, ; 144
	ptr @.str.145, ; 145
	ptr @.str.146, ; 146
	ptr @.str.147, ; 147
	ptr @.str.148, ; 148
	ptr @.str.149, ; 149
	ptr @.str.150, ; 150
	ptr @.str.151, ; 151
	ptr @.str.152, ; 152
	ptr @.str.153, ; 153
	ptr @.str.154, ; 154
	ptr @.str.155, ; 155
	ptr @.str.156, ; 156
	ptr @.str.157, ; 157
	ptr @.str.158, ; 158
	ptr @.str.159, ; 159
	ptr @.str.160, ; 160
	ptr @.str.161, ; 161
	ptr @.str.162, ; 162
	ptr @.str.163, ; 163
	ptr @.str.164, ; 164
	ptr @.str.165, ; 165
	ptr @.str.166, ; 166
	ptr @.str.167, ; 167
	ptr @.str.168, ; 168
	ptr @.str.169, ; 169
	ptr @.str.170, ; 170
	ptr @.str.171 ; 171
], align 16

; Strings
@.str.0 = private unnamed_addr constant [29 x i8] c"org/xmlpull/v1/XmlPullParser\00", align 16
@.str.1 = private unnamed_addr constant [38 x i8] c"org/xmlpull/v1/XmlPullParserException\00", align 16
@.str.2 = private unnamed_addr constant [32 x i8] c"javax/security/cert/Certificate\00", align 16
@.str.3 = private unnamed_addr constant [36 x i8] c"javax/security/cert/X509Certificate\00", align 16
@.str.4 = private unnamed_addr constant [28 x i8] c"javax/security/auth/Subject\00", align 16
@.str.5 = private unnamed_addr constant [24 x i8] c"javax/net/SocketFactory\00", align 16
@.str.6 = private unnamed_addr constant [33 x i8] c"javax/net/ssl/HttpsURLConnection\00", align 16
@.str.7 = private unnamed_addr constant [31 x i8] c"javax/net/ssl/HostnameVerifier\00", align 16
@.str.8 = private unnamed_addr constant [25 x i8] c"javax/net/ssl/KeyManager\00", align 16
@.str.9 = private unnamed_addr constant [25 x i8] c"javax/net/ssl/SSLSession\00", align 16
@.str.10 = private unnamed_addr constant [32 x i8] c"javax/net/ssl/SSLSessionContext\00", align 16
@.str.11 = private unnamed_addr constant [27 x i8] c"javax/net/ssl/TrustManager\00", align 16
@.str.12 = private unnamed_addr constant [32 x i8] c"javax/net/ssl/KeyManagerFactory\00", align 16
@.str.13 = private unnamed_addr constant [25 x i8] c"javax/net/ssl/SSLContext\00", align 16
@.str.14 = private unnamed_addr constant [31 x i8] c"javax/net/ssl/SSLSocketFactory\00", align 16
@.str.15 = private unnamed_addr constant [34 x i8] c"javax/net/ssl/TrustManagerFactory\00", align 16
@.str.16 = private unnamed_addr constant [29 x i8] c"android/webkit/ValueCallback\00", align 16
@.str.17 = private unnamed_addr constant [34 x i8] c"android/webkit/WebResourceRequest\00", align 16
@.str.18 = private unnamed_addr constant [31 x i8] c"android/webkit/WebChromeClient\00", align 16
@.str.19 = private unnamed_addr constant [49 x i8] c"android/webkit/WebChromeClient$FileChooserParams\00", align 16
@.str.20 = private unnamed_addr constant [32 x i8] c"android/webkit/WebResourceError\00", align 16
@.str.21 = private unnamed_addr constant [27 x i8] c"android/webkit/WebSettings\00", align 16
@.str.22 = private unnamed_addr constant [23 x i8] c"android/webkit/WebView\00", align 16
@.str.23 = private unnamed_addr constant [29 x i8] c"android/webkit/WebViewClient\00", align 16
@.str.24 = private unnamed_addr constant [24 x i8] c"android/widget/TextView\00", align 16
@.str.25 = private unnamed_addr constant [30 x i8] c"android/widget/AbsoluteLayout\00", align 16
@.str.26 = private unnamed_addr constant [24 x i8] c"android/widget/EditText\00", align 16
@.str.27 = private unnamed_addr constant [28 x i8] c"android/widget/LinearLayout\00", align 16
@.str.28 = private unnamed_addr constant [21 x i8] c"android/widget/Toast\00", align 16
@.str.29 = private unnamed_addr constant [26 x i8] c"android/util/AttributeSet\00", align 16
@.str.30 = private unnamed_addr constant [19 x i8] c"android/os/Handler\00", align 16
@.str.31 = private unnamed_addr constant [22 x i8] c"android/os/BaseBundle\00", align 16
@.str.32 = private unnamed_addr constant [17 x i8] c"android/os/Build\00", align 16
@.str.33 = private unnamed_addr constant [25 x i8] c"android/os/Build$VERSION\00", align 16
@.str.34 = private unnamed_addr constant [18 x i8] c"android/os/Bundle\00", align 16
@.str.35 = private unnamed_addr constant [30 x i8] c"android/os/CancellationSignal\00", align 16
@.str.36 = private unnamed_addr constant [18 x i8] c"android/os/Looper\00", align 16
@.str.37 = private unnamed_addr constant [35 x i8] c"android/animation/TimeInterpolator\00", align 16
@.str.38 = private unnamed_addr constant [18 x i8] c"android/view/View\00", align 16
@.str.39 = private unnamed_addr constant [22 x i8] c"android/view/KeyEvent\00", align 16
@.str.40 = private unnamed_addr constant [20 x i8] c"android/view/Window\00", align 16
@.str.41 = private unnamed_addr constant [28 x i8] c"android/view/ActionProvider\00", align 16
@.str.42 = private unnamed_addr constant [33 x i8] c"android/view/ContextThemeWrapper\00", align 16
@.str.43 = private unnamed_addr constant [41 x i8] c"android/view/ContextMenu$ContextMenuInfo\00", align 16
@.str.44 = private unnamed_addr constant [18 x i8] c"android/view/Menu\00", align 16
@.str.45 = private unnamed_addr constant [45 x i8] c"android/view/MenuItem$OnActionExpandListener\00", align 16
@.str.46 = private unnamed_addr constant [46 x i8] c"android/view/MenuItem$OnMenuItemClickListener\00", align 16
@.str.47 = private unnamed_addr constant [22 x i8] c"android/view/MenuItem\00", align 16
@.str.48 = private unnamed_addr constant [24 x i8] c"android/view/InputEvent\00", align 16
@.str.49 = private unnamed_addr constant [21 x i8] c"android/view/SubMenu\00", align 16
@.str.50 = private unnamed_addr constant [45 x i8] c"android/view/WindowInsetsAnimationController\00", align 16
@.str.51 = private unnamed_addr constant [50 x i8] c"android/view/WindowInsetsAnimationControlListener\00", align 16
@.str.52 = private unnamed_addr constant [36 x i8] c"android/view/WindowInsetsController\00", align 16
@.str.53 = private unnamed_addr constant [72 x i8] c"android/view/WindowInsetsController$OnControllableInsetsChangedListener\00", align 16
@.str.54 = private unnamed_addr constant [23 x i8] c"android/view/ViewGroup\00", align 16
@.str.55 = private unnamed_addr constant [26 x i8] c"android/view/WindowInsets\00", align 16
@.str.56 = private unnamed_addr constant [31 x i8] c"android/view/WindowInsets$Type\00", align 16
@.str.57 = private unnamed_addr constant [36 x i8] c"android/view/animation/Interpolator\00", align 16
@.str.58 = private unnamed_addr constant [40 x i8] c"mono/android/runtime/InputStreamAdapter\00", align 16
@.str.59 = private unnamed_addr constant [31 x i8] c"mono/android/runtime/JavaArray\00", align 16
@.str.60 = private unnamed_addr constant [21 x i8] c"java/util/Collection\00", align 16
@.str.61 = private unnamed_addr constant [18 x i8] c"java/util/HashMap\00", align 16
@.str.62 = private unnamed_addr constant [20 x i8] c"java/util/ArrayList\00", align 16
@.str.63 = private unnamed_addr constant [32 x i8] c"mono/android/runtime/JavaObject\00", align 16
@.str.64 = private unnamed_addr constant [35 x i8] c"android/runtime/JavaProxyThrowable\00", align 16
@.str.65 = private unnamed_addr constant [18 x i8] c"java/util/HashSet\00", align 16
@.str.66 = private unnamed_addr constant [41 x i8] c"mono/android/runtime/OutputStreamAdapter\00", align 16
@.str.67 = private unnamed_addr constant [40 x i8] c"android/runtime/XmlReaderResourceParser\00", align 16
@.str.68 = private unnamed_addr constant [36 x i8] c"android/runtime/XmlReaderPullParser\00", align 16
@.str.69 = private unnamed_addr constant [16 x i8] c"android/net/Uri\00", align 16
@.str.70 = private unnamed_addr constant [27 x i8] c"android/graphics/BlendMode\00", align 16
@.str.71 = private unnamed_addr constant [24 x i8] c"android/graphics/Insets\00", align 16
@.str.72 = private unnamed_addr constant [23 x i8] c"android/graphics/Paint\00", align 16
@.str.73 = private unnamed_addr constant [28 x i8] c"android/graphics/PorterDuff\00", align 16
@.str.74 = private unnamed_addr constant [33 x i8] c"android/graphics/PorterDuff$Mode\00", align 16
@.str.75 = private unnamed_addr constant [35 x i8] c"android/graphics/drawable/Drawable\00", align 16
@.str.76 = private unnamed_addr constant [24 x i8] c"android/content/Context\00", align 16
@.str.77 = private unnamed_addr constant [23 x i8] c"android/content/Intent\00", align 16
@.str.78 = private unnamed_addr constant [42 x i8] c"android/content/ActivityNotFoundException\00", align 16
@.str.79 = private unnamed_addr constant [30 x i8] c"android/content/ComponentName\00", align 16
@.str.80 = private unnamed_addr constant [32 x i8] c"android/content/ContentResolver\00", align 16
@.str.81 = private unnamed_addr constant [31 x i8] c"android/content/ContextWrapper\00", align 16
@.str.82 = private unnamed_addr constant [48 x i8] c"android/content/DialogInterface$OnClickListener\00", align 16
@.str.83 = private unnamed_addr constant [64 x i8] c"mono/android/content/DialogInterface_OnClickListenerImplementor\00", align 16
@.str.84 = private unnamed_addr constant [32 x i8] c"android/content/DialogInterface\00", align 16
@.str.85 = private unnamed_addr constant [41 x i8] c"android/content/SharedPreferences$Editor\00", align 16
@.str.86 = private unnamed_addr constant [67 x i8] c"android/content/SharedPreferences$OnSharedPreferenceChangeListener\00", align 16
@.str.87 = private unnamed_addr constant [34 x i8] c"android/content/SharedPreferences\00", align 16
@.str.88 = private unnamed_addr constant [38 x i8] c"android/content/res/XmlResourceParser\00", align 16
@.str.89 = private unnamed_addr constant [35 x i8] c"android/content/res/ColorStateList\00", align 16
@.str.90 = private unnamed_addr constant [22 x i8] c"android/app/ActionBar\00", align 16
@.str.91 = private unnamed_addr constant [21 x i8] c"android/app/Activity\00", align 16
@.str.92 = private unnamed_addr constant [24 x i8] c"android/app/AlertDialog\00", align 16
@.str.93 = private unnamed_addr constant [32 x i8] c"android/app/AlertDialog$Builder\00", align 16
@.str.94 = private unnamed_addr constant [24 x i8] c"android/app/Application\00", align 16
@.str.95 = private unnamed_addr constant [19 x i8] c"android/app/Dialog\00", align 16
@.str.96 = private unnamed_addr constant [26 x i8] c"java/net/ConnectException\00", align 16
@.str.97 = private unnamed_addr constant [27 x i8] c"java/net/HttpURLConnection\00", align 16
@.str.98 = private unnamed_addr constant [27 x i8] c"java/net/InetSocketAddress\00", align 16
@.str.99 = private unnamed_addr constant [27 x i8] c"java/net/ProtocolException\00", align 16
@.str.100 = private unnamed_addr constant [15 x i8] c"java/net/Proxy\00", align 1
@.str.101 = private unnamed_addr constant [20 x i8] c"java/net/Proxy$Type\00", align 16
@.str.102 = private unnamed_addr constant [23 x i8] c"java/net/SocketAddress\00", align 16
@.str.103 = private unnamed_addr constant [25 x i8] c"java/net/SocketException\00", align 16
@.str.104 = private unnamed_addr constant [32 x i8] c"java/net/SocketTimeoutException\00", align 16
@.str.105 = private unnamed_addr constant [33 x i8] c"java/net/UnknownServiceException\00", align 16
@.str.106 = private unnamed_addr constant [13 x i8] c"java/net/URL\00", align 1
@.str.107 = private unnamed_addr constant [23 x i8] c"java/net/URLConnection\00", align 16
@.str.108 = private unnamed_addr constant [18 x i8] c"java/security/Key\00", align 16
@.str.109 = private unnamed_addr constant [24 x i8] c"java/security/Principal\00", align 16
@.str.110 = private unnamed_addr constant [25 x i8] c"java/security/PrivateKey\00", align 16
@.str.111 = private unnamed_addr constant [25 x i8] c"java/security/KeyFactory\00", align 16
@.str.112 = private unnamed_addr constant [23 x i8] c"java/security/KeyStore\00", align 16
@.str.113 = private unnamed_addr constant [27 x i8] c"java/security/SecureRandom\00", align 16
@.str.114 = private unnamed_addr constant [34 x i8] c"java/security/spec/EncodedKeySpec\00", align 16
@.str.115 = private unnamed_addr constant [27 x i8] c"java/security/spec/KeySpec\00", align 16
@.str.116 = private unnamed_addr constant [39 x i8] c"java/security/spec/PKCS8EncodedKeySpec\00", align 16
@.str.117 = private unnamed_addr constant [31 x i8] c"java/security/cert/Certificate\00", align 16
@.str.118 = private unnamed_addr constant [30 x i8] c"java/nio/channels/FileChannel\00", align 16
@.str.119 = private unnamed_addr constant [51 x i8] c"java/nio/channels/spi/AbstractInterruptibleChannel\00", align 16
@.str.120 = private unnamed_addr constant [24 x i8] c"java/io/FileInputStream\00", align 16
@.str.121 = private unnamed_addr constant [20 x i8] c"java/io/InputStream\00", align 16
@.str.122 = private unnamed_addr constant [31 x i8] c"java/io/InterruptedIOException\00", align 16
@.str.123 = private unnamed_addr constant [20 x i8] c"java/io/IOException\00", align 16
@.str.124 = private unnamed_addr constant [21 x i8] c"java/io/Serializable\00", align 16
@.str.125 = private unnamed_addr constant [21 x i8] c"java/io/OutputStream\00", align 16
@.str.126 = private unnamed_addr constant [20 x i8] c"java/io/PrintWriter\00", align 16
@.str.127 = private unnamed_addr constant [15 x i8] c"java/io/Reader\00", align 1
@.str.128 = private unnamed_addr constant [21 x i8] c"java/io/StringWriter\00", align 16
@.str.129 = private unnamed_addr constant [15 x i8] c"java/io/Writer\00", align 1
@.str.130 = private unnamed_addr constant [22 x i8] c"java/util/Enumeration\00", align 16
@.str.131 = private unnamed_addr constant [19 x i8] c"java/util/Iterator\00", align 16
@.str.132 = private unnamed_addr constant [17 x i8] c"java/util/Random\00", align 16
@.str.133 = private unnamed_addr constant [28 x i8] c"java/util/function/Consumer\00", align 16
@.str.134 = private unnamed_addr constant [18 x i8] c"java/lang/Boolean\00", align 16
@.str.135 = private unnamed_addr constant [15 x i8] c"java/lang/Byte\00", align 1
@.str.136 = private unnamed_addr constant [20 x i8] c"java/lang/Character\00", align 16
@.str.137 = private unnamed_addr constant [16 x i8] c"java/lang/Class\00", align 16
@.str.138 = private unnamed_addr constant [33 x i8] c"java/lang/ClassNotFoundException\00", align 16
@.str.139 = private unnamed_addr constant [17 x i8] c"java/lang/Double\00", align 16
@.str.140 = private unnamed_addr constant [20 x i8] c"java/lang/Exception\00", align 16
@.str.141 = private unnamed_addr constant [16 x i8] c"java/lang/Float\00", align 16
@.str.142 = private unnamed_addr constant [23 x i8] c"java/lang/CharSequence\00", align 16
@.str.143 = private unnamed_addr constant [18 x i8] c"java/lang/Integer\00", align 16
@.str.144 = private unnamed_addr constant [15 x i8] c"java/lang/Long\00", align 1
@.str.145 = private unnamed_addr constant [17 x i8] c"java/lang/Object\00", align 16
@.str.146 = private unnamed_addr constant [27 x i8] c"java/lang/RuntimeException\00", align 16
@.str.147 = private unnamed_addr constant [16 x i8] c"java/lang/Short\00", align 16
@.str.148 = private unnamed_addr constant [17 x i8] c"java/lang/String\00", align 16
@.str.149 = private unnamed_addr constant [17 x i8] c"java/lang/Thread\00", align 16
@.str.150 = private unnamed_addr constant [35 x i8] c"mono/java/lang/RunnableImplementor\00", align 16
@.str.151 = private unnamed_addr constant [20 x i8] c"java/lang/Throwable\00", align 16
@.str.152 = private unnamed_addr constant [29 x i8] c"java/lang/ClassCastException\00", align 16
@.str.153 = private unnamed_addr constant [15 x i8] c"java/lang/Enum\00", align 1
@.str.154 = private unnamed_addr constant [16 x i8] c"java/lang/Error\00", align 16
@.str.155 = private unnamed_addr constant [35 x i8] c"java/lang/IllegalArgumentException\00", align 16
@.str.156 = private unnamed_addr constant [32 x i8] c"java/lang/IllegalStateException\00", align 16
@.str.157 = private unnamed_addr constant [36 x i8] c"java/lang/IndexOutOfBoundsException\00", align 16
@.str.158 = private unnamed_addr constant [19 x i8] c"java/lang/Runnable\00", align 16
@.str.159 = private unnamed_addr constant [23 x i8] c"java/lang/LinkageError\00", align 16
@.str.160 = private unnamed_addr constant [31 x i8] c"java/lang/NoClassDefFoundError\00", align 16
@.str.161 = private unnamed_addr constant [31 x i8] c"java/lang/NullPointerException\00", align 16
@.str.162 = private unnamed_addr constant [17 x i8] c"java/lang/Number\00", align 16
@.str.163 = private unnamed_addr constant [39 x i8] c"java/lang/ReflectiveOperationException\00", align 16
@.str.164 = private unnamed_addr constant [28 x i8] c"java/lang/SecurityException\00", align 16
@.str.165 = private unnamed_addr constant [28 x i8] c"java/lang/StackTraceElement\00", align 16
@.str.166 = private unnamed_addr constant [40 x i8] c"java/lang/UnsupportedOperationException\00", align 16
@.str.167 = private unnamed_addr constant [25 x i8] c"mono/android/TypeManager\00", align 16
@.str.168 = private unnamed_addr constant [35 x i8] c"crc64f6f2b5806e9afa0f/MainActivity\00", align 16
@.str.169 = private unnamed_addr constant [53 x i8] c"crc64f6f2b5806e9afa0f/MainActivity_GameWebViewClient\00", align 16
@.str.170 = private unnamed_addr constant [55 x i8] c"crc64f6f2b5806e9afa0f/MainActivity_GameWebChromeClient\00", align 16
@.str.171 = private unnamed_addr constant [46 x i8] c"crc64f6f2b5806e9afa0f/MainActivity_GameBridge\00", align 16

;TypeMapModule
@.TypeMapModule.0_assembly_name = private unnamed_addr constant [13 x i8] c"Mono.Android\00", align 1
@.TypeMapModule.1_assembly_name = private unnamed_addr constant [21 x i8] c"XionghanChessAndroid\00", align 16

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
