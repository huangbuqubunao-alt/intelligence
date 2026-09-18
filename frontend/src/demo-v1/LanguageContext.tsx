import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { defaultLanguageSettings, type EvidenceDisplay, type FollowingLanguageMode, type Language, type LanguageSettings } from "./model";
import type { EvidenceItem } from "./fixtures";

/**
 * Language settings live at the DemoApp root and flow down through context.
 *
 * The three concepts are deliberately independent:
 * - uiLanguage: product chrome text (Demo copy stays 简体中文; the picker is a
 *   structural placeholder, see Settings → 常规 / 语言).
 * - outputLanguage: language of generated artifacts (summary, key points,
 *   chapters, Intelligence, Topic, Research).
 * - evidenceDisplay: how Evidence excerpts are rendered (译文 / 双语 / 原文).
 *
 * Changing uiLanguage never mutates source content. Source language is an
 * intrinsic fixture property.
 */
type LanguageContextValue = {
  settings: LanguageSettings;
  setUiLanguage: (language: Language) => void;
  setOutputLanguage: (language: Language) => void;
  setEvidenceDisplay: (display: EvidenceDisplay) => void;
  /** Per-Following override state (browser-only, not persisted). */
  followingOverrides: Record<string, { mode: FollowingLanguageMode; outputLanguage: Language }>;
  setFollowingOverride: (followingId: string, override: { mode: FollowingLanguageMode; outputLanguage: Language }) => void;
  /** Effective output language for a given Following, honoring its override. */
  effectiveOutputLanguage: (followingId?: string) => Language;
};

const LanguageContext = createContext<LanguageContextValue | null>(null);

export function LanguageProvider({ children, initialSettings = defaultLanguageSettings }: { children: ReactNode; initialSettings?: LanguageSettings }) {
  const [settings, setSettings] = useState<LanguageSettings>(initialSettings);
  const [followingOverrides, setFollowingOverrides] = useState<Record<string, { mode: FollowingLanguageMode; outputLanguage: Language }>>({});

  const setUiLanguage = useCallback((uiLanguage: Language) => setSettings(current => ({ ...current, uiLanguage })), []);
  const setOutputLanguage = useCallback((outputLanguage: Language) => setSettings(current => ({ ...current, outputLanguage })), []);
  const setEvidenceDisplay = useCallback((evidenceDisplay: EvidenceDisplay) => setSettings(current => ({ ...current, evidenceDisplay })), []);
  const setFollowingOverride = useCallback((followingId: string, override: { mode: FollowingLanguageMode; outputLanguage: Language }) => {
    setFollowingOverrides(current => ({ ...current, [followingId]: override }));
  }, []);
  const effectiveOutputLanguage = useCallback((followingId?: string): Language => {
    if (!followingId) return settings.outputLanguage;
    const override = followingOverrides[followingId];
    if (override && override.mode === "custom") return override.outputLanguage;
    return settings.outputLanguage;
  }, [followingOverrides, settings.outputLanguage]);

  const value = useMemo<LanguageContextValue>(() => ({
    settings,
    setUiLanguage,
    setOutputLanguage,
    setEvidenceDisplay,
    followingOverrides,
    setFollowingOverride,
    effectiveOutputLanguage,
  }), [settings, setUiLanguage, setOutputLanguage, setEvidenceDisplay, followingOverrides, setFollowingOverride, effectiveOutputLanguage]);

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage(): LanguageContextValue {
  const context = useContext(LanguageContext);
  if (!context) throw new Error("useLanguage must be used inside LanguageProvider");
  return context;
}

/**
 * Resolve which excerpt(s) to render for an Evidence item under a given
 * display mode and output language. The original quote + position always
 * remain authoritative; translation is a display aid, never a new record.
 */
export function resolveEvidenceText(
  item: EvidenceItem,
  display: EvidenceDisplay,
  outputLanguage: Language,
): { primary: string; secondary?: string; showTranslationNote: boolean } {
  const translationAvailable = Boolean(item.translatedQuote) && item.sourceLanguage !== outputLanguage;
  if (!translationAvailable) {
    // Source already matches the output language, or no translation fixture
    // exists — all three modes collapse to the original excerpt.
    return { primary: item.quote, showTranslationNote: false };
  }
  if (display === "原文") return { primary: item.quote, showTranslationNote: true };
  if (display === "译文") return { primary: item.translatedQuote!, showTranslationNote: true };
  // 双语: translation leads, original stays visible underneath.
  return { primary: item.translatedQuote!, secondary: item.quote, showTranslationNote: true };
}
