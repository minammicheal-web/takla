package com.mina.takla;

import android.Manifest;
import android.app.Activity;
import android.app.KeyguardManager;
import android.content.ContentValues;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.ComponentName;
import android.content.pm.ActivityInfo;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.content.res.Configuration;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Color;
import android.graphics.Matrix;
import android.media.ExifInterface;
import android.util.Base64;
import android.graphics.drawable.GradientDrawable;
import android.hardware.biometrics.BiometricManager;
import android.hardware.biometrics.BiometricPrompt;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.CancellationSignal;
import android.os.Environment;
import android.provider.MediaStore;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.webkit.JavascriptInterface;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.TextView;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.Iterator;
import java.io.FileOutputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import org.json.JSONObject;
import android.print.PrintAttributes;
import android.print.PrintManager;
import com.google.mlkit.vision.barcode.common.Barcode;
import com.google.mlkit.vision.codescanner.GmsBarcodeScanner;
import com.google.mlkit.vision.codescanner.GmsBarcodeScannerOptions;
import com.google.mlkit.vision.codescanner.GmsBarcodeScanning;

public class MainActivity extends Activity {
    private static final int PICK = 1;
    private static final int LOCK = 6;
    private static final int PHOTO = 7;
    private int photoReq = 0;
    private Uri photoOut = null;
    private WebView web;
    private ValueCallback<Uri[]> fileCallback;
    private LinearLayout lockView;
    private TextView lockMsg;
    private boolean unlocked = false, authing = false;
    private long leftAt = 0;
    private String authPurpose = "unlock";
    private WebView printView;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        web = new WebView(this);
        FrameLayout root = new FrameLayout(this);
        root.addView(web, new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        lockView = buildLockView();
        root.addView(lockView, new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        lockView.setVisibility(lockOn() ? View.VISIBLE : View.GONE);
        setContentView(root);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setAllowFileAccess(true);
        web.addJavascriptInterface(new Bridge(), "Android");
        web.addJavascriptInterface(new M3Feedback(this, web), "M3");

        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest r) {
                Uri u = r.getUrl();
                if ("file".equals(u.getScheme())) return false;
                try { startActivity(new Intent(Intent.ACTION_VIEW, u)); } catch (Exception ignored) { }
                return true;
            }
        });

        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(WebView v, ValueCallback<Uri[]> cb, FileChooserParams p) {
                if (fileCallback != null) fileCallback.onReceiveValue(null);
                fileCallback = cb;
                Intent i = new Intent(Intent.ACTION_GET_CONTENT);
                i.addCategory(Intent.CATEGORY_OPENABLE);
                i.setType("*/*");
                try {
                    startActivityForResult(Intent.createChooser(i, L("اختر ملف النسخة الاحتياطية", "Choose the backup file")), PICK);
                } catch (Exception e) {
                    fileCallback = null;
                    return false;
                }
                return true;
            }
        });

        StockWorker.schedule(this);
        if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{ Manifest.permission.POST_NOTIFICATIONS }, 3);
        }

        if (state != null) web.restoreState(state);
        else web.loadUrl("file:///android_asset/index.html");
    }

    @Override
    protected void onActivityResult(int req, int res, Intent data) {
        super.onActivityResult(req, res, data);
        if (req == LOCK) {
            authing = false;
            if (res == RESULT_OK) authOk(); else authFailed(L("لم يتم الفتح.", "Not unlocked."));
            return;
        }
        if (req == PHOTO) { gotPhoto(res, data); return; }
        if (req != PICK || fileCallback == null) return;
        Uri[] out = null;
        if (res == RESULT_OK && data != null && data.getData() != null) out = new Uri[]{ data.getData() };
        fileCallback.onReceiveValue(out);
        fileCallback = null;
    }

    /* ---------- supplier-invoice photos: camera or gallery, stored in files/photos ---------- */

    private File photoDir() { File d = new File(getFilesDir(), "photos"); d.mkdirs(); return d; }

    private File photoFile(String id) { return new File(photoDir(), id.replaceAll("[^A-Za-z0-9_-]", "") + ".jpg"); }

    private void openPhotoPicker(int req) {
        photoReq = req; photoOut = null;
        Intent gal = new Intent(Intent.ACTION_GET_CONTENT); gal.setType("image/*"); gal.addCategory(Intent.CATEGORY_OPENABLE);
        Intent chooser = Intent.createChooser(gal, L("صورة فاتورة المورد", "Supplier invoice photo"));
        try {
            Intent cam = new Intent(MediaStore.ACTION_IMAGE_CAPTURE);
            ContentValues cv = new ContentValues();
            cv.put(MediaStore.Images.Media.DISPLAY_NAME, "takla_invoice_" + System.currentTimeMillis() + ".jpg");
            cv.put(MediaStore.Images.Media.MIME_TYPE, "image/jpeg");
            if (Build.VERSION.SDK_INT >= 29) cv.put(MediaStore.Images.Media.RELATIVE_PATH, Environment.DIRECTORY_PICTURES + "/Takla");
            photoOut = getContentResolver().insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, cv);
            if (photoOut != null) {
                cam.putExtra(MediaStore.EXTRA_OUTPUT, photoOut);
                cam.addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION | Intent.FLAG_GRANT_READ_URI_PERMISSION);
            }
            chooser.putExtra(Intent.EXTRA_INITIAL_INTENTS, new Intent[]{ cam });
        } catch (Exception e) { photoOut = null; }
        try { startActivityForResult(chooser, PHOTO); }
        catch (Exception e) { photoDone(null, e.getMessage()); }
    }

    private void gotPhoto(int res, Intent data) {
        final Uri camUri = photoOut; photoOut = null;
        if (res != RESULT_OK) { dropUri(camUri); photoDone(null, null); return; }
        final Uri picked = data != null ? data.getData() : null;
        final Bitmap thumb = (picked == null && data != null && data.getExtras() != null && data.getExtras().get("data") instanceof Bitmap) ? (Bitmap) data.getExtras().get("data") : null;
        new Thread(() -> {
            String url = null, err = null;
            try {
                Uri src = picked != null ? picked : camUri;
                Bitmap b = src != null ? loadScaled(src, 1600) : null;
                if (b == null) b = thumb;
                if (b == null) err = L("مفيش صورة", "No photo");
                else {
                    ByteArrayOutputStream out = new ByteArrayOutputStream();
                    b.compress(Bitmap.CompressFormat.JPEG, 72, out);
                    url = "data:image/jpeg;base64," + Base64.encodeToString(out.toByteArray(), Base64.NO_WRAP);
                }
            } catch (Throwable e) { err = String.valueOf(e.getMessage()); }
            if (picked != null) dropUri(camUri); else if (camUri != null) dropUri(camUri);
            photoDone(url, err);
        }).start();
    }

    private void dropUri(Uri u) { if (u == null) return; try { getContentResolver().delete(u, null, null); } catch (Exception ignored) {} }

    private Bitmap loadScaled(Uri u, int max) throws Exception {
        BitmapFactory.Options o = new BitmapFactory.Options(); o.inJustDecodeBounds = true;
        try (InputStream in = getContentResolver().openInputStream(u)) { BitmapFactory.decodeStream(in, null, o); }
        if (o.outWidth <= 0 || o.outHeight <= 0) return null;
        int sample = 1; while (Math.max(o.outWidth, o.outHeight) / (sample * 2) >= max) sample *= 2;
        BitmapFactory.Options o2 = new BitmapFactory.Options(); o2.inSampleSize = sample;
        Bitmap b;
        try (InputStream in = getContentResolver().openInputStream(u)) { b = BitmapFactory.decodeStream(in, null, o2); }
        if (b == null) return null;
        int rot = 0;
        try (InputStream in = getContentResolver().openInputStream(u)) {
            if (Build.VERSION.SDK_INT >= 24) {
                int or = new ExifInterface(in).getAttributeInt(ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL);
                rot = or == ExifInterface.ORIENTATION_ROTATE_90 ? 90 : or == ExifInterface.ORIENTATION_ROTATE_180 ? 180 : or == ExifInterface.ORIENTATION_ROTATE_270 ? 270 : 0;
            }
        } catch (Exception ignored) {}
        float s = Math.min(1f, (float) max / Math.max(b.getWidth(), b.getHeight()));
        if (s < 1f || rot != 0) {
            Matrix m = new Matrix(); m.postScale(s, s); m.postRotate(rot);
            b = Bitmap.createBitmap(b, 0, 0, b.getWidth(), b.getHeight(), m, true);
        }
        return b;
    }

    private void photoDone(String url, String err) {
        final int r = photoReq;
        sendJs("window.onPhoto&&window.onPhoto(" + r + "," + JSONObject.quote(url == null ? "" : url) + "," + JSONObject.quote(err == null ? "" : err) + ")");
    }

    /* ---------- fingerprint / screen-lock protection ---------- */

    private SharedPreferences lockPrefs() { return getSharedPreferences("lock", MODE_PRIVATE); }

    private boolean lockOn() { return lockPrefs().getBoolean("on", false); }

    private boolean deviceSecure() {
        KeyguardManager km = (KeyguardManager) getSystemService(KEYGUARD_SERVICE);
        return km != null && km.isDeviceSecure();
    }

    private LinearLayout buildLockView() {
        LinearLayout v = new LinearLayout(this);
        v.setOrientation(LinearLayout.VERTICAL);
        v.setGravity(Gravity.CENTER);
        v.setBackgroundColor(Color.rgb(14, 21, 19));
        v.setClickable(true);
        TextView t = new TextView(this);
        t.setText(L("Takla Ibrahim مقفول", "Takla Ibrahim is locked"));
        t.setTextColor(Color.WHITE);
        t.setTextSize(24);
        t.setGravity(Gravity.CENTER);
        v.addView(t);
        lockMsg = new TextView(this);
        lockMsg.setText(L("استخدم البصمة أو قفل الشاشة للفتح.", "Use your fingerprint or screen lock to open."));
        lockMsg.setTextColor(Color.rgb(160, 178, 170));
        lockMsg.setTextSize(15);
        lockMsg.setGravity(Gravity.CENTER);
        lockMsg.setPadding(48, 24, 48, 40);
        v.addView(lockMsg);
        Button b = new Button(this);
        b.setText(L("فتح", "Open"));
        b.setAllCaps(false);
        b.setTextSize(17);
        b.setTypeface(android.graphics.Typeface.DEFAULT_BOLD);
        b.setTextColor(Color.rgb(4, 32, 28));
        GradientDrawable bg = new GradientDrawable();
        bg.setColor(Color.rgb(45, 212, 191));
        bg.setCornerRadius(dp(28));
        b.setBackground(bg);
        b.setStateListAnimator(null);
        b.setPadding(dp(40), 0, dp(40), 0);
        b.setMinWidth(dp(160));
        b.setOnClickListener(x -> auth("unlock"));
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, dp(54));
        lp.gravity = Gravity.CENTER_HORIZONTAL;
        v.addView(b, lp);
        return v;
    }

    private String L(String ar, String en) { return "en".equals(getSharedPreferences("stock", MODE_PRIVATE).getString("lang", "ar")) ? en : ar; }

    private int dp(float x) { return Math.round(x * getResources().getDisplayMetrics().density); }

    private void auth(String purpose) {
        if (authing) return;
        authPurpose = purpose;
        if (!deviceSecure()) {
            if ("unlock".equals(purpose)) { authOk(); return; }
            authFailed(L("فعّل البصمة أو قفل الشاشة من إعدادات الموبايل أولاً.", "Turn on fingerprint or screen lock in phone settings first."));
            return;
        }
        authing = true;
        String title = "unlock".equals(purpose) ? L("فتح Takla Ibrahim", "Open Takla Ibrahim") : "enable".equals(purpose) ? L("تشغيل القفل", "Turn on lock") : L("إيقاف القفل", "Turn off lock");
        try {
            if (Build.VERSION.SDK_INT >= 28) {
                BiometricPrompt.Builder b = new BiometricPrompt.Builder(this).setTitle(title)
                        .setSubtitle(L("البصمة أو الوجه أو قفل الشاشة", "Fingerprint, face or screen lock"));
                if (Build.VERSION.SDK_INT >= 30) {
                    b.setAllowedAuthenticators(BiometricManager.Authenticators.BIOMETRIC_WEAK | BiometricManager.Authenticators.DEVICE_CREDENTIAL);
                } else if (Build.VERSION.SDK_INT >= 29) {
                    b.setDeviceCredentialAllowed(true);
                } else {
                    b.setNegativeButton(L("إلغاء", "Cancel"), getMainExecutor(), (d, w) -> { authing = false; authFailed(L("لم يتم الفتح.", "Not unlocked.")); });
                }
                b.build().authenticate(new CancellationSignal(), getMainExecutor(), new BiometricPrompt.AuthenticationCallback() {
                    @Override
                    public void onAuthenticationSucceeded(BiometricPrompt.AuthenticationResult r) { authing = false; authOk(); }

                    @Override
                    public void onAuthenticationError(int code, CharSequence msg) { authing = false; authFailed(String.valueOf(msg)); }
                });
            } else {
                KeyguardManager km = (KeyguardManager) getSystemService(KEYGUARD_SERVICE);
                Intent i = km.createConfirmDeviceCredentialIntent(title, L("استخدم قفل الشاشة", "Use your screen lock"));
                if (i == null) { authing = false; authOk(); return; }
                startActivityForResult(i, LOCK);
            }
        } catch (Exception e) {
            authing = false;
            authFailed(e.getMessage() == null ? L("تعذر طلب البصمة.", "Couldn't ask for the fingerprint.") : e.getMessage());
        }
    }

    private void authOk() {
        if ("enable".equals(authPurpose)) lockPrefs().edit().putBoolean("on", true).apply();
        else if ("disable".equals(authPurpose)) lockPrefs().edit().putBoolean("on", false).apply();
        unlocked = true;
        lockView.setVisibility(View.GONE);
        if (!"unlock".equals(authPurpose)) sendLock(null);
    }

    private void authFailed(String why) {
        if ("unlock".equals(authPurpose)) { lockMsg.setText(why + L("\nاضغط فتح للمحاولة مرة أخرى.", "\nTap Open to try again.")); return; }
        sendLock(why);
    }

    private void sendLock(String error) {
        try {
            JSONObject o = new JSONObject().put("on", lockOn()).put("available", deviceSecure());
            if (error != null) o.put("error", error);
            sendJs("window.onLock&&window.onLock(" + o + ")");
        } catch (Exception ignored) { }
    }

    @Override
    protected void onStop() {
        super.onStop();
        leftAt = System.currentTimeMillis();
        applyIcon();
    }

    /** Switches the launcher icon to the alias of the chosen store activity. Done when the app goes to the background, because launchers may refresh. */
    private void applyIcon() {
        try {
            SharedPreferences p = StockWorker.prefs(this);
            String want = p.getString("iconWant", null);
            if (want == null || want.equals(p.getString("iconNow", "default"))) return;
            PackageManager pm = getPackageManager();
            String pkg = getPackageName();
            ComponentName on = new ComponentName(pkg, pkg + ".act_" + want);
            pm.getActivityInfo(on, PackageManager.MATCH_DISABLED_COMPONENTS); // throws if there is no such alias
            pm.setComponentEnabledSetting(on, PackageManager.COMPONENT_ENABLED_STATE_ENABLED, PackageManager.DONT_KILL_APP);
            PackageInfo pi = pm.getPackageInfo(pkg, PackageManager.GET_ACTIVITIES | PackageManager.MATCH_DISABLED_COMPONENTS);
            if (pi.activities != null) for (ActivityInfo a : pi.activities) {
                if (a.targetActivity == null || a.name.equals(on.getClassName()) || !a.name.contains(".act_")) continue;
                pm.setComponentEnabledSetting(new ComponentName(pkg, a.name), PackageManager.COMPONENT_ENABLED_STATE_DISABLED, PackageManager.DONT_KILL_APP);
            }
            p.edit().putString("iconNow", want).apply();
        } catch (Exception ignored) { }
    }

    @Override
    protected void onStart() {
        super.onStart();
        if (lockOn() && leftAt > 0 && System.currentTimeMillis() - leftAt > 30000) unlocked = false;
    }

    @Override
    public void onConfigurationChanged(Configuration c) {
        super.onConfigurationChanged(c);
        if (web != null) web.evaluateJavascript("window.onNight&&window.onNight(" + isNight() + ")", null);
    }

    private boolean isNight() {
        return (getResources().getConfiguration().uiMode & Configuration.UI_MODE_NIGHT_MASK) == Configuration.UI_MODE_NIGHT_YES;
    }

    private void applyBars(boolean dark) {
        int c = dark ? Color.rgb(14, 21, 19) : Color.rgb(243, 245, 244);
        getWindow().setStatusBarColor(c);
        getWindow().setNavigationBarColor(c);
        View d = getWindow().getDecorView();
        int f = d.getSystemUiVisibility();
        int light = View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR | (Build.VERSION.SDK_INT >= 26 ? View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR : 0);
        d.setSystemUiVisibility(dark ? (f & ~light) : (f | light));
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (lockOn() && !unlocked) { lockView.setVisibility(View.VISIBLE); auth("unlock"); }
        else lockView.setVisibility(View.GONE);
        if (web != null) web.evaluateJavascript("window.onResumeApp&&window.onResumeApp()", null);
    }

    private void sendJs(String code) { runOnUiThread(() -> web.evaluateJavascript(code, null)); }

    @Override
    protected void onSaveInstanceState(Bundle out) {
        super.onSaveInstanceState(out);
        web.saveState(out);
    }

    @Override
    public void onBackPressed() {
        // 1) let the page close its top popup / menu, 2) go back in the page history,
        // 3) go to the first tab, 4) only then send the app to the background (never kill it).
        web.evaluateJavascript("(function(){try{return !!(window.MK&&MK.back())}catch(e){return false}})()", v -> {
            if ("true".equals(v)) return;
            if (web.canGoBack()) { web.goBack(); return; }
            web.evaluateJavascript("(function(){try{return !!(window.MK&&MK.home())}catch(e){return false}})()", h -> {
                if (!"true".equals(h)) moveTaskToBack(true);
            });
        });
    }

    /** Functions the page can call as Android.xxx(). */
    private class Bridge {
        @JavascriptInterface
        public void pickPhoto(final int req) { runOnUiThread(() -> openPhotoPicker(req)); }

        @JavascriptInterface
        public boolean savePhoto(String id, String dataUrl) {
            try {
                int c = dataUrl.indexOf(','); byte[] b = Base64.decode(c >= 0 ? dataUrl.substring(c + 1) : dataUrl, Base64.DEFAULT);
                try (FileOutputStream o = new FileOutputStream(photoFile(id))) { o.write(b); }
                return true;
            } catch (Exception e) { return false; }
        }

        @JavascriptInterface
        public String getPhoto(String id) {
            File f = photoFile(id); if (!f.exists()) return "";
            try (InputStream in = new java.io.FileInputStream(f)) {
                ByteArrayOutputStream o = new ByteArrayOutputStream(); byte[] buf = new byte[16384]; int n;
                while ((n = in.read(buf)) > 0) o.write(buf, 0, n);
                return "data:image/jpeg;base64," + Base64.encodeToString(o.toByteArray(), Base64.NO_WRAP);
            } catch (Exception e) { return ""; }
        }

        @JavascriptInterface
        public boolean hasPhoto(String id) { return photoFile(id).exists(); }

        @JavascriptInterface
        public void delPhoto(String id) { photoFile(id).delete(); }

        /** Paints the status bar (and nav bar) like the top of the page; darkIcons for light colours. */
        @JavascriptInterface
        public void setBars(final String color, final boolean darkIcons) {
            runOnUiThread(() -> {
                try {
                    android.view.Window w = getWindow();
                    int c = android.graphics.Color.parseColor(color);
                    w.setStatusBarColor(c);
                    w.setNavigationBarColor(c);
                    if (Build.VERSION.SDK_INT >= 23) {
                        android.view.View d = w.getDecorView();
                        int f = d.getSystemUiVisibility();
                        f = darkIcons ? (f | android.view.View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR) : (f & ~android.view.View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR);
                        d.setSystemUiVisibility(f);
                    }
                } catch (Exception ignored) {}
            });
        }

        /** Paints the navigation bar like the bottom of the page (a bottom sheet, the page, a dim popup). */
        @JavascriptInterface
        public void setNav(final String color, final boolean darkIcons) {
            runOnUiThread(() -> {
                try {
                    android.view.Window w = getWindow();
                    w.setNavigationBarColor(android.graphics.Color.parseColor(color));
                    if (Build.VERSION.SDK_INT >= 26) {
                        android.view.View d = w.getDecorView();
                        int f = d.getSystemUiVisibility();
                        f = darkIcons ? (f | android.view.View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR) : (f & ~android.view.View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR);
                        d.setSystemUiVisibility(f);
                    }
                } catch (Exception ignored) {}
            });
        }

        @JavascriptInterface
        public String saveFile(String name, String text) {
            try {
                byte[] bytes = text.getBytes(StandardCharsets.UTF_8);
                if (Build.VERSION.SDK_INT >= 29) {
                    ContentValues cv = new ContentValues();
                    cv.put(MediaStore.Downloads.DISPLAY_NAME, name);
                    cv.put(MediaStore.Downloads.MIME_TYPE, name.endsWith(".csv") ? "text/csv" : "application/json");
                    cv.put(MediaStore.Downloads.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS);
                    Uri u = getContentResolver().insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, cv);
                    try (OutputStream o = getContentResolver().openOutputStream(u)) { o.write(bytes); }
                    return "Downloads";
                } else {
                    File f = new File(getExternalFilesDir(null), name);
                    try (FileOutputStream o = new FileOutputStream(f)) { o.write(bytes); }
                    return f.getParent();
                }
            } catch (Exception e) {
                return "";
            }
        }

        /** Saves a binary file (base64) to Downloads; returns its content:// address (or the folder on old phones), "" on failure. */
        @JavascriptInterface
        public String saveBytes(String name, String b64, String mime) {
            try {
                byte[] bytes = Base64.decode(b64, Base64.DEFAULT);
                if (Build.VERSION.SDK_INT >= 29) {
                    ContentValues cv = new ContentValues();
                    cv.put(MediaStore.Downloads.DISPLAY_NAME, name);
                    cv.put(MediaStore.Downloads.MIME_TYPE, mime);
                    cv.put(MediaStore.Downloads.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS);
                    Uri u = getContentResolver().insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, cv);
                    try (OutputStream o = getContentResolver().openOutputStream(u)) { o.write(bytes); }
                    return u.toString();
                } else {
                    File f = new File(getExternalFilesDir(null), name);
                    try (FileOutputStream o = new FileOutputStream(f)) { o.write(bytes); }
                    return f.getParent();
                }
            } catch (Exception e) { return ""; }
        }

        /** Opens the share sheet for a saved file (WhatsApp, Drive, a print app…). */
        @JavascriptInterface
        public void shareUri(final String uri, final String mime, final String title) {
            runOnUiThread(() -> {
                try {
                    Intent i = new Intent(Intent.ACTION_SEND);
                    i.setType(mime);
                    i.putExtra(Intent.EXTRA_STREAM, Uri.parse(uri));
                    i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                    startActivity(Intent.createChooser(i, title));
                } catch (Exception ignored) { }
            });
        }

        /** Network request for cloud sync. The answer comes back through window.onHttp(id, status, body). */
        @JavascriptInterface
        public void http(final int id, final String method, final String url, final String headers, final String body) {
            new Thread(() -> {
                int status = 0;
                String text;
                try {
                    HttpURLConnection c = (HttpURLConnection) new URL(url).openConnection();
                    c.setConnectTimeout(15000);
                    c.setReadTimeout(30000);
                    c.setRequestMethod(method);
                    JSONObject h = new JSONObject(headers == null || headers.isEmpty() ? "{}" : headers);
                    for (Iterator<String> it = h.keys(); it.hasNext(); ) { String k = it.next(); c.setRequestProperty(k, h.getString(k)); }
                    if (body != null && !body.isEmpty()) {
                        c.setDoOutput(true);
                        try (OutputStream o = c.getOutputStream()) { o.write(body.getBytes(StandardCharsets.UTF_8)); }
                    }
                    status = c.getResponseCode();
                    InputStream in = status >= 400 ? c.getErrorStream() : c.getInputStream();
                    ByteArrayOutputStream b = new ByteArrayOutputStream();
                    if (in != null) { byte[] buf = new byte[8192]; int n; while ((n = in.read(buf)) > 0) b.write(buf, 0, n); in.close(); }
                    text = b.toString("UTF-8");
                } catch (Exception e) {
                    text = String.valueOf(e.getMessage());
                }
                sendJs("window.onHttp&&window.onHttp(" + id + "," + status + "," + JSONObject.quote(text) + ")");
            }).start();
        }

        @JavascriptInterface
        public void share(String text) {
            runOnUiThread(() -> {
                Intent i = new Intent(Intent.ACTION_SEND).setType("text/plain").putExtra(Intent.EXTRA_TEXT, text);
                try { startActivity(Intent.createChooser(i, L("مشاركة الكود", "Share code"))); } catch (Exception ignored) { }
            });
        }

        @JavascriptInterface
        public void copy(String text) {
            android.content.ClipboardManager cm = (android.content.ClipboardManager) getSystemService(CLIPBOARD_SERVICE);
            if (cm != null) cm.setPrimaryClip(android.content.ClipData.newPlainText("code", text));
        }

        /** Opens Google's barcode scanner (no camera permission needed). Result: window.onScan(id, text or null, error). */
        @JavascriptInterface
        public void scan(final int id) {
            runOnUiThread(() -> {
                try {
                    GmsBarcodeScannerOptions o = new GmsBarcodeScannerOptions.Builder()
                            .setBarcodeFormats(Barcode.FORMAT_ALL_FORMATS).enableAutoZoom().build();
                    GmsBarcodeScanner sc = GmsBarcodeScanning.getClient(MainActivity.this, o);
                    sc.startScan()
                            .addOnSuccessListener(b -> sendJs("window.onScan&&window.onScan(" + id + "," + JSONObject.quote(String.valueOf(b.getRawValue())) + ",'')"))
                            .addOnCanceledListener(() -> sendJs("window.onScan&&window.onScan(" + id + ",null,'')"))
                            .addOnFailureListener(e -> sendJs("window.onScan&&window.onScan(" + id + ",null," + JSONObject.quote(String.valueOf(e.getMessage())) + ")"));
                } catch (Throwable e) {
                    sendJs("window.onScan&&window.onScan(" + id + ",null," + JSONObject.quote(String.valueOf(e.getMessage())) + ")");
                }
            });
        }

        /** Prints an HTML page (receipt) through Android printing: a Wi-Fi/Bluetooth printer or Save as PDF. */
        @JavascriptInterface
        public void print(final String html, final String job) {
            runOnUiThread(() -> {
                WebView pv = new WebView(MainActivity.this);
                printView = pv;
                pv.setWebViewClient(new WebViewClient() {
                    @Override
                    public void onPageFinished(WebView v, String url) {
                        PrintManager pm = (PrintManager) getSystemService(PRINT_SERVICE);
                        if (pm == null) return;
                        pm.print(job, v.createPrintDocumentAdapter(job), new PrintAttributes.Builder().build());
                    }
                });
                pv.loadDataWithBaseURL(null, html, "text/html", "UTF-8", null);
            });
        }

        /** Opens a link outside the app (WhatsApp wa.me links). */
        @JavascriptInterface
        public void openUrl(final String url) {
            runOnUiThread(() -> {
                try { startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url))); } catch (Exception ignored) { }
            });
        }

        @JavascriptInterface
        public void shareText(final String text, final String title) {
            runOnUiThread(() -> {
                Intent i = new Intent(Intent.ACTION_SEND).setType("text/plain").putExtra(Intent.EXTRA_TEXT, text);
                try { startActivity(Intent.createChooser(i, title)); } catch (Exception ignored) { }
            });
        }

        @JavascriptInterface
        public void setLang(String lang) {
            StockWorker.prefs(MainActivity.this).edit().putString("lang", "en".equals(lang) ? "en" : "ar").apply();
            runOnUiThread(() -> { if (lockView != null && lockView.getChildCount() > 2) {
                ((TextView) lockView.getChildAt(0)).setText(L("Takla Ibrahim مقفول", "Takla Ibrahim is locked"));
                ((Button) lockView.getChildAt(2)).setText(L("فتح", "Open")); } });
        }

        @JavascriptInterface
        public void setIcon(String key) {
            if (key != null && key.matches("[a-z0-9_]+")) StockWorker.prefs(MainActivity.this).edit().putString("iconWant", key).apply();
        }

        @JavascriptInterface
        public void setAlerts(String json) {
            StockWorker.prefs(MainActivity.this).edit().putString("alerts", json).apply();
        }

        @JavascriptInterface
        public String lockState() {
            try { return new JSONObject().put("on", lockOn()).put("available", deviceSecure()).toString(); } catch (Exception e) { return "{}"; }
        }

        @JavascriptInterface
        public void lockEnable() { runOnUiThread(() -> auth("enable")); }

        @JavascriptInterface
        public void lockDisable() { runOnUiThread(() -> auth("disable")); }

        @JavascriptInterface
        public boolean isNight() { return MainActivity.this.isNight(); }

        @JavascriptInterface
        public void setTheme(String mode) { runOnUiThread(() -> applyBars("dark".equals(mode))); }
    }
}
