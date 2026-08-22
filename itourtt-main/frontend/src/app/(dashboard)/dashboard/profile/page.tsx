"use client";

import { useState, useEffect } from "react";
import { Moon, Sun, Monitor, Globe, User } from "lucide-react";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAuthStore } from "@/stores/auth-store";
import { useTheme } from "@/components/theme-provider";
import { useT } from "@/lib/i18n";
import { TwoFactorSettings } from "@/components/two-factor-settings";

const LANGUAGES = [
  { value: "en", label: "English" },
  { value: "ar", label: "Arabic" },
  { value: "fr", label: "French" },
  { value: "de", label: "German" },
  { value: "es", label: "Spanish" },
  { value: "it", label: "Italian" },
  { value: "ru", label: "Russian" },
  { value: "zh", label: "Chinese" },
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

export default function ProfilePage() {
  const { user } = useAuthStore();
  const { applyLocal } = useTheme();
  const t = useT();
  const [themeMode, setThemeMode] = useState("system");
  const [language, setLanguage] = useState("en");

  // Load user prefs on mount
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
    if (!user?.id) return;

    saveUserPrefs(user.id, { theme: themeMode, language: value });
    applyLocal({ language: value });
    document.documentElement.lang = value;
    document.documentElement.dir = value === "ar" ? "rtl" : "ltr";
    toast.success(
      `${t("profile.languageSet")} ${LANGUAGES.find((l) => l.value === value)?.label ?? value}`
    );
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      {/* User Info */}
      <Card className="border-border bg-card">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-lg">
            <User className="h-5 w-5" />
            {t("profile.title")}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">{t("common.name")}</span>
            <span className="text-sm font-medium text-foreground">
              {user?.name ?? "\u2014"}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">{t("common.email")}</span>
            <span className="text-sm font-medium text-foreground">
              {user?.email ?? "\u2014"}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">{t("common.role")}</span>
            <Badge variant="outline" className="border-border text-muted-foreground">
              {t(`role.${user?.role ?? ""}`)}
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* Security — Two-factor authentication */}
      <TwoFactorSettings />

      {/* Appearance */}
      <Card className="border-border bg-card">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Sun className="h-5 w-5" />
            {t("profile.appearance")}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <Label className="text-sm text-muted-foreground">{t("profile.theme")}</Label>
            <div className="flex gap-2">
              <Button
                variant={themeMode === "light" ? "default" : "outline"}
                size="sm"
                className="flex-1 gap-2"
                onClick={() => handleThemeChange("light")}
              >
                <Sun className="h-4 w-4" />
                {t("profile.light")}
              </Button>
              <Button
                variant={themeMode === "dark" ? "default" : "outline"}
                size="sm"
                className="flex-1 gap-2"
                onClick={() => handleThemeChange("dark")}
              >
                <Moon className="h-4 w-4" />
                {t("profile.dark")}
              </Button>
              <Button
                variant={themeMode === "system" ? "default" : "outline"}
                size="sm"
                className="flex-1 gap-2"
                onClick={() => handleThemeChange("system")}
              >
                <Monitor className="h-4 w-4" />
                {t("profile.system")}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Language */}
      <Card className="border-border bg-card">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Globe className="h-5 w-5" />
            {t("profile.language")}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <Label className="text-sm text-muted-foreground">
              {t("profile.displayLanguage")}
            </Label>
            <Select value={language} onValueChange={handleLanguageChange}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder={t("profile.displayLanguage")} />
              </SelectTrigger>
              <SelectContent>
                {LANGUAGES.map((lang) => (
                  <SelectItem key={lang.value} value={lang.value}>
                    {lang.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              {t("profile.rtlNote")}
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
