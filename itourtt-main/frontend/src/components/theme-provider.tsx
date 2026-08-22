"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import api from "@/lib/api";

interface SystemSettings {
  theme: "light" | "dark";
  primaryColor: string;
  accentColor: string;
  sidebarColor: string;
  fontFamily: string;
  language: string;
  innerBgImageUrl: string | null;
  loginBgImageUrl: string | null;
  loginLogoUrl: string | null;
}

const DEFAULTS: SystemSettings = {
  theme: "dark",
  // iTour Reservations LITE brand — sky primary, cyan accent, slate sidebar.
  primaryColor: "#0ea5e9",
  accentColor: "#06b6d4",
  sidebarColor: "#0f172a",
  fontFamily: "Geist",
  language: "en",
  innerBgImageUrl: null,
  loginBgImageUrl: null,
  loginLogoUrl: null,
};

interface ThemeContextValue {
  settings: SystemSettings;
  loading: boolean;
  updateSettings: (partial: Partial<SystemSettings>) => Promise<void>;
  applyLocal: (partial: Partial<SystemSettings>) => void;
}

const ThemeContext = createContext<ThemeContextValue>({
  settings: DEFAULTS,
  loading: true,
  updateSettings: async () => {},
  applyLocal: () => {},
});

export function useTheme() {
  return useContext(ThemeContext);
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<SystemSettings>(DEFAULTS);
  const [loading, setLoading] = useState(true);

  // Fetch settings on mount, then overlay user preferences
  useEffect(() => {
    api
      .get("/settings/system")
      .then(({ data }) => {
        const systemSettings: SystemSettings = {
          theme: data.theme ?? DEFAULTS.theme,
          primaryColor: data.primaryColor ?? DEFAULTS.primaryColor,
          accentColor: data.accentColor ?? DEFAULTS.accentColor,
          sidebarColor: data.sidebarColor ?? DEFAULTS.sidebarColor,
          fontFamily: data.fontFamily ?? DEFAULTS.fontFamily,
          language: data.language ?? DEFAULTS.language,
          innerBgImageUrl: data.innerBgImageUrl ?? null,
          loginBgImageUrl: data.loginBgImageUrl ?? null,
          loginLogoUrl: data.loginLogoUrl ?? null,
        };

        // Overlay per-user preferences from localStorage
        try {
          const userStr = localStorage.getItem("user");
          if (userStr) {
            const user = JSON.parse(userStr);
            const prefsStr = localStorage.getItem(`user-prefs-${user.id}`);
            if (prefsStr) {
              const prefs = JSON.parse(prefsStr);
              if (prefs.language) {
                systemSettings.language = prefs.language;
              }
              if (prefs.theme) {
                if (prefs.theme === "system") {
                  systemSettings.theme = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
                } else {
                  systemSettings.theme = prefs.theme;
                }
              }
            }
          }
        } catch {
          // ignore parse errors
        }

        setSettings(systemSettings);
      })
      .catch(() => {
        // keep defaults
      })
      .finally(() => setLoading(false));
  }, []);

  // Apply theme class
  useEffect(() => {
    const root = document.documentElement;
    if (settings.theme === "dark") {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
  }, [settings.theme]);

  // Apply language + RTL direction
  useEffect(() => {
    document.documentElement.lang = settings.language;
    document.documentElement.dir = settings.language === "ar" ? "rtl" : "ltr";
  }, [settings.language]);

  // Arabic font families that already include Arabic glyphs
  const ARABIC_FONTS = ["Aref Ruqaa", "Beiruti", "El Messiri"];
  const DEFAULT_ARABIC_FONT = "El Messiri";

  // Load Google Font + Arabic fallback font
  useEffect(() => {
    const existingLink = document.getElementById("theme-font-link");
    const existingArLink = document.getElementById("theme-arabic-font-link");
    const isArabic = settings.language === "ar";
    const fontIsArabic = ARABIC_FONTS.includes(settings.fontFamily);

    if (settings.fontFamily === "Geist") {
      existingLink?.remove();
      if (!isArabic) {
        existingArLink?.remove();
        document.documentElement.style.removeProperty("--font-geist-sans");
      } else {
        // Load Arabic fallback font for Geist
        const arHref = `https://fonts.googleapis.com/css2?family=${DEFAULT_ARABIC_FONT.replace(/ /g, "+")}:wght@400;500;600;700&display=swap`;
        if (existingArLink) {
          existingArLink.setAttribute("href", arHref);
        } else {
          const link = document.createElement("link");
          link.id = "theme-arabic-font-link";
          link.rel = "stylesheet";
          link.href = arHref;
          document.head.appendChild(link);
        }
        document.documentElement.style.setProperty(
          "--font-geist-sans",
          `"${DEFAULT_ARABIC_FONT}", sans-serif`
        );
      }
      return;
    }

    // Load the selected font
    const href = `https://fonts.googleapis.com/css2?family=${settings.fontFamily.replace(/ /g, "+")}:wght@400;500;600;700&display=swap`;

    if (existingLink) {
      existingLink.setAttribute("href", href);
    } else {
      const link = document.createElement("link");
      link.id = "theme-font-link";
      link.rel = "stylesheet";
      link.href = href;
      document.head.appendChild(link);
    }

    // If Arabic language and selected font doesn't have Arabic glyphs, also load Arabic fallback
    if (isArabic && !fontIsArabic) {
      const arHref = `https://fonts.googleapis.com/css2?family=${DEFAULT_ARABIC_FONT.replace(/ /g, "+")}:wght@400;500;600;700&display=swap`;
      if (existingArLink) {
        existingArLink.setAttribute("href", arHref);
      } else {
        const link = document.createElement("link");
        link.id = "theme-arabic-font-link";
        link.rel = "stylesheet";
        link.href = arHref;
        document.head.appendChild(link);
      }
      document.documentElement.style.setProperty(
        "--font-geist-sans",
        `"${settings.fontFamily}", "${DEFAULT_ARABIC_FONT}", sans-serif`
      );
    } else {
      existingArLink?.remove();
      document.documentElement.style.setProperty(
        "--font-geist-sans",
        `"${settings.fontFamily}", sans-serif`
      );
    }
  }, [settings.fontFamily, settings.language]);

  // Apply custom colors as CSS variables
  useEffect(() => {
    const root = document.documentElement;
    root.style.setProperty("--primary-hex", settings.primaryColor);
    root.style.setProperty("--accent-hex", settings.accentColor);
    // The configurable sidebar colour is the DARK rail only. In light mode the
    // sidebar follows the CSS light tokens (ResLite slate-200) — so clear the
    // inline override there instead of forcing the dark brand colour.
    if (settings.theme === "dark") {
      root.style.setProperty("--sidebar", settings.sidebarColor);
      root.style.setProperty("--sidebar-gradient-end", settings.sidebarColor + "99");
    } else {
      root.style.removeProperty("--sidebar");
      root.style.removeProperty("--sidebar-gradient-end");
    }
  }, [settings.primaryColor, settings.accentColor, settings.sidebarColor, settings.theme]);

  // Apply inner background image — /uploads/... is served by nginx at the same origin
  useEffect(() => {
    if (settings.innerBgImageUrl) {
      document.documentElement.style.setProperty("--inner-bg-image", `url('${settings.innerBgImageUrl}')`);
      document.body.classList.add("has-inner-bg");
    } else {
      document.documentElement.style.removeProperty("--inner-bg-image");
      document.body.classList.remove("has-inner-bg");
    }
  }, [settings.innerBgImageUrl]);

  // Apply locally only (no API call) — used by per-user profile pages
  const applyLocal = useCallback(
    (partial: Partial<SystemSettings>) => {
      setSettings((prev) => ({ ...prev, ...partial }));
    },
    []
  );

  // Save to system settings API (ADMIN only) — used by admin styling page
  const updateSettings = useCallback(
    async (partial: Partial<SystemSettings>) => {
      setSettings((prev) => ({ ...prev, ...partial }));
      await api.patch("/settings/system", partial);
    },
    []
  );

  return (
    <ThemeContext.Provider value={{ settings, loading, updateSettings, applyLocal }}>
      {children}
    </ThemeContext.Provider>
  );
}
