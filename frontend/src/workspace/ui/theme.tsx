/**
 * Dual-theme semantic controller ("Obsidian Dark" & "Warm Paper Light") (ADAPT).
 * Upstream token model: https://github.com/shadcn-ui/ui (MIT, commit dd41d19e2f80ff6891951f7ced74c2c9a650b065)
 */
import { createContext, ReactNode, useContext, useEffect, useState } from "react";
import { runViewTransition } from "../motion";

export type UiTheme = "dark" | "light";

const THEME_STORAGE_KEY = "yia.ui-theme";

export function savedTheme(): UiTheme {
  try {
    return window.localStorage.getItem(THEME_STORAGE_KEY) === "light" ? "light" : "dark";
  } catch {
    return "dark";
  }
}

function applyDocumentTheme(theme: UiTheme) {
  if (typeof document === "undefined") return;
  document.documentElement.dataset.theme = theme;
  document.documentElement.style.colorScheme = theme;
}

type ThemeContextValue = {
  theme: UiTheme;
  setTheme: (next: UiTheme) => void;
  toggleTheme: () => void;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function UiThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setCurrentTheme] = useState<UiTheme>(() => {
    const initial = savedTheme();
    applyDocumentTheme(initial);
    return initial;
  });

  useEffect(() => {
    applyDocumentTheme(theme);
  }, [theme]);

  const setTheme = (next: UiTheme) => {
    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, next);
    } catch {
      // Ignore restricted storage environments.
    }
    runViewTransition(() => {
      applyDocumentTheme(next);
      setCurrentTheme(next);
    });
  };

  const toggleTheme = () => {
    setTheme(theme === "dark" ? "light" : "dark");
  };

  return (
    <ThemeContext.Provider value={{ theme, setTheme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useUiTheme(): ThemeContextValue {
  const value = useContext(ThemeContext);
  if (!value) {
    return {
      theme: "dark",
      setTheme: () => undefined,
      toggleTheme: () => undefined,
    };
  }
  return value;
}
