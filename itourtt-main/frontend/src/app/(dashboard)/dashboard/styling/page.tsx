"use client";

import { useEffect, useRef, useState } from "react";
import {
  Moon,
  Sun,
  Type,
  Languages,
  Palette,
  Loader2,
  Upload,
  X,
  Monitor,
  LogIn,
  Sidebar,
  Save,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import api from "@/lib/api";
import { useTheme } from "@/components/theme-provider";
import { useT } from "@/lib/i18n";

// ─── Font options ────────────────────────────────────────────────
const FONTS = [
  { value: "Geist", label: "Geist (Default)" },
  { value: "Inter", label: "Inter" },
  { value: "Roboto", label: "Roboto" },
  { value: "Open Sans", label: "Open Sans" },
  { value: "Lato", label: "Lato" },
  { value: "Poppins", label: "Poppins" },
  { value: "Montserrat", label: "Montserrat" },
  { value: "Nunito", label: "Nunito" },
  { value: "Raleway", label: "Raleway" },
  { value: "Source Sans 3", label: "Source Sans Pro" },
  { value: "Plus Jakarta Sans", label: "Plus Jakarta Sans" },
  { value: "Aref Ruqaa", label: "Aref Ruqaa (Arabic)" },
  { value: "Beiruti", label: "Beiruti (Arabic)" },
  { value: "El Messiri", label: "El Messiri (Arabic)" },
];

// ─── Language options ────────────────────────────────────────────
const LANGUAGES = [
  { value: "en", label: "English" },
  { value: "ar", label: "Arabic" },
  { value: "fr", label: "French" },
  { value: "es", label: "Spanish" },
  { value: "de", label: "German" },
  { value: "it", label: "Italian" },
  { value: "pt", label: "Portuguese" },
  { value: "tr", label: "Turkish" },
  { value: "zh", label: "Chinese (Simplified)" },
  { value: "ja", label: "Japanese" },
  { value: "ko", label: "Korean" },
  { value: "ru", label: "Russian" },
  { value: "hi", label: "Hindi" },
];

// /uploads/... is proxied by nginx at the same origin — use paths as-is
function resolveUrl(url: string | null) {
  return url ?? null;
}

// ─── Image Upload Row ────────────────────────────────────────────
function ImageUploadRow({
  label,
  description,
  currentUrl,
  accept,
  endpoint,
  onUploaded,
  onRemoved,
}: {
  label: string;
  description: string;
  currentUrl: string | null;
  accept: string;
  endpoint: string;
  onUploaded: (url: string) => void;
  onRemoved: () => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);

  async function handleFile(file: File) {
    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const { data } = await api.post(endpoint, form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      onUploaded(data.url);
      toast.success("Image uploaded");
    } catch {
      toast.error("Upload failed");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="rounded-xl border border-white/10 bg-white/5 p-4">
      <div className="mb-3">
        <p className="text-sm font-medium text-foreground">{label}</p>
        <p className="mt-0.5 text-xs text-muted-foreground">{description}</p>
      </div>

      {currentUrl ? (
        <div className="relative mb-3 overflow-hidden rounded-lg border border-white/10">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={currentUrl}
            alt={label}
            className="h-24 w-full object-cover"
          />
          <button
            onClick={onRemoved}
            className="absolute right-2 top-2 rounded-full bg-black/60 p-1 text-white/80 hover:text-white"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      ) : (
        <div className="mb-3 flex h-16 items-center justify-center rounded-lg border border-dashed border-white/20 text-xs text-muted-foreground">
          No image set
        </div>
      )}

      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) handleFile(f);
          e.target.value = "";
        }}
      />
      <Button
        variant="outline"
        size="sm"
        className="w-full gap-1.5 text-xs"
        disabled={uploading}
        onClick={() => inputRef.current?.click()}
      >
        {uploading ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : (
          <Upload className="h-3.5 w-3.5" />
        )}
        {uploading ? "Uploading…" : "Upload Image"}
      </Button>
    </div>
  );
}

// ─── Section Header ──────────────────────────────────────────────
function SectionHeader({
  icon: Icon,
  title,
}: {
  icon: React.ElementType;
  title: string;
}) {
  return (
    <div className="flex items-center gap-2 border-b border-white/10 pb-3">
      <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-white/10">
        <Icon className="h-4 w-4 text-foreground/80" />
      </div>
      <span className="text-sm font-semibold text-foreground">{title}</span>
    </div>
  );
}

// ─── Color Swatch ────────────────────────────────────────────────
function ColorSwatch({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-white/10 bg-white/5 px-4 py-3">
      <div>
        <p className="text-sm font-medium text-foreground">{label}</p>
        <p className="text-xs text-muted-foreground">{value}</p>
      </div>
      <label className="cursor-pointer">
        <div
          className="h-10 w-10 rounded-lg border-2 border-white/20 shadow-inner transition-transform hover:scale-105"
          style={{ backgroundColor: value }}
        />
        <input
          type="color"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="sr-only"
        />
      </label>
    </div>
  );
}

// ─── Live Preview ─────────────────────────────────────────────────
function LivePreview({
  theme,
  sidebarColor,
  primaryColor,
  accentColor,
  fontFamily,
  innerBgUrl,
  loginBgUrl,
  loginLogoUrl,
}: {
  theme: string;
  sidebarColor: string;
  primaryColor: string;
  accentColor: string;
  fontFamily: string;
  innerBgUrl: string | null;
  loginBgUrl: string | null;
  loginLogoUrl: string | null;
}) {
  const isDark = theme === "dark";
  const bodyBg = isDark ? "#0b1120" : "#f5f5f5";
  const bodyFg = isDark ? "#f5f5f5" : "#1a1a1a";
  const cardBg = isDark ? "rgba(255,255,255,0.07)" : "rgba(0,0,0,0.03)";
  const cardBorder = isDark ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.08)";

  return (
    <div className="flex h-full flex-col gap-4">
      {/* Dashboard Preview */}
      <div>
        <div className="mb-2 flex items-center gap-1.5 text-xs text-muted-foreground">
          <Monitor className="h-3.5 w-3.5" />
          Dashboard Preview
        </div>
        <div
          className="overflow-hidden rounded-xl border border-white/10 shadow-2xl"
          style={{ fontFamily: fontFamily === "Geist" ? undefined : `"${fontFamily}", sans-serif` }}
        >
          <div className="flex" style={{ height: 240 }}>
            {/* Sidebar */}
            <div
              className="flex flex-col items-center gap-3 py-4"
              style={{
                width: 52,
                background: `linear-gradient(180deg, ${sidebarColor} 0%, ${sidebarColor}cc 100%)`,
              }}
            >
              <div className="h-7 w-7 rounded-lg bg-white/20" />
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-4 w-7 rounded bg-white/15" />
              ))}
            </div>
            {/* Content */}
            <div
              className="flex-1 p-3"
              style={{
                background: innerBgUrl
                  ? `url('${innerBgUrl}') center/cover`
                  : bodyBg,
              }}
            >
              {/* Header bar */}
              <div
                className="mb-3 flex h-7 items-center justify-between rounded-lg px-3"
                style={{ background: cardBg, border: `1px solid ${cardBorder}` }}
              >
                <div className="h-2 w-16 rounded" style={{ background: bodyFg + "40" }} />
                <div className="h-5 w-5 rounded-full" style={{ background: primaryColor + "80" }} />
              </div>
              {/* Cards row */}
              <div className="mb-3 grid grid-cols-3 gap-2">
                {[primaryColor, accentColor, sidebarColor].map((c, i) => (
                  <div
                    key={i}
                    className="rounded-lg p-2"
                    style={{ background: cardBg, border: `1px solid ${cardBorder}` }}
                  >
                    <div className="mb-1.5 h-1.5 w-8 rounded" style={{ background: c + "80" }} />
                    <div className="h-3 w-12 rounded text-xs font-bold" style={{ background: c }} />
                  </div>
                ))}
              </div>
              {/* Table mock */}
              <div
                className="rounded-lg overflow-hidden"
                style={{ background: cardBg, border: `1px solid ${cardBorder}` }}
              >
                <div className="h-5 px-2 flex items-center gap-2" style={{ background: sidebarColor + "44" }}>
                  {[40, 60, 50, 30].map((w, i) => (
                    <div key={i} className="h-1.5 rounded" style={{ width: w, background: "#fff5" }} />
                  ))}
                </div>
                {[...Array(3)].map((_, i) => (
                  <div key={i} className="h-5 px-2 flex items-center gap-2" style={{ borderTop: `1px solid ${cardBorder}` }}>
                    {[40, 60, 50, 30].map((w, j) => (
                      <div key={j} className="h-1.5 rounded" style={{ width: w, background: bodyFg + "25" }} />
                    ))}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Login Preview */}
      <div>
        <div className="mb-2 flex items-center gap-1.5 text-xs text-muted-foreground">
          <LogIn className="h-3.5 w-3.5" />
          Login Page Preview
        </div>
        <div
          className="relative overflow-hidden rounded-xl border border-white/10 shadow-2xl"
          style={{ height: 200 }}
        >
          {/* BG */}
          <div
            className="absolute inset-0"
            style={{
              background: loginBgUrl ? `url('${loginBgUrl}') center/cover` : "linear-gradient(135deg,#1a0520 0%,#0d0014 100%)",
            }}
          />
          <div className="absolute inset-0 bg-black/40" />
          {/* Card */}
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="rounded-xl border border-white/15 bg-white/[0.07] px-6 py-5 shadow-2xl backdrop-blur-xl" style={{ width: 160 }}>
              <div className="mb-3 flex flex-col items-center gap-1.5">
                {loginLogoUrl ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={loginLogoUrl} alt="logo" className="h-8 w-8 rounded object-cover" />
                ) : (
                  <div className="h-8 w-8 rounded-lg" style={{ background: sidebarColor }} />
                )}
                <div className="h-2 w-20 rounded bg-white/40" />
              </div>
              <div className="space-y-2">
                <div className="h-6 rounded-lg border border-white/10 bg-white/5" />
                <div className="h-6 rounded-lg border border-white/10 bg-white/5" />
                <div className="h-6 rounded-lg" style={{ background: primaryColor }} />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────
export default function StylingPage() {
  const t = useT();
  const { settings, updateSettings } = useTheme();

  const [theme, setTheme] = useState("dark");
  const [fontFamily, setFontFamily] = useState("Geist");
  const [language, setLanguage] = useState("en");
  const [primaryColor, setPrimaryColor] = useState("#3b82f6");
  const [accentColor, setAccentColor] = useState("#8b5cf6");
  const [sidebarColor, setSidebarColor] = useState("#0f172a");
  const [googleMapsApiKey, setGoogleMapsApiKey] = useState("");
  const [innerBgImageUrl, setInnerBgImageUrl] = useState<string | null>(null);
  const [loginBgImageUrl, setLoginBgImageUrl] = useState<string | null>(null);
  const [loginLogoUrl, setLoginLogoUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    api
      .get("/settings/system")
      .then(({ data }) => {
        setTheme(data.theme ?? "dark");
        setFontFamily(data.fontFamily ?? "Geist");
        setLanguage(data.language ?? "en");
        setPrimaryColor(data.primaryColor ?? "#3b82f6");
        setAccentColor(data.accentColor ?? "#8b5cf6");
        setSidebarColor(data.sidebarColor ?? "#0f172a");
        setGoogleMapsApiKey(data.googleMapsApiKey ?? "");
        setInnerBgImageUrl(resolveUrl(data.innerBgImageUrl));
        setLoginBgImageUrl(resolveUrl(data.loginBgImageUrl));
        setLoginLogoUrl(resolveUrl(data.loginLogoUrl));
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  async function handleSave() {
    setSubmitting(true);
    try {
      await updateSettings({
        theme: theme as "light" | "dark",
        fontFamily,
        language,
        primaryColor,
        accentColor,
        sidebarColor,
      });
      toast.success(t("styling.settingsSaved"));
    } catch {
      toast.error(t("styling.failedSave"));
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-80px)] overflow-hidden">
      {/* ── Left: Controls Panel ── */}
      <div className="flex w-[340px] shrink-0 flex-col border-r border-white/10 bg-black/20 backdrop-blur-sm">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-white/10 px-5 py-4">
          <div>
            <h2 className="text-sm font-semibold text-foreground">Theme Customizer</h2>
            <p className="text-xs text-muted-foreground">Customize your system appearance</p>
          </div>
          <Button size="sm" onClick={handleSave} disabled={submitting} className="gap-1.5">
            {submitting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
            Save
          </Button>
        </div>

        {/* Scrollable sections */}
        <div className="flex-1 overflow-y-auto px-5 py-5 space-y-7">

          {/* ── Theme Mode ── */}
          <div className="space-y-4">
            <SectionHeader icon={theme === "dark" ? Moon : Sun} title="Theme Mode" />
            <div className="flex items-center justify-between rounded-lg border border-white/10 bg-white/5 px-4 py-3">
              <div>
                <Label className="text-sm font-medium text-foreground">{t("styling.darkMode")}</Label>
                <p className="text-xs text-muted-foreground">
                  Currently: <span className="capitalize font-medium text-foreground/70">{theme}</span>
                </p>
              </div>
              <Switch
                checked={theme === "dark"}
                onCheckedChange={(checked) => setTheme(checked ? "dark" : "light")}
              />
            </div>
          </div>

          {/* ── Colors ── */}
          <div className="space-y-3">
            <SectionHeader icon={Palette} title="Colors" />
            <ColorSwatch label="Sidebar Color" value={sidebarColor} onChange={setSidebarColor} />
            <ColorSwatch label={t("styling.primaryColor")} value={primaryColor} onChange={setPrimaryColor} />
            <ColorSwatch label={t("styling.accentColor")} value={accentColor} onChange={setAccentColor} />
          </div>

          {/* ── Font ── */}
          <div className="space-y-3">
            <SectionHeader icon={Type} title={t("styling.displayFont")} />
            <Select value={fontFamily} onValueChange={setFontFamily}>
              <SelectTrigger className="border-white/10 bg-white/5 text-foreground">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="border-border bg-popover text-popover-foreground">
                {FONTS.map((f) => (
                  <SelectItem key={f.value} value={f.value}>
                    {f.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p
              className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-muted-foreground"
              style={{ fontFamily: fontFamily === "Geist" ? undefined : `"${fontFamily}", sans-serif` }}
            >
              The quick brown fox jumps over the lazy dog
            </p>
          </div>

          {/* ── Language ── */}
          <div className="space-y-3">
            <SectionHeader icon={Languages} title={t("styling.displayLanguage")} />
            <Select value={language} onValueChange={setLanguage}>
              <SelectTrigger className="border-white/10 bg-white/5 text-foreground">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="border-border bg-popover text-popover-foreground">
                {LANGUAGES.map((l) => (
                  <SelectItem key={l.value} value={l.value}>
                    {l.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* ── Images ── */}
          <div className="space-y-3">
            <SectionHeader icon={Sidebar} title="Background Images" />

            <ImageUploadRow
              label="Dashboard Background"
              description="Overlay image behind all inner pages (PNG, JPG, SVG)"
              currentUrl={innerBgImageUrl}
              accept="image/png,image/jpeg,image/svg+xml"
              endpoint="/settings/system/inner-bg"
              onUploaded={(url) => {
                setInnerBgImageUrl(url);
                updateSettings({ innerBgImageUrl: url });
              }}
              onRemoved={() => {
                setInnerBgImageUrl(null);
                updateSettings({ innerBgImageUrl: null as unknown as string });
              }}
            />

            <ImageUploadRow
              label="Login Background"
              description="Full-screen image behind the login card (PNG, JPG, SVG)"
              currentUrl={loginBgImageUrl}
              accept="image/png,image/jpeg,image/svg+xml"
              endpoint="/settings/system/login-bg"
              onUploaded={(url) => setLoginBgImageUrl(url)}
              onRemoved={() => setLoginBgImageUrl(null)}
            />

            <ImageUploadRow
              label="Login Logo"
              description="Logo shown above the login form (PNG, JPG, SVG)"
              currentUrl={loginLogoUrl}
              accept="image/png,image/jpeg,image/svg+xml"
              endpoint="/settings/system/login-logo"
              onUploaded={(url) => setLoginLogoUrl(url)}
              onRemoved={() => setLoginLogoUrl(null)}
            />
          </div>

        </div>
      </div>

      {/* ── Right: Live Preview ── */}
      <div className="flex-1 overflow-y-auto bg-black/10 p-6">
        <div className="mb-4">
          <h3 className="text-sm font-semibold text-foreground">Live Preview</h3>
          <p className="text-xs text-muted-foreground">Updates as you change settings above</p>
        </div>
        <LivePreview
          theme={theme}
          sidebarColor={sidebarColor}
          primaryColor={primaryColor}
          accentColor={accentColor}
          fontFamily={fontFamily}
          innerBgUrl={innerBgImageUrl}
          loginBgUrl={loginBgImageUrl}
          loginLogoUrl={loginLogoUrl}
        />
      </div>
    </div>
  );
}
