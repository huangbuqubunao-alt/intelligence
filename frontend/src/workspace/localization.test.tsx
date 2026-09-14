import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  LANGUAGE_STORAGE_KEY,
  LanguageProvider,
  useLanguage,
} from "./localization";

function Harness() {
  const { locale, setLocale, t } = useLanguage();
  return (
    <main>
      <p>{locale}</p>
      <h1>{t("Dashboard")}</h1>
      <button type="button" onClick={() => setLocale("zh-CN")}>
        Chinese
      </button>
      <button type="button" onClick={() => setLocale("en")}>
        English
      </button>
    </main>
  );
}

beforeEach(() => {
  localStorage.clear();
  document.documentElement.lang = "";
});

test("defaults to English and declares the document language", () => {
  render(<LanguageProvider><Harness /></LanguageProvider>);

  expect(screen.getByRole("heading", { name: "Dashboard" })).toBeTruthy();
  expect(screen.getByText("en")).toBeTruthy();
  expect(document.documentElement.lang).toBe("en");
  expect(localStorage.getItem(LANGUAGE_STORAGE_KEY)).toBeNull();
});

test("switches immediately and persists only the supported locale", async () => {
  const user = userEvent.setup();
  const first = render(<LanguageProvider><Harness /></LanguageProvider>);

  await user.click(screen.getByRole("button", { name: "Chinese" }));
  expect(screen.getByRole("heading", { name: "概览" })).toBeTruthy();
  expect(screen.getByText("zh-CN")).toBeTruthy();
  expect(document.documentElement.lang).toBe("zh-CN");
  expect(localStorage.getItem(LANGUAGE_STORAGE_KEY)).toBe("zh-CN");

  first.unmount();
  render(<LanguageProvider><Harness /></LanguageProvider>);
  expect(screen.getByRole("heading", { name: "概览" })).toBeTruthy();

  await user.click(screen.getByRole("button", { name: "English" }));
  expect(screen.getByRole("heading", { name: "Dashboard" })).toBeTruthy();
  expect(localStorage.getItem(LANGUAGE_STORAGE_KEY)).toBe("en");
});

test("falls back to English when persisted locale is unsupported", () => {
  localStorage.setItem(LANGUAGE_STORAGE_KEY, "fr");
  render(<LanguageProvider><Harness /></LanguageProvider>);

  expect(screen.getByRole("heading", { name: "Dashboard" })).toBeTruthy();
  expect(screen.getByText("en")).toBeTruthy();
  expect(document.documentElement.lang).toBe("en");
});
