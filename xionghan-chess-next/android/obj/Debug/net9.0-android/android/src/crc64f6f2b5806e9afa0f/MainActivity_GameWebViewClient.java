package crc64f6f2b5806e9afa0f;


public class MainActivity_GameWebViewClient
	extends android.webkit.WebViewClient
	implements
		mono.android.IGCUserPeer
{
/** @hide */
	public static final String __md_methods;
	static {
		__md_methods = 
			"n_onPageFinished:(Landroid/webkit/WebView;Ljava/lang/String;)V:GetOnPageFinished_Landroid_webkit_WebView_Ljava_lang_String_Handler\n" +
			"n_onReceivedError:(Landroid/webkit/WebView;Landroid/webkit/WebResourceRequest;Landroid/webkit/WebResourceError;)V:GetOnReceivedError_Landroid_webkit_WebView_Landroid_webkit_WebResourceRequest_Landroid_webkit_WebResourceError_Handler\n" +
			"";
		mono.android.Runtime.register ("XionghanChessAndroid.MainActivity+GameWebViewClient, XionghanChessAndroid", MainActivity_GameWebViewClient.class, __md_methods);
	}

	public MainActivity_GameWebViewClient ()
	{
		super ();
		if (getClass () == MainActivity_GameWebViewClient.class) {
			mono.android.TypeManager.Activate ("XionghanChessAndroid.MainActivity+GameWebViewClient, XionghanChessAndroid", "", this, new java.lang.Object[] {  });
		}
	}

	public MainActivity_GameWebViewClient (crc64f6f2b5806e9afa0f.MainActivity p0)
	{
		super ();
		if (getClass () == MainActivity_GameWebViewClient.class) {
			mono.android.TypeManager.Activate ("XionghanChessAndroid.MainActivity+GameWebViewClient, XionghanChessAndroid", "XionghanChessAndroid.MainActivity, XionghanChessAndroid", this, new java.lang.Object[] { p0 });
		}
	}

	public void onPageFinished (android.webkit.WebView p0, java.lang.String p1)
	{
		n_onPageFinished (p0, p1);
	}

	private native void n_onPageFinished (android.webkit.WebView p0, java.lang.String p1);

	public void onReceivedError (android.webkit.WebView p0, android.webkit.WebResourceRequest p1, android.webkit.WebResourceError p2)
	{
		n_onReceivedError (p0, p1, p2);
	}

	private native void n_onReceivedError (android.webkit.WebView p0, android.webkit.WebResourceRequest p1, android.webkit.WebResourceError p2);

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
