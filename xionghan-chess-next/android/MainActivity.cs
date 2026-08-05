using Android.App;
using Android.Content;
using Android.OS;
using Android.Views;
using Android.Webkit;
using Android.Widget;

namespace XionghanChessAndroid;

[Activity(Label = "@string/app_name", MainLauncher = true, ScreenOrientation = Android.Content.PM.ScreenOrientation.Unspecified, Exported = true)]
public sealed class MainActivity : Activity
{
    const string PreferencesName = "xionghan-chess";
    const string ServerUrlKey = "server_url";
    const string DefaultServerUrl = "http://10.0.2.2:8000/";
    WebView? webView;

    protected override void OnCreate(Bundle? savedInstanceState)
    {
        base.OnCreate(savedInstanceState);
        Window.SetStatusBarColor(Android.Graphics.Color.Rgb(91, 27, 24));
        webView = new WebView(this);
        webView.Settings.JavaScriptEnabled = true;
        webView.Settings.DomStorageEnabled = true;
        webView.Settings.MediaPlaybackRequiresUserGesture = false;
        webView.Settings.AllowFileAccess = true;
        webView.Settings.MixedContentMode = MixedContentHandling.CompatibilityMode;
        webView.SetWebViewClient(new WebViewClient());
        webView.SetBackgroundColor(Android.Graphics.Color.Rgb(241, 223, 183));
        webView.ClearCache(true);
        SetContentView(webView);

        var savedUrl = GetSharedPreferences(PreferencesName, FileCreationMode.Private)?.GetString(ServerUrlKey, null);
        if (string.IsNullOrWhiteSpace(savedUrl)) ShowServerDialog(DefaultServerUrl);
        else LoadGame(savedUrl);
    }

    void ShowServerDialog(string initial)
    {
        var input = new EditText(this) { Text = initial, Hint = "例如 http://192.168.1.10:8000/" };
        input.SetSingleLine(true);
        var container = new LinearLayout(this) { Orientation = Orientation.Vertical };
        container.SetPadding(48, 8, 48, 0);
        container.AddView(input);
        new AlertDialog.Builder(this)
            .SetTitle("连接匈汉象棋服务")
            .SetMessage("请输入 FastAPI 服务地址。模拟器可使用 10.0.2.2 访问开发机，手机请填写局域网或公网地址。")
            .SetView(container)
            .SetPositiveButton("进入", (_, _) =>
            {
                var url = input.Text?.Trim();
                if (string.IsNullOrWhiteSpace(url)) url = initial;
                if (!url.EndsWith('/')) url += "/";
                GetSharedPreferences(PreferencesName, FileCreationMode.Private)?.Edit()?.PutString(ServerUrlKey, url).Apply();
                LoadGame(url);
            })
            .SetNegativeButton("退出", (_, _) => Finish())
            .SetCancelable(false)
            .Show();
    }

    void LoadGame(string url)
    {
        webView?.LoadUrl(url);
    }

    public override bool OnCreateOptionsMenu(IMenu? menu)
    {
        menu?.Add("刷新");
        menu?.Add("服务器设置");
        return base.OnCreateOptionsMenu(menu);
    }

    public override bool OnOptionsItemSelected(IMenuItem item)
    {
        if (item.TitleFormatted?.ToString() == "刷新")
        {
            webView?.Reload();
            return true;
        }
        if (item.TitleFormatted?.ToString() == "服务器设置")
        {
            var current = GetSharedPreferences(PreferencesName, FileCreationMode.Private)?.GetString(ServerUrlKey, DefaultServerUrl) ?? DefaultServerUrl;
            ShowServerDialog(current);
            return true;
        }
        return base.OnOptionsItemSelected(item);
    }

    public override void OnBackPressed()
    {
        if (webView?.CanGoBack() == true) webView.GoBack();
        else base.OnBackPressed();
    }
}
