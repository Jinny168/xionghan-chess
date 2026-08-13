package crc64f6f2b5806e9afa0f;


public class MainActivity_GameBridge
	extends java.lang.Object
	implements
		mono.android.IGCUserPeer
{
/** @hide */
	public static final String __md_methods;
	static {
		__md_methods = 
			"n_SaveGame:(Ljava/lang/String;Ljava/lang/String;)V:__export__\n" +
			"n_RetryServer:()V:__export__\n" +
			"n_OpenServerSettings:()V:__export__\n" +
			"n_GetServerUrl:()Ljava/lang/String;:__export__\n" +
			"";
		mono.android.Runtime.register ("XionghanChessAndroid.MainActivity+GameBridge, XionghanChessAndroid", MainActivity_GameBridge.class, __md_methods);
	}

	public MainActivity_GameBridge ()
	{
		super ();
		if (getClass () == MainActivity_GameBridge.class) {
			mono.android.TypeManager.Activate ("XionghanChessAndroid.MainActivity+GameBridge, XionghanChessAndroid", "", this, new java.lang.Object[] {  });
		}
	}

	public MainActivity_GameBridge (crc64f6f2b5806e9afa0f.MainActivity p0)
	{
		super ();
		if (getClass () == MainActivity_GameBridge.class) {
			mono.android.TypeManager.Activate ("XionghanChessAndroid.MainActivity+GameBridge, XionghanChessAndroid", "XionghanChessAndroid.MainActivity, XionghanChessAndroid", this, new java.lang.Object[] { p0 });
		}
	}

@android.webkit.JavascriptInterface
	public void saveGame (java.lang.String p0, java.lang.String p1)
	{
		n_SaveGame (p0, p1);
	}

	private native void n_SaveGame (java.lang.String p0, java.lang.String p1);

@android.webkit.JavascriptInterface
	public void retryServer ()
	{
		n_RetryServer ();
	}

	private native void n_RetryServer ();

@android.webkit.JavascriptInterface
	public void openServerSettings ()
	{
		n_OpenServerSettings ();
	}

	private native void n_OpenServerSettings ();

@android.webkit.JavascriptInterface
	public java.lang.String getServerUrl ()
	{
		return n_GetServerUrl ();
	}

	private native java.lang.String n_GetServerUrl ();

	private java.util.ArrayList refList;
	public void monodroidAddReference (java.lang.Object obj)
	{
		if (refList == null)
			refList = new java.util.ArrayList ();
		refList.add (obj);
	}

	public void monodroidClearReferences ()
	{
		if (refList != null)
			refList.clear ();
	}
}
