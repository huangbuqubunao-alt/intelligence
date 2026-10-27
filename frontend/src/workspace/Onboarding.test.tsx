import { fireEvent, render, screen } from "@testing-library/react";
import { completeOnboarding, FirstRunOnboarding, onboardingCompleted, onboardingStorageKey } from "./Onboarding";
import { UiLanguageProvider } from "./uiLanguage";

test("completion is durable across component remount and an empty library", () => {
  localStorage.removeItem(onboardingStorageKey);
  expect(onboardingCompleted()).toBe(false);
  completeOnboarding();
  expect(onboardingCompleted()).toBe(true);
  expect(localStorage.getItem(onboardingStorageKey)).toBe("true");
});

test.each(["en", "zh-CN"])("onboarding offers truthful multiple sources and skip (%s)", language => {
  localStorage.setItem("yia.ui-language", language);
  const skip = vi.fn(); const add = vi.fn();
  render(<UiLanguageProvider><FirstRunOnboarding onSkip={skip} onAddFollowing={add} /></UiLanguageProvider>);
  const continueLabel = language === "en" ? "Continue" : "继续";
  fireEvent.click(screen.getByRole("button", { name: continueLabel }));
  expect(screen.getByText(language === "en" ? /Never make a paid cloud call/ : /明确/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: continueLabel }));
  expect(screen.getByText(/YouTube.*Bilibili/)).toBeTruthy();
  expect(screen.queryByText("Topic")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: language === "en" ? "Skip for now" : "暂时跳过" }));
  expect(skip).toHaveBeenCalledOnce();
  fireEvent.click(screen.getByRole("button", { name: language === "en" ? "Add something" : "添加内容" }));
  expect(add).toHaveBeenCalledOnce();
});


test("first-run cloud setup can be opened without completing import or invoking a model", () => {
  localStorage.setItem("yia.ui-language", "en");
  const skip = vi.fn();
  render(<UiLanguageProvider><FirstRunOnboarding onSkip={skip} onAddFollowing={vi.fn()} /></UiLanguageProvider>);
  fireEvent.click(screen.getByRole("button", { name: "Continue" }));
  const setup = screen.getByRole("link", { name: "Explore optional cloud Intelligence setup" });
  expect(setup.getAttribute("href")).toBe("#Settings/models/bigmodel");
  fireEvent.click(setup);
  expect(skip).toHaveBeenCalledOnce();
});
