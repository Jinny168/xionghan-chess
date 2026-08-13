package crc64f6f2b5806e9afa0f;


public class MainActivity_GameWebChromeClient
	extends android.webkit.WebChromeClient
	implements
		mono.android.IGCUserPeer
{
/** @hide */
	public static final String __md_methods;
	static {
		__md_methods = 
			"n_onShowFileChooser:(Landroid/webkit/WebView;Landroid/webkit/ValueCallback;Landroid/webkit/WebChromeClient$FileChooserParams;)Z:GetOnShowFileChooser_Landroid_webkit_WebView_Landroid_webkit_ValueCallback_Landroid_webkit_WebChromeClient_FileChooserParams_Handler\n" +
			"";
		mono.android.Runtime.register ("XionghanChessAndroid.MainActivity+GameWebChromeClient, XionghanChessAndroid", MainActivity_GameWebChromeClient.class, __md_methods);
	}

	public MainActivity_GameWebChromeClient ()
	{
		super ();
		if (getClass () == MainActivity_GameWebChromeClient.class) {
			mono.android.TypeManager.Activate ("XionghanChessAndroid.MainActivity+GameWebChromeClient, XionghanChessAndroid", "", this, new java.lang.Object[] {  });
		}
	}

	public MainActivity_GameWebChromeClient (crc64f6f2b5806e9afa0f.MainActivity p0)
	{
		super ();
		if (getClass () == MainActivity_GameWebChromeClient.class) {
			mono.android.TypeManager.Activate ("XionghanChessAndroid.MainActivity+GameWebChromeClient, XionghanChessAndroid", "XionghanChessAndroid.MainActivity, XionghanChessAndroid", this, new java.lang.Object[] { p0 });
		}
	}

	public boolean onShowFileChooser (android.webkit.WebView p0, android.webkit.ValueCallback p1, android.webkit.WebChromeClient.FileChooserParams p2)
	{
		return n_onShowFileChooser (p0, p1, p2);
	}

	private native boolean n_onShowFileChooser (android.webkit.WebView p0, android.webkit.ValueCallback p1, android.webkit.WebChromeClient.FileChooserParams p2);

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
