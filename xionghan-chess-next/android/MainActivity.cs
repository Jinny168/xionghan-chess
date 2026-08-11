using Android.App;
using Android.Content;
using Android.OS;
using Android.Views;
using Android.Webkit;
using Android.Widget;
using Java.Interop;
using System.Net.Http;
using System.Text;

namespace XionghanChessAndroid;

[Activity(Label = "@string/app_name", MainLauncher = true, ScreenOrientation = Android.Content.PM.ScreenOrientation.Unspecified, Exported = true)]
public sealed class MainActivity : Activity
{
    const string PreferencesName = "xionghan-chess";
    const string ServerUrlKey = "server_url";
    const string DefaultServerUrl = "http://10.0.2.2:8000/";
    const string OfflineUrl = "file:///android_asset/offline/index.html";
    const int OpenGameRequest = 1201;
    const int SaveGameRequest = 1202;
    WebView? webView;
    IValueCallback? filePathCallback;
    string? pendingGameContent;
    GameBridge? gameBridge;
    readonly HttpClient healthClient = new() { Timeout = TimeSpan.FromSeconds(4) };
    System.Threading.Timer? connectionTimer;
    string serverUrl = DefaultServerUrl;
    bool showingServerPage;
    bool checkingServer;
    int consecutiveFailures;
    string L(string zh, string en) =>
        System.Globalization.CultureInfo.CurrentUICulture.TwoLetterISOLanguageName == "en" ? en : zh;

    protected override void OnCreate(Bundle? savedInstanceState)
    {
        base.OnCreate(savedInstanceState);
        try
        {
            EnterImmersiveMode();
            ActionBar?.Hide();
            webView = new WebView(this);
            webView.Settings.JavaScriptEnabled = true;
            webView.Settings.DomStorageEnabled = true;
            webView.Settings.MediaPlaybackRequiresUserGesture = false;
            webView.Settings.AllowFileAccess = true;
            webView.Settings.MixedContentMode = MixedContentHandling.CompatibilityMode;
            webView.Settings.SetSupportZoom(false);
            webView.Settings.BuiltInZoomControls = false;
            webView.Settings.DisplayZoomControls = false;
            webView.SetWebViewClient(new GameWebViewClient(this));
            webView.SetWebChromeClient(new GameWebChromeClient(this));
            gameBridge = new GameBridge(this);
            webView.AddJavascriptInterface(gameBridge, "XionghanAndroid");
            webView.SetBackgroundColor(Android.Graphics.Color.Rgb(241, 223, 183));
            SetContentView(webView);

            serverUrl = NormalizeServerUrl(
                GetSharedPreferences(PreferencesName, FileCreationMode.Private)?.GetString(ServerUrlKey, DefaultServerUrl)
                ?? DefaultServerUrl);
            LoadOfflineGame(L("离线同机模式可直接使用，正在检测服务器", "Offline pass-and-play is ready. Checking server."));
            connectionTimer = new System.Threading.Timer(_ => _ = CheckServerAsync(), null,
                TimeSpan.FromSeconds(1), TimeSpan.FromSeconds(10));
        }
        catch (Exception exception)
        {
            var fallback = new TextView(this) { Text = $"{L("应用启动失败，请更新 Android System WebView 后重试。", "Startup failed. Update Android System WebView and try again.")}\n\n{exception.Message}", TextSize = 18 };
            fallback.SetPadding(48, 72, 48, 48);
            SetContentView(fallback);
        }
    }

    void EnterImmersiveMode()
    {
        try
        {
            if (Build.VERSION.SdkInt >= BuildVersionCodes.R)
            {
                Window.SetDecorFitsSystemWindows(false);
                var controller = Window.InsetsController;
                controller?.Hide(WindowInsets.Type.StatusBars() | WindowInsets.Type.NavigationBars());
                if (controller is not null)
                    controller.SystemBarsBehavior = (int)WindowInsetsControllerBehavior.ShowTransientBarsBySwipe;
            }
            else
            {
#pragma warning disable CS0618
                Window.DecorView.SystemUiVisibility = (StatusBarVisibility)(
                    SystemUiFlags.Fullscreen | SystemUiFlags.HideNavigation |
                    SystemUiFlags.ImmersiveSticky | SystemUiFlags.LayoutFullscreen |
                    SystemUiFlags.LayoutHideNavigation | SystemUiFlags.LayoutStable);
#pragma warning restore CS0618
            }
        }
        catch { }
    }

    public override void OnWindowFocusChanged(bool hasFocus)
    {
        base.OnWindowFocusChanged(hasFocus);
        if (hasFocus)
        {
            EnterImmersiveMode();
            RequestGameRedraw();
        }
    }

    protected override void OnResume()
    {
        base.OnResume();
        EnterImmersiveMode();
        RequestGameRedraw();
    }

    void RequestGameRedraw() => webView?.EvaluateJavascript(
        "requestAnimationFrame(function(){document.body.classList.add('android-client');window.dispatchEvent(new Event('resize'));if(window.redrawBoard)window.redrawBoard();});",
        null);

    void ShowServerDialog(string initial)
    {
        var input = new EditText(this) { Text = initial, Hint = L("例如 http://192.168.1.10:8000/", "For example http://192.168.1.10:8000/") };
        input.SetSingleLine(true);
        var container = new LinearLayout(this) { Orientation = Orientation.Vertical };
        container.SetPadding(48, 8, 48, 0);
        container.AddView(input);
        new AlertDialog.Builder(this)
            .SetTitle(L("连接匈汉象棋服务", "Connect to Xionghan Chess server"))
            .SetMessage(L("请输入 FastAPI 服务地址。离线同机对战不需要服务器；连接成功后会自动恢复人机和联网功能。", "Enter the FastAPI server URL. Offline pass-and-play does not need a server; AI and online modes resume after connection."))
            .SetView(container)
            .SetPositiveButton(L("进入", "Enter"), (_, _) =>
            {
                var url = input.Text?.Trim();
                if (string.IsNullOrWhiteSpace(url)) url = initial;
                serverUrl = NormalizeServerUrl(url);
                GetSharedPreferences(PreferencesName, FileCreationMode.Private)?.Edit()
                    ?.PutString(ServerUrlKey, serverUrl).Apply();
                _ = CheckServerAsync(true);
            })
            .SetNegativeButton(L("继续离线", "Stay offline"), (_, _) => LoadOfflineGame(L("已保持离线同机模式", "Staying in offline pass-and-play")))
            .SetCancelable(true)
            .Show();
    }

    static string NormalizeServerUrl(string? value)
    {
        var url = string.IsNullOrWhiteSpace(value) ? DefaultServerUrl : value.Trim();
        return url.EndsWith('/') ? url : url + "/";
    }

    internal void LoadOfflineGame(string message)
    {
        RunOnUiThread(() =>
        {
            showingServerPage = false;
            webView?.LoadUrl($"{OfflineUrl}?message={Android.Net.Uri.Encode(message)}");
        });
    }

    async Task CheckServerAsync(bool announceFailure = false)
    {
        if (checkingServer) return;
        checkingServer = true;
        try
        {
            using var response = await healthClient.GetAsync(new Uri(new Uri(serverUrl), "api/health"));
            if (!response.IsSuccessStatusCode) throw new HttpRequestException($"HTTP {(int)response.StatusCode}");
            consecutiveFailures = 0;
            if (!showingServerPage)
            {
                RunOnUiThread(() =>
                {
                    showingServerPage = true;
                    webView?.LoadUrl(serverUrl);
                    Toast.MakeText(this, L("服务器连接成功，在线功能已恢复", "Server connected. Online features restored."), ToastLength.Short)?.Show();
                });
            }
        }
        catch
        {
            consecutiveFailures++;
            if (showingServerPage && consecutiveFailures >= 2)
                LoadOfflineGame(L("服务器连接中断，已切换到离线同机模式", "Server connection lost. Switched to offline pass-and-play."));
            else if (announceFailure)
                RunOnUiThread(() => Toast.MakeText(this, L("服务器不可用，继续使用离线同机模式", "Server unavailable. Continuing offline pass-and-play."), ToastLength.Long)?.Show());
        }
        finally
        {
            checkingServer = false;
        }
    }

    internal void OpenGameFile(IValueCallback? callback, WebChromeClient.FileChooserParams? chooserParams)
    {
        filePathCallback?.OnReceiveValue(null);
        filePathCallback = callback;
        Intent intent;
        try
        {
            intent = chooserParams?.CreateIntent() ?? new Intent(Intent.ActionOpenDocument);
        }
        catch
        {
            intent = new Intent(Intent.ActionOpenDocument);
        }
        intent.SetType("application/json");
        intent.AddCategory(Intent.CategoryOpenable);
        intent.PutExtra(Intent.ExtraMimeTypes, new[] { "application/json", "application/octet-stream", "text/plain" });
        try
        {
            StartActivityForResult(intent, OpenGameRequest);
        }
        catch (ActivityNotFoundException)
        {
            filePathCallback?.OnReceiveValue(null);
            filePathCallback = null;
            Toast.MakeText(this, L("没有可用的文件选择器", "No file picker is available"), ToastLength.Long)?.Show();
        }
    }

    internal void SaveGameFile(string filename, string content)
    {
        pendingGameContent = content;
        var intent = new Intent(Intent.ActionCreateDocument);
        intent.AddCategory(Intent.CategoryOpenable);
        intent.SetType("application/json");
        intent.PutExtra(Intent.ExtraTitle, filename);
        try
        {
            StartActivityForResult(intent, SaveGameRequest);
        }
        catch (ActivityNotFoundException)
        {
            pendingGameContent = null;
            Toast.MakeText(this, L("没有可用的文件保存器", "No file saver is available"), ToastLength.Long)?.Show();
        }
    }

    protected override void OnActivityResult(int requestCode, Result resultCode, Intent? data)
    {
        if (requestCode == OpenGameRequest)
        {
            filePathCallback?.OnReceiveValue(WebChromeClient.FileChooserParams.ParseResult((int)resultCode, data));
            filePathCallback = null;
            return;
        }
        if (requestCode == SaveGameRequest)
        {
            if (resultCode == Result.Ok && data?.Data is { } uri && pendingGameContent is { } content)
            {
                try
                {
                    using var stream = ContentResolver?.OpenOutputStream(uri);
                    using var writer = new StreamWriter(stream!, new UTF8Encoding(false));
                    writer.Write(content);
                    Toast.MakeText(this, L("棋局文件已保存", "Game file saved"), ToastLength.Short)?.Show();
                }
                catch (Exception exception)
                {
                    Toast.MakeText(this, $"{L("保存失败：", "Save failed: ")}{exception.Message}", ToastLength.Long)?.Show();
                }
            }
            pendingGameContent = null;
            return;
        }
        base.OnActivityResult(requestCode, resultCode, data);
    }

    public override bool OnCreateOptionsMenu(IMenu? menu)
    {
        menu?.Add(L("刷新", "Refresh"));
        menu?.Add(L("离线同机", "Offline"));
        menu?.Add(L("重新连接", "Reconnect"));
        menu?.Add(L("服务器设置", "Server settings"));
        return base.OnCreateOptionsMenu(menu);
    }

    public override bool OnOptionsItemSelected(IMenuItem item)
    {
        if (item.TitleFormatted?.ToString() == L("刷新", "Refresh"))
        {
            webView?.Reload();
            return true;
        }
        if (item.TitleFormatted?.ToString() == L("离线同机", "Offline"))
        {
            LoadOfflineGame(L("已进入离线同机模式", "Entered offline pass-and-play"));
            return true;
        }
        if (item.TitleFormatted?.ToString() == L("重新连接", "Reconnect"))
        {
            _ = CheckServerAsync(true);
            return true;
        }
        if (item.TitleFormatted?.ToString() == L("服务器设置", "Server settings"))
        {
            ShowServerDialog(serverUrl);
            return true;
        }
        return base.OnOptionsItemSelected(item);
    }

    public override void OnBackPressed()
    {
        if (webView?.CanGoBack() == true) webView.GoBack();
        else base.OnBackPressed();
    }

    protected override void OnDestroy()
    {
        connectionTimer?.Dispose();
        healthClient.Dispose();
        base.OnDestroy();
    }

    [Android.Runtime.Preserve(AllMembers = true)]
    sealed class GameWebViewClient(MainActivity activity) : WebViewClient
    {
        public override void OnPageFinished(WebView? view, string? url)
        {
            base.OnPageFinished(view, url);
            activity.RequestGameRedraw();
            if (!string.IsNullOrWhiteSpace(url) && url.StartsWith(activity.serverUrl, StringComparison.OrdinalIgnoreCase))
            {
                activity.showingServerPage = true;
                activity.consecutiveFailures = 0;
            }
        }

        public override void OnReceivedError(WebView? view, IWebResourceRequest? request, WebResourceError? error)
        {
            base.OnReceivedError(view, request, error);
            if (request?.IsForMainFrame == true && activity.showingServerPage)
                activity.LoadOfflineGame(activity.L("服务器页面无法访问，已切换到离线同机模式", "Server page unavailable. Switched to offline pass-and-play."));
        }
    }

    [Android.Runtime.Preserve(AllMembers = true)]
    sealed class GameWebChromeClient(MainActivity activity) : WebChromeClient
    {
        public override bool OnShowFileChooser(WebView? webView, IValueCallback? filePathCallback,
                                               FileChooserParams? fileChooserParams)
        {
            activity.OpenGameFile(filePathCallback, fileChooserParams);
            return true;
        }
    }

    [Android.Runtime.Preserve(AllMembers = true)]
    sealed class GameBridge(MainActivity activity) : Java.Lang.Object
    {
        [JavascriptInterface]
        [Export("saveGame")]
        public void SaveGame(string filename, string content)
        {
            activity.RunOnUiThread(() => activity.SaveGameFile(filename, content));
        }

        [JavascriptInterface]
        [Export("retryServer")]
        public void RetryServer() => _ = activity.CheckServerAsync(true);

        [JavascriptInterface]
        [Export("openServerSettings")]
        public void OpenServerSettings() => activity.RunOnUiThread(() => activity.ShowServerDialog(activity.serverUrl));

        [JavascriptInterface]
        [Export("getServerUrl")]
        public string GetServerUrl() => activity.serverUrl;
    }
}
