"use client";

import { useState, useEffect } from "react";
import { Moon, Sun, Monitor, Globe, User, ChevronRight } from "lucide-react";
import { toast } from "sonner";
import { Card, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { useAuthStore } from "@/stores/auth-store";
import { useTheme } from "@/components/theme-provider";
import { cn } from "@/lib/utils";
import { useT } from "@/lib/i18n";

const LANGUAGES = [
  { value: "en", label: "English", native: "English" },
  { value: "ar", label: "Arabic", native: "\u0627\u0644\u0639\u0631\u0628\u064A\u0629" },
  { value: "fr", label: "French", native: "Fran\u00E7ais" },
  { value: "de", label: "German", native: "Deutsch" },
  { value: "es", label: "Spanish", native: "Espa\u00F1ol" },
  { value: "it", label: "Italian", native: "Italiano" },
  { value: "ru", label: "Russian", native: "\u0420\u0443\u0441\u0441\u043A\u0438\u0439" },
  { value: "zh", label: "Chinese", native: "\u4E2D\u6587" },
];

function getPrefsKey(userId: string) {
  return `user-prefs-${userId}`;
}

function loadUserPrefs(userId: string): { theme: string; language: string } {
  try {
    const raw = localStorage.getItem(getPrefsKey(userId));
    if (raw) return JSON.parse(raw);
  } catch {
    // ignore
  }
  return { theme: "system", language: "en" };
}

function saveUserPrefs(userId: string, prefs: { theme: string; language: string }) {
  localStorage.setItem(getPrefsKey(userId), JSON.stringify(prefs));
}

export default function MobileProfilePage() {
  const { user } = useAuthStore();
  const { applyLocal } = useTheme();
  const t = useT();
  const [themeMode, setThemeMode] = useState("system");
  const [language, setLanguage] = useState("en");
  const [langOpen, setLangOpen] = useState(false);

  useEffect(() => {
    if (!user?.id) return;
    const prefs = loadUserPrefs(user.id);
    setThemeMode(prefs.theme);
    setLanguage(prefs.language);
  }, [user?.id]);

  function handleThemeChange(value: string) {
    setThemeMode(value);
    if (!user?.id) return;

    let resolvedTheme: "light" | "dark";
    if (value === "system") {
      resolvedTheme = window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light";
    } else {
      resolvedTheme = value as "light" | "dark";
    }

    saveUserPrefs(user.id, { theme: value, language });
    applyLocal({ theme: resolvedTheme });
    toast.success(`${t("profile.themeSet")} ${value}`);
  }

  function handleLanguageChange(value: string) {
    setLanguage(value);
    setLangOpen(false);
    if (!user?.id) return;

    saveUserPrefs(user.id, { theme: themeMode, language: value });
    applyLocal({ language: value });
    document.documentElement.lang = value;
    document.documentElement.dir = value === "ar" ? "rtl" : "ltr";
    toast.success(
      `${t("profile.languageSet")} ${LANGUAGES.find((l) => l.value === value)?.label ?? value}`
    );
  }

  const currentLang = LANGUAGES.find((l) => l.value === language);

  return (
    <div className="space-y-4">
      {/* User avatar + info */}
      <div className="flex flex-col items-center gap-2 pb-2 pt-4">
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
          <User className="h-8 w-8 text-primary" />
        </div>
        <div className="text-center">
          <p className="text-lg font-semibold text-foreground">{user?.name ?? "\u2014"}</p>
          <p className="text-sm text-muted-foreground">{user?.email ?? "\u2014"}</p>
          <Badge variant="outline" className="mt-1 border-border text-muted-foreground">
            {t(`role.${user?.role ?? ""}`)}
          </Badge>
        </div>
      </div>

      {/* Theme section */}
      <Card className="border-border bg-card">
        <CardContent className="p-4">
          <Label className="mb-3 flex items-center gap-2 text-sm font-medium text-foreground">
            <Sun className="h-4 w-4 text-muted-foreground" />
            {t("profile.appearance")}
          </Label>
          <div className="grid grid-cols-3 gap-2">
            {[
              { value: "light", labelKey: "profile.light", icon: Sun },
              { value: "dark", labelKey: "profile.dark", icon: Moon },
              { value: "system", labelKey: "profile.system", icon: Monitor },
            ].map((opt) => (
              <button
                key={opt.value}
                onClick={() => handleThemeChange(opt.value)}
                className={cn(
                  "flex flex-col items-center gap-1.5 rounded-xl border-2 px-3 py-3 text-xs font-medium transition-all",
                  themeMode === opt.value
                    ? "border-primary bg-primary/10 text-primary"
                    : "border-border bg-card text-muted-foreground active:bg-muted"
                )}
              >
                <opt.icon className="h-5 w-5" />
                {t(opt.labelKey)}
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Language section */}
      <Card className="border-border bg-card">
        <CardContent className="p-4">
          <Label className="mb-3 flex items-center gap-2 text-sm font-medium text-foreground">
            <Globe className="h-4 w-4 text-muted-foreground" />
            {t("profile.language")}
          </Label>

          {!langOpen ? (
            <button
              onClick={() => setLangOpen(true)}
              className="flex w-full items-center justify-between rounded-lg border border-border bg-muted/30 px-4 py-3 text-sm active:bg-muted"
            >
              <span className="text-foreground">
                {currentLang?.label ?? language}{" "}
                <span className="text-muted-foreground">({currentLang?.native})</span>
              </span>
              <ChevronRight className="h-4 w-4 text-muted-foreground" />
            </button>
          ) : (
            <div className="space-y-1">
              {LANGUAGES.map((lang) => (
                <button
                  key={lang.value}
                  onClick={() => handleLanguageChange(lang.value)}
                  className={cn(
                    "flex w-full items-center justify-between rounded-lg px-4 py-3 text-sm transition-colors active:bg-muted",
                    language === lang.value
                      ? "bg-primary/10 text-primary font-medium"
                      : "text-foreground"
                  )}
                >
                  <span>
                    {lang.label}{" "}
                    <span className="text-muted-foreground">({lang.native})</span>
                  </span>
                  {language === lang.value && (
                    <div className="h-2 w-2 rounded-full bg-primary" />
                  )}
                </button>
              ))}
            </div>
          )}

          <p className="mt-2 text-xs text-muted-foreground">
            {t("profile.rtlNote")}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
