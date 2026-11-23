import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { completeOnboarding, FirstRunOnboarding, onboardingCompleted, onboardingStorageKey } from "./Onboarding";
import { UiLanguageProvider, useUiLanguage } from "./uiLanguage";

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

test.each(["en", "zh-CN"])("onboarding stepper jumps steps cleanly and structures step 2 links and step 3 source cards (%s)", language => {
  cleanup();
  localStorage.setItem("yia.ui-language", language);
  render(<UiLanguageProvider><FirstRunOnboarding onSkip={vi.fn()} onAddFollowing={vi.fn()} /></UiLanguageProvider>);
  const step1 = screen.getByRole("button", { name: language === "en" ? "1. Core flow" : "1. 核心流程" });
  const step2 = screen.getByRole("button", { name: language === "en" ? "2. Local & privacy" : "2. 本地与隐私" });
  const step3 = screen.getByRole("button", { name: language === "en" ? "3. First import" : "3. 导入首条内容" });
  expect(step1.getAttribute("aria-current")).toBe("step");

  fireEvent.click(step2);
  expect(step2.getAttribute("aria-current")).toBe("step");
  const setupLinks = document.querySelector(".onboarding-setup-links");
  expect(setupLinks).toBeTruthy();
  expect(setupLinks?.classList.contains("button-row")).toBe(true);
  expect(within(setupLinks as HTMLElement).getAllByRole("link")).toHaveLength(2);

  fireEvent.click(step3);
  expect(step3.getAttribute("aria-current")).toBe("step");
  const sourceItems = document.querySelectorAll(".onboarding-source-list li");
  expect(sourceItems).toHaveLength(3);
  expect(screen.queryByText("Topic")).toBeNull();
  cleanup();
});

test("zh-CN dictionary covers previously missing UI strings and removes raw UNKNOWN billing label", () => {
  cleanup();
  localStorage.setItem("yia.ui-language", "zh-CN");
  function TranslationProbe() {
    const { t } = useUiLanguage();
    return (
      <div>
        <span data-testid="organized">{t("Organized")}</span>
        <span data-testid="pos">{t("Position unavailable")}</span>
        <span data-testid="review">{t("Review Content")}</span>
        <span data-testid="loading-saved">{t("Loading current saved Intelligence…")}</span>
        <span data-testid="investigations">{t("Investigations are not active in V1")}</span>
        <span data-testid="moonshot-cost">
          {t("Moonshot API usage is billed separately and may incur charges. Cost for this execution: UNKNOWN before the response. Published China-platform K2.6 rates: ¥6.50 per million uncached input tokens, ¥1.10 per million cached input tokens, and ¥27 per million output tokens. This request allows up to 8,192 output tokens.")}
        </span>
      </div>
    );
  }
  render(<UiLanguageProvider><TranslationProbe /></UiLanguageProvider>);
  expect(screen.getByTestId("organized").textContent).toBe("已整理");
  expect(screen.getByTestId("pos").textContent).toBe("位置信息暂不可用");
  expect(screen.getByTestId("review").textContent).toBe("查看内容");
  expect(screen.getByTestId("loading-saved").textContent).toBe("正在加载已收藏洞察…");
  expect(screen.getByTestId("investigations").textContent).toBe("V1 版本暂未启用专题调查");
  const costText = screen.getByTestId("moonshot-cost").textContent ?? "";
  expect(costText).toContain("实际费用未知");
  expect(costText).not.toContain("UNKNOWN");
  cleanup();
});
